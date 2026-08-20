import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.participant import Participant
from app.models.payment import Payment
from app.models.integration_log import IntegrationLog
from app.integrations.meta_capi import meta_capi_client
from app.core.config import settings
from app.core.logging import logger


class MetaCAPIService:
    """
    Business service orchestrating server-side Meta Conversions API events.
    Manages customer matching hashing, conversion deduplication (event_id),
    UTM ad attribution preservation, and non-blocking payment safety.
    """

    @staticmethod
    async def _check_idempotency(
        db: AsyncSession,
        registration_id: Optional[str],
        event_type: str,
    ) -> Optional[IntegrationLog]:
        """Check if this Meta event was already successfully sent for this entity."""
        if not registration_id:
            return None
        query = select(IntegrationLog).where(
            and_(
                IntegrationLog.registration_id == registration_id,
                IntegrationLog.service_name == "META_CAPI",
                IntegrationLog.event_type == event_type,
                IntegrationLog.status == "SUCCESS",
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def _send_event_internal(
        cls,
        db: AsyncSession,
        event_name: str,
        event_id: str,
        user_data: Dict[str, Any],
        custom_data: Optional[Dict[str, Any]] = None,
        registration_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Internal dispatch routine with idempotency check, logging, and error isolation."""
        event_type = f"META_{event_name.upper()}"

        # 1. Idempotency Check
        if registration_id:
            prior_log = await cls._check_idempotency(db, registration_id, event_type)
            if prior_log:
                logger.info(f"[META CAPI IDEMPOTENCY] Skipped duplicate event {event_name} for {event_id}.")
                return {
                    "status": "SUCCESS",
                    "idempotent": True,
                    "event_name": event_name,
                    "event_id": event_id,
                    "message": "Event already recorded in Meta CAPI.",
                }

        # 2. Dispatch to Meta Integration Client
        try:
            res = await meta_capi_client.send_event(
                event_name=event_name,
                event_id=event_id,
                user_data=user_data,
                custom_data=custom_data,
                event_source_url=event_source_url,
            )

            # Record SUCCESS in IntegrationLog
            log_entry = IntegrationLog(
                id=str(uuid.uuid4()),
                registration_id=registration_id,
                service_name="META_CAPI",
                event_type=event_type,
                status="SUCCESS",
                retry_count=0,
                request_payload=json.dumps({
                    "event_name": event_name,
                    "event_id": event_id,
                    "custom_data": custom_data,
                }, default=str),
                response_payload=json.dumps(res, default=str),
            )
            db.add(log_entry)
            await db.commit()

            return {
                "status": "SUCCESS",
                "event_name": event_name,
                "event_id": event_id,
                "service": "META_CAPI",
                "mock": res.get("mock", False),
            }

        except Exception as e:
            error_msg = str(e)
            is_permanent = "rejected" in error_msg.lower() or "400" in error_msg
            logger.error(f"[META CAPI SERVICE] Failed tracking {event_name} ({event_id}): {error_msg}")

            # Record FAILED in IntegrationLog
            log_entry = IntegrationLog(
                id=str(uuid.uuid4()),
                registration_id=registration_id,
                service_name="META_CAPI",
                event_type=event_type,
                status="FAILED",
                retry_count=1,
                request_payload=json.dumps({"event_name": event_name, "event_id": event_id}),
                error_message=error_msg[:500],
            )
            db.add(log_entry)
            await db.commit()

            return {
                "status": "FAILED",
                "event_name": event_name,
                "error": error_msg,
                "retryable": not is_permanent,
            }

    # Public Meta Funnel Trackers
    @classmethod
    async def track_page_view(
        cls,
        db: AsyncSession,
        session_id: str,
        url: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_id = f"pageview_{session_id}_{int(datetime.now(timezone.utc).timestamp())}"
        user_data = meta_capi_client.build_user_data(client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp)
        return await cls._send_event_internal(
            db=db,
            event_name="PageView",
            event_id=event_id,
            user_data=user_data,
            event_source_url=url,
        )

    @classmethod
    async def track_view_content(
        cls,
        db: AsyncSession,
        category_code: str,
        category_title: str,
        price_inr: float,
        session_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_id = f"viewcontent_{category_code}_{session_id}"
        user_data = meta_capi_client.build_user_data(client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp)
        custom_data = {
            "content_name": category_title,
            "content_category": "Marathon Race Category",
            "content_ids": [category_code],
            "content_type": "product",
            "value": float(price_inr),
            "currency": "INR",
        }
        return await cls._send_event_internal(
            db=db,
            event_name="ViewContent",
            event_id=event_id,
            user_data=user_data,
            custom_data=custom_data,
        )

    @classmethod
    async def track_lead(
        cls,
        db: AsyncSession,
        registration_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = select(Registration).options(selectinload(Registration.participant), selectinload(Registration.category)).where(Registration.id == registration_id)
        res = await db.execute(query)
        reg = res.scalar_one_or_none()
        if not reg:
            return {"status": "FAILED", "error": "Registration not found"}

        p = reg.participant
        c = reg.category
        event_id = f"lead_{reg.registration_code}"
        user_data = meta_capi_client.build_user_data(
            email=p.email, phone=p.phone_number, full_name=p.full_name,
            city=p.city, state=p.state, client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp
        )
        custom_data = {
            "content_name": c.title,
            "content_category": "Marathon Lead",
            "value": float(c.price_inr),
            "currency": "INR",
            "utm_source": reg.utm_source,
            "utm_campaign": reg.utm_campaign,
        }
        return await cls._send_event_internal(
            db=db,
            event_name="Lead",
            event_id=event_id,
            user_data=user_data,
            custom_data=custom_data,
            registration_id=reg.id,
        )

    @classmethod
    async def track_initiate_checkout(
        cls,
        db: AsyncSession,
        registration_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = select(Registration).options(selectinload(Registration.participant), selectinload(Registration.category)).where(Registration.id == registration_id)
        res = await db.execute(query)
        reg = res.scalar_one_or_none()
        if not reg:
            return {"status": "FAILED", "error": "Registration not found"}

        p = reg.participant
        c = reg.category
        event_id = f"initiate_checkout_{reg.registration_code}"
        user_data = meta_capi_client.build_user_data(
            email=p.email, phone=p.phone_number, full_name=p.full_name,
            city=p.city, state=p.state, client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp
        )
        custom_data = {
            "content_name": c.title,
            "content_category": "Marathon Registration Checkout",
            "content_ids": [c.code],
            "value": float(c.price_inr),
            "currency": "INR",
            "num_items": 1,
            "utm_source": reg.utm_source,
            "utm_campaign": reg.utm_campaign,
        }
        return await cls._send_event_internal(
            db=db,
            event_name="InitiateCheckout",
            event_id=event_id,
            user_data=user_data,
            custom_data=custom_data,
            registration_id=reg.id,
        )

    @classmethod
    async def track_complete_registration(
        cls,
        db: AsyncSession,
        registration_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = select(Registration).options(selectinload(Registration.participant), selectinload(Registration.category)).where(Registration.id == registration_id)
        res = await db.execute(query)
        reg = res.scalar_one_or_none()
        if not reg:
            return {"status": "FAILED", "error": "Registration not found"}

        p = reg.participant
        c = reg.category
        event_id = f"complete_registration_{reg.registration_code}"
        user_data = meta_capi_client.build_user_data(
            email=p.email, phone=p.phone_number, full_name=p.full_name,
            city=p.city, state=p.state, client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp
        )
        custom_data = {
            "content_name": c.title,
            "status": "CONFIRMED",
            "registration_code": reg.registration_code,
            "bib_number": reg.bib_number,
            "value": float(c.price_inr),
            "currency": "INR",
            "utm_source": reg.utm_source,
            "utm_campaign": reg.utm_campaign,
        }
        return await cls._send_event_internal(
            db=db,
            event_name="CompleteRegistration",
            event_id=event_id,
            user_data=user_data,
            custom_data=custom_data,
            registration_id=reg.id,
        )

    @classmethod
    async def track_purchase(
        cls,
        db: AsyncSession,
        registration_id: str,
        payment_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track verified Purchase event server-side.
        DETERMINISTIC DEDUPLICATION: event_id = purchase_{registration_code}_{payment_id}
        """
        query = (
            select(Registration)
            .options(
                selectinload(Registration.participant),
                selectinload(Registration.category),
                selectinload(Registration.payments),
            )
            .where(Registration.id == registration_id)
        )
        res = await db.execute(query)
        reg = res.scalar_one_or_none()
        if not reg:
            return {"status": "FAILED", "error": "Registration not found"}

        p = reg.participant
        c = reg.category
        payment = reg.payments[0] if reg.payments else None
        clean_pay_id = payment_id or (payment.razorpay_payment_id if payment else "pay_assigned")

        event_id = f"purchase_{reg.registration_code}_{clean_pay_id}"
        user_data = meta_capi_client.build_user_data(
            email=p.email, phone=p.phone_number, full_name=p.full_name,
            city=p.city, state=p.state, client_ip=client_ip, user_agent=user_agent, fbc=fbc, fbp=fbp
        )
        custom_data = {
            "content_name": c.title,
            "content_type": "product",
            "content_ids": [c.code],
            "value": float(payment.amount_inr) if payment else float(c.price_inr),
            "currency": "INR",
            "order_id": payment.razorpay_order_id if payment else reg.registration_code,
            "registration_code": reg.registration_code,
            "bib_number": reg.bib_number,
            "utm_source": reg.utm_source,
            "utm_medium": reg.utm_medium,
            "utm_campaign": reg.utm_campaign,
        }
        return await cls._send_event_internal(
            db=db,
            event_name="Purchase",
            event_id=event_id,
            user_data=user_data,
            custom_data=custom_data,
            registration_id=reg.id,
        )

    @classmethod
    async def retry_failed_meta_events(
        cls,
        db: AsyncSession,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retry failed Meta CAPI events without duplicating conversions."""
        query = select(IntegrationLog).where(
            and_(
                IntegrationLog.service_name == "META_CAPI",
                IntegrationLog.status == "FAILED",
                IntegrationLog.retry_count < max_retries,
            )
        )
        result = await db.execute(query)
        failed_logs = result.scalars().all()

        retry_results = []
        for log in failed_logs:
            if not log.registration_id:
                continue
            event_name = log.event_type.replace("META_", "").title()
            if event_name == "Purchase":
                res = await cls.track_purchase(db, log.registration_id)
            elif event_name == "Completeregistration":
                res = await cls.track_complete_registration(db, log.registration_id)
            elif event_name == "Lead":
                res = await cls.track_lead(db, log.registration_id)
            elif event_name == "Initiatecheckout":
                res = await cls.track_initiate_checkout(db, log.registration_id)
            else:
                continue

            retry_results.append({"registration_id": log.registration_id, "event": event_name, "result": res})

        return retry_results


meta_capi_service = MetaCAPIService()
