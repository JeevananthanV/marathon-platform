import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.participant import Participant
from app.models.whatsapp_message import WhatsAppMessage
from app.models.integration_log import IntegrationLog
from app.services.whatsapp.provider import BaseWhatsAppProvider
from app.services.whatsapp.mock_provider import MockWhatsAppProvider
from app.services.whatsapp.cloud_provider import WhatsAppCloudAPIProvider
from app.services.whatsapp.templates import (
    WhatsAppTemplateType,
    template_engine,
)
from app.core.config import settings
from app.core.logging import logger


class WhatsAppService:
    """
    Core WhatsApp Service orchestrating outbound communication, template rendering,
    strict consent checks, persistent message ledger, and idempotent delivery tracking.
    """

    def __init__(self):
        self._mock_provider = MockWhatsAppProvider()
        self._cloud_provider = WhatsAppCloudAPIProvider()

    def get_provider(self) -> BaseWhatsAppProvider:
        """Dynamically select Mock or Live Meta Graph API provider."""
        if settings.is_whatsapp_mock_active():
            return self._mock_provider
        return self._cloud_provider

    @property
    def mock_provider(self) -> MockWhatsAppProvider:
        return self._mock_provider

    async def _send_template_internal(
        self,
        db: AsyncSession,
        registration_id: str,
        template_type: WhatsAppTemplateType,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal routine for consent verification, template compilation,
        idempotency checking, provider dispatch, and database persistence.
        """
        idempotency_key = f"whatsapp:{template_type.value}:{registration_id}"

        # 1. Fetch Registration with relationships
        query = (
            select(Registration)
            .options(
                selectinload(Registration.participant),
                selectinload(Registration.category),
                selectinload(Registration.payments),
            )
            .where(Registration.id == registration_id)
        )
        result = await db.execute(query)
        reg = result.scalar_one_or_none()

        if not reg:
            logger.warning(f"[WHATSAPP SERVICE] Registration '{registration_id}' not found.")
            return {"status": "FAILED", "error": "Registration not found", "retryable": False}

        participant = reg.participant
        category = reg.category
        latest_payment = reg.payments[0] if reg.payments else None

        # 2. Consent Verification (Participant + Registration Consent)
        has_consent = bool(
            getattr(participant, "whatsapp_consent", True)
            and getattr(reg, "communication_consent", True)
        )
        if not has_consent:
            logger.info(f"[WHATSAPP CONSENT] Suppressed message for {participant.email}: Consent is disabled.")
            return {
                "status": "FAILED",
                "error": "WhatsApp communication consent not granted by participant.",
                "retryable": False,
                "consent_required": True,
            }

        # 3. Phone Number Validation
        if not participant.phone_number:
            return {"status": "FAILED", "error": "Missing participant phone number", "retryable": False}

        # 4. Strong Idempotency Check in whatsapp_messages table
        existing_msg_q = select(WhatsAppMessage).where(WhatsAppMessage.idempotency_key == idempotency_key)
        existing_msg = (await db.execute(existing_msg_q)).scalar_one_or_none()

        if existing_msg and existing_msg.status in ["SENT", "DELIVERED", "READ"]:
            logger.info(f"[WHATSAPP IDEMPOTENCY] Message {idempotency_key} already sent previously.")
            return {
                "status": "SUCCESS",
                "idempotent": True,
                "message_id": existing_msg.provider_message_id,
                "template": template_type.value,
                "message": "Message already sent previously.",
            }

        # 5. Assemble Template Context
        context = {
            "name": participant.full_name,
            "registration_id": reg.registration_code,
            "category": category.title if category else "Marathon",
            "event_name": settings.EVENT_NAME,
            "event_date": "March 22, 2026",
            "venue": "Bengaluru Stadium / Cubbon Park",
            "bib_number": reg.bib_number or reg.registration_code,
            "reporting_time": category.start_time if category else "05:30 AM",
            "amount": f"{float(latest_payment.amount_inr):.2f}" if latest_payment else (f"{float(category.price_inr):.2f}" if category else "0.00"),
            "payment_status": latest_payment.status if latest_payment else ("CONFIRMED" if reg.status == "CONFIRMED" else "PENDING"),
            "support_contact": "support@marathon.example.com / +91 80 1234 5678",
            **(extra_data or {}),
        }

        # 6. Render Template
        try:
            rendered = template_engine.render_template(
                template_type=template_type,
                recipient_phone=participant.phone_number,
                context=context,
            )
        except Exception as render_err:
            logger.error(f"[WHATSAPP TEMPLATE] Render failed for {template_type.value}: {str(render_err)}")
            return {"status": "FAILED", "error": str(render_err), "retryable": False}

        provider = self.get_provider()
        now = datetime.now(timezone.utc)

        # 7. Dispatch via Provider
        try:
            res = await provider.send_template_message(
                to_phone=participant.phone_number,
                template_name=rendered.template_name,
                parameters=rendered.parameters,
                components=rendered.components,
                idempotency_key=idempotency_key,
            )

            provider_msg_id = res.get("message_id")

            # 8. Record / Update WhatsAppMessage Ledger
            if existing_msg:
                existing_msg.status = "SENT"
                existing_msg.sent_at = now
                existing_msg.provider_message_id = provider_msg_id
                existing_msg.provider = provider.provider_name
                existing_msg.message_content = rendered.rendered_text
                existing_msg.error_message = None
            else:
                new_msg = WhatsAppMessage(
                    id=str(uuid.uuid4()),
                    registration_id=reg.id,
                    participant_id=participant.id,
                    phone_number=participant.phone_number,
                    message_type=template_type.name,
                    template_name=template_type.value,
                    message_content=rendered.rendered_text,
                    provider=provider.provider_name,
                    provider_message_id=provider_msg_id,
                    idempotency_key=idempotency_key,
                    status="SENT",
                    created_at=now,
                    sent_at=now,
                    retry_count=0,
                )
                db.add(new_msg)

            # Record in IntegrationLog for unified audit
            log_q = select(IntegrationLog).where(
                and_(
                    IntegrationLog.registration_id == reg.id,
                    IntegrationLog.service_name == "WHATSAPP",
                    IntegrationLog.event_type == f"WHATSAPP_{template_type.name}",
                )
            )
            existing_log = (await db.execute(log_q)).scalars().first()
            if existing_log:
                existing_log.status = "SUCCESS"
                existing_log.response_payload = json.dumps(res, default=str)
                existing_log.error_message = None
            else:
                log_entry = IntegrationLog(
                    id=str(uuid.uuid4()),
                    registration_id=reg.id,
                    service_name="WHATSAPP",
                    event_type=f"WHATSAPP_{template_type.name}",
                    status="SUCCESS",
                    retry_count=0,
                    request_payload=json.dumps({"template": template_type.value, "recipient": provider.clean_phone_number(participant.phone_number)}),
                    response_payload=json.dumps(res, default=str),
                )
                db.add(log_entry)

            await db.commit()

            return {
                "status": "SUCCESS",
                "message_id": provider_msg_id,
                "template": template_type.value,
                "service": "WHATSAPP",
                "provider": provider.provider_name,
                "mock": res.get("mock", False),
            }

        except Exception as e:
            error_msg = str(e)
            is_permanent = "permanent" in error_msg.lower() or "131030" in error_msg
            logger.error(f"[WHATSAPP DISPATCH ERROR] {reg.registration_code} ({template_type.value}): {error_msg}")

            if existing_msg:
                existing_msg.status = "FAILED"
                existing_msg.failed_at = now
                existing_msg.error_message = error_msg[:500]
                existing_msg.retry_count += 1
            else:
                failed_msg = WhatsAppMessage(
                    id=str(uuid.uuid4()),
                    registration_id=reg.id,
                    participant_id=participant.id,
                    phone_number=participant.phone_number,
                    message_type=template_type.name,
                    template_name=template_type.value,
                    message_content=rendered.rendered_text,
                    provider=provider.provider_name,
                    idempotency_key=idempotency_key,
                    status="FAILED",
                    created_at=now,
                    failed_at=now,
                    error_message=error_msg[:500],
                    retry_count=1,
                )
                db.add(failed_msg)

            # Record FAILED in IntegrationLog
            log_q = select(IntegrationLog).where(
                and_(
                    IntegrationLog.registration_id == reg.id,
                    IntegrationLog.service_name == "WHATSAPP",
                    IntegrationLog.event_type == f"WHATSAPP_{template_type.name}",
                )
            )
            existing_log = (await db.execute(log_q)).scalars().first()
            if existing_log:
                existing_log.status = "FAILED"
                existing_log.error_message = error_msg[:500]
                existing_log.retry_count += 1
            else:
                log_entry = IntegrationLog(
                    id=str(uuid.uuid4()),
                    registration_id=reg.id,
                    service_name="WHATSAPP",
                    event_type=f"WHATSAPP_{template_type.name}",
                    status="FAILED",
                    retry_count=1,
                    request_payload=json.dumps({"template": template_type.value, "phone": participant.phone_number}),
                    error_message=error_msg[:500],
                )
                db.add(log_entry)

            await db.commit()

            return {
                "status": "FAILED",
                "error": error_msg,
                "retryable": not is_permanent,
                "template": template_type.value,
            }

    # Public Template Dispatchers
    async def send_registration_confirmation(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.REGISTRATION_CONFIRMATION)

    async def send_payment_confirmation(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.PAYMENT_CONFIRMATION)

    async def send_digital_pass(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.DIGITAL_PASS_BIB)

    async def send_reminder_7_days(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.REMINDER_7_DAYS)

    async def send_reminder_1_day(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.REMINDER_1_DAY)

    async def send_event_day_reminder(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.REMINDER_RACE_DAY)

    async def send_reminder_event_day(self, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, WhatsAppTemplateType.REMINDER_RACE_DAY)

    async def process_delivery_webhook(self, db: AsyncSession, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.whatsapp.delivery import delivery_handler
        return await delivery_handler.process_webhook_payload(db, webhook_payload)

    async def send_reminder(
        self,
        db: AsyncSession,
        registration_id: str,
        template_type: WhatsAppTemplateType,
    ) -> Dict[str, Any]:
        return await self._send_template_internal(db, registration_id, template_type)

    async def retry_failed_message(self, db: AsyncSession, message_id: str) -> Dict[str, Any]:
        """Retry a specific failed WhatsAppMessage record."""
        query = select(WhatsAppMessage).where(WhatsAppMessage.id == message_id)
        msg = (await db.execute(query)).scalar_one_or_none()
        if not msg:
            return {"status": "FAILED", "error": "Message record not found", "retryable": False}

        try:
            tpl_enum = WhatsAppTemplateType(msg.template_name)
        except Exception:
            return {"status": "FAILED", "error": f"Invalid template: {msg.template_name}", "retryable": False}

        # Clear failed status to allow resend
        msg.status = "PENDING"
        await db.commit()

        return await self._send_template_internal(db, msg.registration_id, tpl_enum)

    async def retry_failed_messages(self, db: AsyncSession, limit: int = 50) -> Dict[str, Any]:
        """Batch retry all failed WhatsApp messages."""
        query = (
            select(WhatsAppMessage)
            .where(WhatsAppMessage.status == "FAILED")
            .order_by(WhatsAppMessage.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(query)
        failed_records = res.scalars().all()

        results = []
        for msg in failed_records:
            retry_res = await self.retry_failed_message(db=db, message_id=msg.id)
            results.append({"message_id": msg.id, "result": retry_res})

        successful = sum(1 for r in results if r["result"].get("status") == "SUCCESS")
        failed = sum(1 for r in results if r["result"].get("status") == "FAILED")

        return {
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "details": results,
        }

    async def get_communication_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Aggregate message delivery metrics for Admin Dashboard."""
        total = (await db.execute(select(func.count(WhatsAppMessage.id)))).scalar_one() or 0
        pending = (await db.execute(select(func.count(WhatsAppMessage.id)).where(WhatsAppMessage.status == "PENDING"))).scalar_one() or 0
        sent = (await db.execute(select(func.count(WhatsAppMessage.id)).where(WhatsAppMessage.status == "SENT"))).scalar_one() or 0
        delivered = (await db.execute(select(func.count(WhatsAppMessage.id)).where(WhatsAppMessage.status == "DELIVERED"))).scalar_one() or 0
        read = (await db.execute(select(func.count(WhatsAppMessage.id)).where(WhatsAppMessage.status == "READ"))).scalar_one() or 0
        failed = (await db.execute(select(func.count(WhatsAppMessage.id)).where(WhatsAppMessage.status == "FAILED"))).scalar_one() or 0

        provider_health = await self.get_provider().health_check()

        return {
            "total_messages": total,
            "pending_count": pending,
            "sent_count": sent,
            "delivered_count": delivered,
            "read_count": read,
            "failed_count": failed,
            "provider_health": provider_health,
        }

    async def get_messages_list(
        self,
        db: AsyncSession,
        registration_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """List filterable WhatsApp message records with pagination."""
        query = select(WhatsAppMessage)

        if registration_id:
            query = query.where(WhatsAppMessage.registration_id == registration_id)
        if phone_number:
            query = query.where(WhatsAppMessage.phone_number.contains(phone_number))
        if message_type:
            query = query.where(WhatsAppMessage.message_type == message_type)
        if status:
            query = query.where(WhatsAppMessage.status == status)

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar_one() or 0

        # Query items
        offset = (page - 1) * page_size
        items_q = query.order_by(WhatsAppMessage.created_at.desc()).offset(offset).limit(page_size)
        res = await db.execute(items_q)
        items = res.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": m.id,
                    "registration_id": m.registration_id,
                    "participant_id": m.participant_id,
                    "phone_number": m.phone_number,
                    "message_type": m.message_type,
                    "template_name": m.template_name,
                    "message_content": m.message_content,
                    "provider": m.provider,
                    "provider_message_id": m.provider_message_id,
                    "idempotency_key": m.idempotency_key,
                    "status": m.status,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                    "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
                    "read_at": m.read_at.isoformat() if m.read_at else None,
                    "failed_at": m.failed_at.isoformat() if m.failed_at else None,
                    "error_message": m.error_message,
                    "retry_count": m.retry_count,
                }
                for m in items
            ],
        }


whatsapp_service = WhatsAppService()
