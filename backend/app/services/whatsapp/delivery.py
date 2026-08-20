from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.whatsapp_message import WhatsAppMessage
from app.models.integration_log import IntegrationLog
from app.core.logging import logger


class DeliveryStatusHandler:
    """
    Handles WhatsApp message delivery state transitions received via webhooks.
    Lifecycle: PENDING -> SENT -> DELIVERED -> READ (or FAILED).
    """

    @classmethod
    async def process_webhook_payload(
        cls,
        db: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract delivery status updates from Meta Graph API webhook format.
        """
        updated_records: List[Dict[str, Any]] = []
        entries = payload.get("entry", [])

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for status_item in value.get("statuses", []):
                    msg_id = status_item.get("id")
                    status_raw = status_item.get("status", "").upper() # SENT, DELIVERED, READ, FAILED
                    recipient_id = status_item.get("recipient_id")
                    errors = status_item.get("errors", [])
                    error_msg = errors[0].get("message") if errors else None

                    if not msg_id or not status_raw:
                        continue

                    # Standardize status
                    normalized_status = status_raw
                    if normalized_status not in ["SENT", "DELIVERED", "READ", "FAILED"]:
                        normalized_status = "SENT"

                    now = datetime.now(timezone.utc)

                    # Update WhatsAppMessage table
                    query = select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == msg_id)
                    res = await db.execute(query)
                    msg_record = res.scalar_one_or_none()

                    if msg_record:
                        msg_record.status = normalized_status
                        if normalized_status == "SENT" and not msg_record.sent_at:
                            msg_record.sent_at = now
                        elif normalized_status == "DELIVERED":
                            msg_record.delivered_at = now
                        elif normalized_status == "READ":
                            msg_record.read_at = now
                        elif normalized_status == "FAILED":
                            msg_record.failed_at = now
                            msg_record.error_message = error_msg or f"Delivery failed via webhook status update."

                        updated_records.append({
                            "message_id": msg_id,
                            "registration_id": msg_record.registration_id,
                            "status": normalized_status,
                            "phone": msg_record.phone_number,
                        })

                    # Also update IntegrationLog if referenced
                    log_query = select(IntegrationLog).where(
                        IntegrationLog.response_payload.contains(msg_id)
                    )
                    log_res = await db.execute(log_query)
                    log_entry = log_res.scalar_one_or_none()
                    if log_entry:
                        if normalized_status == "FAILED":
                            log_entry.status = "FAILED"
                            log_entry.error_message = error_msg or f"Delivery failed via webhook status."

                    await db.commit()

        logger.info(f"[WHATSAPP DELIVERY] Processed {len(updated_records)} webhook status updates.")
        return {
            "status": "processed",
            "count": len(updated_records),
            "updated_count": len(updated_records),
            "updated": updated_records,
        }


delivery_handler = DeliveryStatusHandler()
