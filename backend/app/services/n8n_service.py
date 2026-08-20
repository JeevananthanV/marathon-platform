import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.integrations.n8n import n8n_client
from app.core.config import settings
from app.core.logging import logger


class N8NAutomationService:
    """
    Business service orchestrating outbound webhook event dispatches from the FastAPI backend to n8n.
    Maintains the backend/PostgreSQL database as the single source of truth while providing
    idempotent event envelopes, reminder eligibility filtering, and non-blocking safety.
    """

    @staticmethod
    async def _check_idempotency(
        db: AsyncSession,
        registration_id: str,
        event_type: str,
    ) -> Optional[IntegrationLog]:
        """Check if this specific n8n event was already successfully dispatched."""
        query = select(IntegrationLog).where(
            and_(
                IntegrationLog.registration_id == registration_id,
                IntegrationLog.service_name == "N8N",
                IntegrationLog.event_type == event_type,
                IntegrationLog.status == "SUCCESS",
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def _dispatch_event_internal(
        cls,
        db: AsyncSession,
        registration_id: str,
        event_name: str,
        payload_builder: Any,
    ) -> Dict[str, Any]:
        """Internal dispatch routine ensuring idempotency, audit logging, and payment isolation."""
        event_type = f"N8N_{event_name.upper().replace('.', '_')}"
        idempotency_key = f"n8n:{event_name}:{registration_id}"

        # 1. Idempotency Check
        prior_log = await cls._check_idempotency(db, registration_id, event_type)
        if prior_log:
            logger.info(f"[N8N IDEMPOTENCY] Skipped duplicate dispatch for {idempotency_key}.")
            prior_payload = json.loads(prior_log.response_payload) if prior_log.response_payload else {}
            return {
                "status": "SUCCESS",
                "idempotent": True,
                "event": event_name,
                "event_id": prior_payload.get("event_id"),
                "execution_id": prior_payload.get("execution_id"),
                "message": "Event already dispatched to n8n previously.",
            }

        # 2. Query Registration Entity
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
            logger.warning(f"[N8N SERVICE] Registration '{registration_id}' not found.")
            return {"status": "FAILED", "error": "Registration not found", "retryable": False}

        # 3. Assemble Clean Event Payload
        event_payload = payload_builder(reg)

        # 4. Dispatch to n8n Client
        try:
            res = await n8n_client.trigger_event(
                event_name=event_name,
                payload=event_payload,
                idempotency_key=idempotency_key,
            )

            # Record SUCCESS in IntegrationLog
            log_entry = IntegrationLog(
                id=str(uuid.uuid4()),
                registration_id=reg.id,
                service_name="N8N",
                event_type=event_type,
                status="SUCCESS",
                retry_count=0,
                request_payload=json.dumps({"event": event_name, "payload": event_payload}, default=str),
                response_payload=json.dumps(res, default=str),
            )
            db.add(log_entry)
            await db.commit()

            return {
                "status": "SUCCESS",
                "event": event_name,
                "event_id": res.get("event_id"),
                "execution_id": res.get("execution_id"),
                "service": "N8N",
                "mock": res.get("mock", False),
            }

        except Exception as e:
            error_msg = str(e)
            is_permanent = "rejected" in error_msg.lower() or "400" in error_msg
            logger.error(f"[N8N SERVICE] Event dispatch failed for {event_name} ({reg.registration_code}): {error_msg}")

            # Record FAILED in IntegrationLog
            log_entry = IntegrationLog(
                id=str(uuid.uuid4()),
                registration_id=reg.id,
                service_name="N8N",
                event_type=event_type,
                status="FAILED",
                retry_count=1,
                request_payload=json.dumps({"event": event_name, "payload": event_payload}, default=str),
                error_message=error_msg[:500],
            )
            db.add(log_entry)
            await db.commit()

            return {
                "status": "FAILED",
                "event": event_name,
                "error": error_msg,
                "retryable": not is_permanent,
            }

    # Public Event Dispatchers
    @classmethod
    async def dispatch_registration_confirmed(cls, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        def build_payload(reg: Registration) -> Dict[str, Any]:
            p = reg.participant
            c = reg.category
            return {
                "registration_id": reg.id,
                "registration_code": reg.registration_code,
                "bib_number": reg.bib_number,
                "status": reg.status,
                "event_name": settings.EVENT_NAME,
                "event_date": settings.EVENT_DATE,
                "participant": {
                    "full_name": p.full_name,
                    "email": p.email,
                    "phone": p.phone_number,
                    "city": p.city,
                    "state": p.state,
                    "gender": p.gender,
                    "tshirt_size": p.tshirt_size,
                },
                "race": {
                    "code": c.code,
                    "title": c.title,
                    "distance_km": c.distance_km,
                    "start_time": c.start_time,
                },
                "tracking": {
                    "utm_source": reg.utm_source,
                    "utm_medium": reg.utm_medium,
                    "utm_campaign": reg.utm_campaign,
                },
            }

        return await cls._dispatch_event_internal(db, registration_id, "registration.confirmed", build_payload)

    @classmethod
    async def dispatch_payment_captured(
        cls,
        db: AsyncSession,
        registration_id: str,
        payment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        def build_payload(reg: Registration) -> Dict[str, Any]:
            payment = reg.payments[0] if reg.payments else None
            return {
                "registration_id": reg.id,
                "registration_code": reg.registration_code,
                "payment_id": payment_id or (payment.razorpay_payment_id if payment else "mock_pay_id"),
                "order_id": payment.razorpay_order_id if payment else "mock_order_id",
                "amount_inr": float(payment.amount_inr) if payment else float(reg.category.price_inr),
                "currency": "INR",
                "status": "SUCCESS",
                "captured_at": payment.captured_at.isoformat() if payment and payment.captured_at else datetime.now(timezone.utc).isoformat(),
            }

        return await cls._dispatch_event_internal(db, registration_id, "payment.captured", build_payload)

    @classmethod
    async def dispatch_bib_assigned(cls, db: AsyncSession, registration_id: str) -> Dict[str, Any]:
        def build_payload(reg: Registration) -> Dict[str, Any]:
            return {
                "registration_id": reg.id,
                "registration_code": reg.registration_code,
                "bib_number": reg.bib_number or "ASSIGNED",
                "category_title": reg.category.title,
                "venue": settings.EVENT_VENUE,
                "reporting_time": settings.EVENT_REPORTING_TIME,
                "participant_name": reg.participant.full_name,
                "phone": reg.participant.phone_number,
            }

        return await cls._dispatch_event_internal(db, registration_id, "bib.assigned", build_payload)

    @classmethod
    async def dispatch_reminder(
        cls,
        db: AsyncSession,
        registration_id: str,
        reminder_type: str,
    ) -> Dict[str, Any]:
        """
        Dispatch a pre-marathon reminder event (7_days, 1_day, event_day).
        STRICT ELIGIBILITY: Only CONFIRMED registrations are eligible.
        """
        # Eligibility Verification: Must be CONFIRMED
        q = select(Registration).where(Registration.id == registration_id)
        res = await db.execute(q)
        reg = res.scalar_one_or_none()

        if not reg or reg.status != "CONFIRMED":
            logger.warning(f"[N8N REMINDER] Registration '{registration_id}' is not CONFIRMED. Excluded from reminders.")
            return {
                "status": "SKIPPED",
                "eligible": False,
                "reason": "Participant registration is not CONFIRMED",
                "event": f"reminder.{reminder_type}",
            }

        def build_payload(r: Registration) -> Dict[str, Any]:
            return {
                "registration_id": r.id,
                "registration_code": r.registration_code,
                "bib_number": r.bib_number,
                "reminder_type": reminder_type,
                "event_name": settings.EVENT_NAME,
                "event_date": settings.EVENT_DATE,
                "event_venue": settings.EVENT_VENUE,
                "reporting_time": settings.EVENT_REPORTING_TIME,
                "participant": {
                    "full_name": r.participant.full_name,
                    "email": r.participant.email,
                    "phone": r.participant.phone_number,
                },
                "category": r.category.title,
            }

        return await cls._dispatch_event_internal(db, registration_id, f"reminder.{reminder_type}", build_payload)

    @classmethod
    async def get_eligible_reminder_participants(
        cls,
        db: AsyncSession,
        reminder_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Query eligible participants for n8n scheduled reminder workflows.
        Filters strictly for CONFIRMED status.
        """
        query = (
            select(Registration)
            .options(
                selectinload(Registration.participant),
                selectinload(Registration.category),
            )
            .where(Registration.status == "CONFIRMED")
        )
        result = await db.execute(query)
        confirmed_regs = result.scalars().all()

        participants_list = []
        for r in confirmed_regs:
            participants_list.append({
                "registration_id": r.id,
                "registration_code": r.registration_code,
                "bib_number": r.bib_number,
                "full_name": r.participant.full_name,
                "email": r.participant.email,
                "phone": r.participant.phone_number,
                "category": r.category.title,
                "status": r.status,
            })

        return participants_list

    @classmethod
    async def retry_failed_n8n_events(
        cls,
        db: AsyncSession,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retry failed n8n webhook event dispatches."""
        query = select(IntegrationLog).where(
            and_(
                IntegrationLog.service_name == "N8N",
                IntegrationLog.status == "FAILED",
                IntegrationLog.retry_count < max_retries,
            )
        )
        result = await db.execute(query)
        failed_logs = result.scalars().all()

        reg_events = [(log.registration_id, log.event_type) for log in failed_logs]
        retry_results = []

        for reg_id, event_type in reg_events:
            event_name = event_type.replace("N8N_", "").lower().replace("_", ".")
            if event_name == "registration.confirmed":
                res = await cls.dispatch_registration_confirmed(db, reg_id)
            elif event_name == "payment.captured":
                res = await cls.dispatch_payment_captured(db, reg_id)
            elif event_name == "bib.assigned":
                res = await cls.dispatch_bib_assigned(db, reg_id)
            elif event_name.startswith("reminder."):
                rem_type = event_name.replace("reminder.", "")
                res = await cls.dispatch_reminder(db, reg_id, rem_type)
            else:
                continue

            retry_results.append({"registration_id": reg_id, "event": event_name, "result": res})

        return retry_results


n8n_service = N8NAutomationService()
