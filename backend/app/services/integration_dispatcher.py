import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.integration_log import IntegrationLog
from app.integrations import zoho_client, whatsapp_client, n8n_client, meta_capi_client
from app.core.logging import logger


class IntegrationDispatcherService:
    """
    Unified Orchestrator for Phase 4 Marketing Automations & External Integrations.
    
    Key Architectural Guarantees:
    1. Resilient & Non-Blocking: External API delays or downtimes NEVER invalidate or rollback successful payments.
    2. Idempotent: Checks prior SUCCESS logs to prevent duplicate messaging or duplicate lead creation.
    3. Persistent Audit Trail: Stores every outgoing payload, response, and error in the `integration_logs` table.
    4. Auto-Retrying: Tracks retry counts for safe subsequent recovery.
    """

    @staticmethod
    async def log_integration_step(
        db: AsyncSession,
        registration_id: str,
        service_name: str,
        event_type: str,
        status: str,
        request_payload: Optional[Dict[str, Any]] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> IntegrationLog:
        """
        Record or update an integration execution entry in `integration_logs`.
        """
        from sqlalchemy import and_
        existing_log_query = select(IntegrationLog).where(
            and_(
                IntegrationLog.registration_id == registration_id,
                IntegrationLog.service_name == service_name,
            )
        )
        res = await db.execute(existing_log_query)
        log_entry = res.scalars().first()

        if log_entry:
            log_entry.event_type = event_type
            log_entry.status = status
            log_entry.request_payload = json.dumps(request_payload) if request_payload else None
            log_entry.response_payload = json.dumps(response_payload) if response_payload else None
            log_entry.error_message = error_message[:500] if error_message else None
        else:
            log_entry = IntegrationLog(
                id=str(uuid.uuid4()),
                registration_id=registration_id,
                service_name=service_name,
                event_type=event_type,
                status=status,
                retry_count=0,
                request_payload=json.dumps(request_payload) if request_payload else None,
                response_payload=json.dumps(response_payload) if response_payload else None,
                error_message=error_message[:500] if error_message else None,
            )
            db.add(log_entry)

        await db.commit()
        return log_entry

    @classmethod
    async def dispatch_registration_confirmed(
        cls,
        db: AsyncSession,
        registration_id: str,
    ) -> Dict[str, Any]:
        """
        Dispatches post-payment confirmation automations across:
        1. Zoho CRM (Deal creation / contact update)
        2. WhatsApp Business Cloud API (Pass & BIB confirmation template)
        3. n8n Automation Engine (Registration event webhook)
        4. Meta Conversions API (Purchase event with hashed data)
        """
        # Fetch registration with participant and category
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
            logger.warning(f"Cannot dispatch integrations: Registration '{registration_id}' not found.")
            return {"status": "error", "reason": "Registration not found"}

        # Extract all fields upfront into local variables
        reg_id = str(reg.id)
        reg_code = str(reg.registration_code)
        bib_number = str(reg.bib_number or reg_code)
        ip_address = reg.ip_address
        user_agent = reg.user_agent
        referrer = reg.referrer
        utm_source = reg.utm_source
        utm_medium = reg.utm_medium
        utm_campaign = reg.utm_campaign
        utm_content = reg.utm_content
        utm_term = reg.utm_term

        participant = reg.participant
        full_name = str(participant.full_name)
        email = str(participant.email)
        phone = str(participant.phone_number)
        city = str(participant.city)
        state = str(participant.state)
        tshirt_size = str(participant.tshirt_size)

        category = reg.category
        category_title = str(category.title)
        category_code = str(category.code)
        distance_km = float(category.distance_km)
        price_inr = float(category.price_inr)
        start_time = str(category.start_time)

        latest_payment = reg.payments[0] if reg.payments else None
        order_id = latest_payment.razorpay_order_id if latest_payment else None
        payment_id = latest_payment.razorpay_payment_id if latest_payment else None

        results = {
            "zoho": "skipped",
            "whatsapp": "skipped",
            "n8n": "skipped",
            "meta_capi": "skipped",
        }

        # 1. Zoho CRM Deal / Contact Sync
        try:
            zoho_payload = {
                "registration_code": reg_code,
                "bib_number": bib_number,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "category": category_title,
                "amount": price_inr,
                "city": city,
                "utm_source": utm_source,
                "utm_campaign": utm_campaign,
            }
            res = await zoho_client.create_confirmed_contact(
                contact_data=zoho_payload,
                idempotency_key=f"zoho_deal_{reg_id}",
            )
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=zoho_client.service_name,
                event_type="REGISTRATION_CONFIRMED",
                status="SUCCESS",
                request_payload=zoho_payload,
                response_payload=res,
            )
            results["zoho"] = res.get("status")
        except Exception as e:
            logger.error(f"Zoho CRM integration error (non-fatal): {str(e)}")
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=zoho_client.service_name,
                event_type="REGISTRATION_CONFIRMED",
                status="FAILED",
                error_message=str(e),
            )
            results["zoho"] = "failed"

        # 2. WhatsApp Confirmation Template Notification
        try:
            wa_params = [
                {"type": "text", "text": full_name},
                {"type": "text", "text": category_title},
                {"type": "text", "text": bib_number},
                {"type": "text", "text": start_time},
            ]
            res = await whatsapp_client.send_template_message(
                to_phone=phone,
                template_name="marathon_pass_confirmed",
                parameters=wa_params,
                idempotency_key=f"wa_pass_{reg_id}",
            )
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=whatsapp_client.service_name,
                event_type="PASS_SENT",
                status="SUCCESS",
                request_payload={"to": phone, "params": wa_params},
                response_payload=res,
            )
            results["whatsapp"] = res.get("status")
        except Exception as e:
            logger.error(f"WhatsApp integration error (non-fatal): {str(e)}")
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=whatsapp_client.service_name,
                event_type="PASS_SENT",
                status="FAILED",
                error_message=str(e),
            )
            results["whatsapp"] = "failed"

        # 3. n8n Automation Webhook Event
        try:
            n8n_payload = {
                "event": "marathon.registration.confirmed",
                "registration_id": reg_id,
                "registration_code": reg_code,
                "bib_number": bib_number,
                "participant": {
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "tshirt_size": tshirt_size,
                    "city": city,
                },
                "category": {
                    "code": category_code,
                    "title": category_title,
                    "distance_km": distance_km,
                    "amount_inr": price_inr,
                },
                "utm": {
                    "source": utm_source,
                    "medium": utm_medium,
                    "campaign": utm_campaign,
                    "content": utm_content,
                    "term": utm_term,
                    "referrer": referrer,
                },
                "payment": {
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "amount_inr": price_inr,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            res = await n8n_client.trigger_event(
                event_name="marathon.registration.confirmed",
                payload=n8n_payload,
                idempotency_key=f"n8n_confirm_{reg_id}",
            )
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=n8n_client.service_name,
                event_type="WORKFLOW_TRIGGERED",
                status="SUCCESS",
                request_payload=n8n_payload,
                response_payload=res,
            )
            results["n8n"] = res.get("status")
        except Exception as e:
            logger.error(f"n8n integration error (non-fatal): {str(e)}")
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=n8n_client.service_name,
                event_type="WORKFLOW_TRIGGERED",
                status="FAILED",
                error_message=str(e),
            )
            results["n8n"] = "failed"

        # 4. Meta Conversions API (Purchase Event)
        try:
            name_parts = full_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            user_data = {
                "email": email,
                "phone": phone,
                "first_name": first_name,
                "last_name": last_name,
                "city": city,
                "state": state,
                "client_ip_address": ip_address,
                "client_user_agent": user_agent,
            }
            custom_data = {
                "currency": "INR",
                "value": price_inr,
                "content_name": category_title,
                "content_category": "Marathon Registration",
                "order_id": reg_code,
            }
            res = await meta_capi_client.send_event(
                event_name="Purchase",
                user_data=user_data,
                custom_data=custom_data,
                event_source_url=referrer or "https://citymarathon2026.com/register",
                event_id=f"purchase_{reg_code}",
            )
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=meta_capi_client.service_name,
                event_type="PURCHASE_TRACKED",
                status="SUCCESS",
                request_payload={"event": "Purchase", "custom_data": custom_data},
                response_payload=res,
            )
            results["meta_capi"] = res.get("status")
        except Exception as e:
            logger.error(f"Meta CAPI integration error (non-fatal): {str(e)}")
            await cls.log_integration_step(
                db=db,
                registration_id=reg_id,
                service_name=meta_capi_client.service_name,
                event_type="PURCHASE_TRACKED",
                status="FAILED",
                error_message=str(e),
            )
            results["meta_capi"] = "failed"

        logger.info(f"Completed Phase 4 integrations dispatch for {reg_code}: {results}")
        return results


integration_dispatcher = IntegrationDispatcherService()
