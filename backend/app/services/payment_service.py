import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.payment import Payment
from app.models.registration import Registration
from app.models.race_category import RaceCategory
from app.models.participant import Participant
from app.integrations.razorpay_client import razorpay_client
from app.services.registration_service import allocate_bib_number
from app.services.zoho_service import zoho_service
from app.services.whatsapp_service import whatsapp_service
from app.services.n8n_service import n8n_service
from app.services.meta_capi_service import meta_capi_service
from app.core.logging import logger


class PaymentService:

    @staticmethod
    async def verify_payment(
        db: AsyncSession,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Dict[str, Any]:
        """
        Verify Razorpay payment signature server-side.
        Transitions Payment to SUCCESS and Registration to CONFIRMED.
        Allocates BIB number atomically and dispatches non-blocking Zoho CRM, WhatsApp, n8n, and Meta CAPI syncs.
        """
        # 1. Fetch Payment and related Registration
        query = (
            select(Payment)
            .options(
                selectinload(Payment.registration).selectinload(Registration.category),
                selectinload(Payment.registration).selectinload(Registration.participant),
            )
            .where(Payment.razorpay_order_id == razorpay_order_id)
        )
        result = await db.execute(query)
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No payment order found matching order_id '{razorpay_order_id}'.",
            )

        registration = payment.registration
        category = registration.category
        participant = registration.participant

        # 2. Idempotency Check: If already confirmed, return success immediately
        if registration.status == "CONFIRMED" and payment.status == "SUCCESS":
            logger.info(f"Payment already verified and confirmed for {registration.registration_code}")
            return {
                "status": "CONFIRMED",
                "registration_code": registration.registration_code,
                "bib_number": registration.bib_number or "ASSIGNED",
                "participant_name": participant.full_name,
                "category_title": category.title,
                "message": "Registration is confirmed.",
            }

        # 3. Cryptographic Signature Verification
        is_valid = razorpay_client.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not is_valid:
            logger.warning(
                f"Signature verification failed for order {razorpay_order_id} | payment {razorpay_payment_id}"
            )
            payment.status = "FAILED"
            payment.error_code = "BAD_REQUEST_ERROR"
            payment.error_description = "Server-side payment signature verification failed."
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature. Payment verification failed.",
            )

        # 4. Successful Verification: Update Payment & Confirm Registration
        now = datetime.now(timezone.utc)
        payment.status = "SUCCESS"
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.captured_at = now

        # Allocate Bib Number if not already allocated
        if not registration.bib_number:
            bib = await allocate_bib_number(db, category)
            registration.bib_number = bib
            category.current_count += 1

        registration.status = "CONFIRMED"
        registration.confirmed_at = now
        participant.lead_status = "CONVERTED"

        await db.commit()

        logger.info(
            f"Payment Verified: {razorpay_payment_id} | Order: {razorpay_order_id} | "
            f"Reg: {registration.registration_code} | Bib: {registration.bib_number}"
        )

        # 5. Non-Blocking Zoho CRM Synchronization
        try:
            await zoho_service.sync_registration_to_zoho(db=db, registration_id=registration.id)
        except Exception as zoho_err:
            logger.error(f"[Payment -> Zoho] Non-fatal Zoho sync exception: {str(zoho_err)}")

        # 6. Non-Blocking WhatsApp Pass & Confirmation Dispatch
        try:
            await whatsapp_service.send_registration_confirmation(db=db, registration_id=registration.id)
            await whatsapp_service.send_payment_confirmation(db=db, registration_id=registration.id)
        except Exception as wa_err:
            logger.error(f"[Payment -> WhatsApp] Non-fatal WhatsApp dispatch exception: {str(wa_err)}")

        # 7. Non-Blocking n8n Orchestration Event Dispatch
        try:
            await n8n_service.dispatch_registration_confirmed(db=db, registration_id=registration.id)
            await n8n_service.dispatch_payment_captured(db=db, registration_id=registration.id, payment_id=razorpay_payment_id)
            await n8n_service.dispatch_bib_assigned(db=db, registration_id=registration.id)
        except Exception as n8n_err:
            logger.error(f"[Payment -> n8n] Non-fatal n8n dispatch exception: {str(n8n_err)}")

        # 8. Non-Blocking Meta Conversions API (Purchase & CompleteRegistration)
        try:
            await meta_capi_service.track_purchase(db=db, registration_id=registration.id, payment_id=razorpay_payment_id)
            await meta_capi_service.track_complete_registration(db=db, registration_id=registration.id)
        except Exception as meta_err:
            logger.error(f"[Payment -> Meta CAPI] Non-fatal Meta CAPI dispatch exception: {str(meta_err)}")

        return {
            "status": "CONFIRMED",
            "registration_code": registration.registration_code,
            "bib_number": registration.bib_number,
            "participant_name": participant.full_name,
            "category_title": category.title,
            "message": "Payment verified successfully. Marathon registration confirmed!",
        }

    @staticmethod
    async def process_webhook(
        db: AsyncSession,
        raw_body: bytes,
        signature: str,
        webhook_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process Razorpay webhook event with HMAC authenticity verification and strict idempotency.
        """
        # 1. Verify Webhook Signature
        is_authentic = razorpay_client.verify_webhook_signature(
            raw_body=raw_body,
            signature=signature,
            webhook_secret=webhook_secret,
        )

        if not is_authentic:
            logger.error("Razorpay webhook signature verification failed.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature.",
            )

        # 2. Parse Event Payload
        try:
            event_payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed JSON in webhook body: {str(e)}",
            )

        event_name = event_payload.get("event")
        payload_data = event_payload.get("payload", {})
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_entity = payload_data.get("order", {}).get("entity", {})

        razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")
        razorpay_payment_id = payment_entity.get("id")

        logger.info(f"Received Razorpay webhook event: {event_name} | Order: {razorpay_order_id}")

        if not razorpay_order_id:
            return {"status": "ignored", "reason": "No order_id found in webhook payload"}

        # 3. Fetch Payment and Registration
        query = (
            select(Payment)
            .options(
                selectinload(Payment.registration).selectinload(Registration.category),
                selectinload(Payment.registration).selectinload(Registration.participant),
            )
            .where(Payment.razorpay_order_id == razorpay_order_id)
        )
        result = await db.execute(query)
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"Webhook received for unknown order_id: {razorpay_order_id}")
            return {"status": "ignored", "reason": f"Order {razorpay_order_id} not found in database"}

        registration = payment.registration
        category = registration.category
        participant = registration.participant

        # 4. Handle Event Types
        now = datetime.now(timezone.utc)
        payment.raw_webhook_payload = json.dumps(event_payload)

        if event_name in ["payment.captured", "order.paid"]:
            # Idempotency Check: If already confirmed, acknowledge without reprocessing
            if registration.status == "CONFIRMED" and payment.status == "SUCCESS":
                logger.info(f"Webhook event '{event_name}' already processed for {registration.registration_code}")
                return {
                    "status": "already_processed",
                    "registration_code": registration.registration_code,
                    "idempotency": True,
                }

            # Update Payment & Registration
            payment.status = "SUCCESS"
            if razorpay_payment_id:
                payment.razorpay_payment_id = razorpay_payment_id
            payment.captured_at = now

            if not registration.bib_number:
                registration.bib_number = await allocate_bib_number(db, category)
                category.current_count += 1

            registration.status = "CONFIRMED"
            registration.confirmed_at = now
            participant.lead_status = "CONVERTED"

            await db.commit()

            # Non-blocking Zoho sync dispatch
            try:
                await zoho_service.sync_registration_to_zoho(db=db, registration_id=registration.id)
            except Exception as zoho_err:
                logger.error(f"[Webhook -> Zoho] Non-fatal Zoho sync exception: {str(zoho_err)}")

            # Non-blocking WhatsApp pass & confirmation dispatch
            try:
                await whatsapp_service.send_registration_confirmation(db=db, registration_id=registration.id)
                await whatsapp_service.send_payment_confirmation(db=db, registration_id=registration.id)
            except Exception as wa_err:
                logger.error(f"[Webhook -> WhatsApp] Non-fatal WhatsApp dispatch exception: {str(wa_err)}")

            # Non-blocking n8n event dispatch
            try:
                await n8n_service.dispatch_registration_confirmed(db=db, registration_id=registration.id)
                await n8n_service.dispatch_payment_captured(db=db, registration_id=registration.id, payment_id=razorpay_payment_id)
                await n8n_service.dispatch_bib_assigned(db=db, registration_id=registration.id)
            except Exception as n8n_err:
                logger.error(f"[Webhook -> n8n] Non-fatal n8n dispatch exception: {str(n8n_err)}")

            # Non-blocking Meta Conversions API (Purchase & CompleteRegistration)
            try:
                await meta_capi_service.track_purchase(db=db, registration_id=registration.id, payment_id=razorpay_payment_id)
                await meta_capi_service.track_complete_registration(db=db, registration_id=registration.id)
            except Exception as meta_err:
                logger.error(f"[Webhook -> Meta CAPI] Non-fatal Meta CAPI dispatch exception: {str(meta_err)}")

            logger.info(f"Webhook successfully confirmed registration: {registration.registration_code}")
            return {
                "status": "processed",
                "event": event_name,
                "registration_code": registration.registration_code,
                "bib_number": registration.bib_number,
            }

        elif event_name == "payment.failed":
            error_code = payment_entity.get("error_code")
            error_desc = payment_entity.get("error_description")
            payment.status = "FAILED"
            payment.error_code = error_code
            payment.error_description = error_desc
            await db.commit()
            logger.warning(f"Payment failed webhook received for {razorpay_order_id}: {error_desc}")
            return {"status": "payment_failed_recorded", "error": error_desc}

        return {"status": "acknowledged", "event": event_name}
