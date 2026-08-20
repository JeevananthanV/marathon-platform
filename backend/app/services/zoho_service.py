import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.integrations.zoho_crm import zoho_client
from app.core.logging import logger


class ZohoCRMService:
    """
    Business service for synchronizing marathon registrations with Zoho CRM (Phase 5).
    
    Guarantees:
    1. Safe Decoupling: Zoho failures NEVER roll back or alter registration / payment status.
    2. Duplicate Prevention: Performs search-before-create by email.
    3. Idempotency: Duplicate calls update existing CRM records without creating new ones.
    4. Audit Logging: Updates/records audit logs in `integration_logs`.
    5. Sync Status Tracking: Updates `zoho_sync_status`, `zoho_last_sync_attempt`, `zoho_last_successful_sync`.
    """

    @classmethod
    async def sync_registration_to_zoho(
        cls,
        db: AsyncSession,
        registration_id: str,
    ) -> Dict[str, Any]:
        """
        Synchronize a registration record to Zoho CRM safely and idempotently.
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
        result = await db.execute(query)
        registration = result.scalar_one_or_none()

        if not registration:
            logger.warning(f"[ZOHO SERVICE] Registration '{registration_id}' not found.")
            return {"status": "FAILED", "registration_id": registration_id, "error": "Registration not found", "retryable": False}

        participant = registration.participant
        category = registration.category
        latest_payment = registration.payments[0] if registration.payments else None
        now = datetime.now(timezone.utc)

        # Update attempt tracking
        registration.zoho_last_sync_attempt = now
        if registration.zoho_sync_status == "FAILED":
            registration.zoho_retry_count = (registration.zoho_retry_count or 0) + 1

        participant_data = {
            "full_name": participant.full_name,
            "email": participant.email,
            "phone_number": participant.phone_number,
            "date_of_birth": participant.date_of_birth.isoformat() if hasattr(participant.date_of_birth, "isoformat") else str(participant.date_of_birth),
            "gender": participant.gender,
            "blood_group": participant.blood_group,
            "tshirt_size": participant.tshirt_size,
            "emergency_contact_name": participant.emergency_contact_name,
            "emergency_contact_phone": participant.emergency_contact_phone,
            "city": participant.city,
            "state": participant.state,
        }

        registration_data = {
            "registration_code": registration.registration_code,
            "bib_number": registration.bib_number or registration.registration_code,
            "category_title": category.title if category else "Marathon",
            "category_code": category.code if category else "",
            "amount_inr": float(latest_payment.amount_inr) if latest_payment else (float(category.price_inr) if category else 0.0),
            "status": registration.status,
            "payment_status": latest_payment.status if latest_payment else ("SUCCESS" if registration.status == "CONFIRMED" else "PENDING"),
        }

        utm_data = {
            "utm_source": registration.utm_source,
            "utm_medium": registration.utm_medium,
            "utm_campaign": registration.utm_campaign,
            "utm_content": registration.utm_content,
            "utm_term": registration.utm_term,
            "referrer": registration.referrer,
        }

        request_payload_snapshot = {
            "participant": participant_data,
            "registration": registration_data,
            "utm": utm_data,
        }

        try:
            # Synchronize with Zoho CRM via integration client
            res = await zoho_client.sync_participant_lead(
                participant_data=participant_data,
                registration_data=registration_data,
                utm_data=utm_data,
                idempotency_key=registration.registration_code,
            )

            zoho_record_id = res.get("zoho_record_id")
            if zoho_record_id and participant:
                participant.zoho_lead_id = zoho_record_id

            # Mark status as SYNCED
            registration.zoho_sync_status = "SYNCED"
            registration.zoho_last_successful_sync = now
            registration.zoho_error_message = None

            # Upsert in IntegrationLog
            log_q = select(IntegrationLog).where(
                and_(
                    IntegrationLog.registration_id == registration.id,
                    IntegrationLog.service_name == "ZOHO_CRM",
                )
            )
            existing_log = (await db.execute(log_q)).scalars().first()

            if existing_log:
                existing_log.status = "SUCCESS"
                existing_log.retry_count = registration.zoho_retry_count or 0
                existing_log.request_payload = json.dumps(request_payload_snapshot)
                existing_log.response_payload = json.dumps(res)
                existing_log.error_message = None
            else:
                log_entry = IntegrationLog(
                    id=str(uuid.uuid4()),
                    registration_id=registration.id,
                    service_name="ZOHO_CRM",
                    event_type="ZOHO_LEAD_SYNC",
                    status="SUCCESS",
                    retry_count=0,
                    request_payload=json.dumps(request_payload_snapshot),
                    response_payload=json.dumps(res),
                    error_message=None,
                )
                db.add(log_entry)

            await db.commit()

            logger.info(
                f"[ZOHO SUCCESS] Synced Reg {registration.registration_code} -> Zoho ID: {zoho_record_id}"
            )
            return {
                "status": "SUCCESS",
                "registration_id": registration.id,
                "registration_code": registration.registration_code,
                "zoho_record_id": zoho_record_id,
                "action": res.get("action", "synced"),
                "mock": res.get("mock", False),
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[ZOHO ERROR] Failed to sync {registration.registration_code}: {error_msg}")

            # Mark status as FAILED in Registration record
            registration.zoho_sync_status = "FAILED"
            registration.zoho_error_message = error_msg[:500]

            # Upsert in IntegrationLog
            log_q = select(IntegrationLog).where(
                and_(
                    IntegrationLog.registration_id == registration.id,
                    IntegrationLog.service_name == "ZOHO_CRM",
                )
            )
            existing_log = (await db.execute(log_q)).scalars().first()

            if existing_log:
                existing_log.status = "FAILED"
                existing_log.retry_count = registration.zoho_retry_count or 0
                existing_log.request_payload = json.dumps(request_payload_snapshot)
                existing_log.response_payload = None
                existing_log.error_message = error_msg[:500]
            else:
                log_entry = IntegrationLog(
                    id=str(uuid.uuid4()),
                    registration_id=registration.id,
                    service_name="ZOHO_CRM",
                    event_type="ZOHO_LEAD_SYNC",
                    status="FAILED",
                    retry_count=registration.zoho_retry_count or 0,
                    request_payload=json.dumps(request_payload_snapshot),
                    response_payload=None,
                    error_message=error_msg[:500],
                )
                db.add(log_entry)

            await db.commit()

            return {
                "status": "FAILED",
                "registration_id": registration.id,
                "registration_code": registration.registration_code,
                "error": error_msg,
                "retryable": True,
            }

    @classmethod
    async def retry_failed_zoho_syncs(
        cls,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Query and retry synchronization for registrations with FAILED or PENDING Zoho status.
        Returns a list of sync result dictionaries.
        """
        query = (
            select(Registration.id)
            .where(Registration.zoho_sync_status.in_(["FAILED", "PENDING"]))
            .order_by(Registration.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(query)
        reg_ids = res.scalars().all()

        details = []
        for r_id in reg_ids:
            sync_res = await cls.sync_registration_to_zoho(db=db, registration_id=r_id)
            details.append(sync_res)

        return details

    @classmethod
    async def get_zoho_status_summary(
        cls,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Get Zoho CRM synchronization counts and health status for Admin Dashboard.
        """
        # Count by sync status
        total_synced = (
            await db.execute(
                select(func.count(Registration.id)).where(Registration.zoho_sync_status == "SYNCED")
            )
        ).scalar_one() or 0

        total_pending = (
            await db.execute(
                select(func.count(Registration.id)).where(Registration.zoho_sync_status == "PENDING")
            )
        ).scalar_one() or 0

        total_failed = (
            await db.execute(
                select(func.count(Registration.id)).where(Registration.zoho_sync_status == "FAILED")
            )
        ).scalar_one() or 0

        # Latest sync attempt
        last_sync = (
            await db.execute(
                select(func.max(Registration.zoho_last_sync_attempt))
            )
        ).scalar_one_or_none()

        health = await zoho_client.health_check()

        return {
            "mode": health["mode"], # "mock" or "live"
            "configured": health["configured"],
            "status": health["status"],
            "synced_count": total_synced,
            "pending_count": total_pending,
            "failed_count": total_failed,
            "last_sync_attempt": last_sync.isoformat() if last_sync else None,
            "health": health,
        }


zoho_service = ZohoCRMService()
