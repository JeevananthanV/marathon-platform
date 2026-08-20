import uuid
import httpx
from typing import Dict, Any, List, Optional, Union
from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import BaseIntegration
from app.integrations.whatsapp_templates import WhatsAppTemplateMessage


class WhatsAppIntegrationClient(BaseIntegration):
    """
    Official WhatsApp Business Cloud API Integration Adapter (Phase 4C).
    Supports Meta Graph API v20.0 message dispatch and full deterministic Mock Mode.
    """

    def __init__(self):
        # In-memory store for mock delivery tracking & status transitions
        self._mock_sent_messages: Dict[str, Dict[str, Any]] = {}
        # Testing flags for simulated API failure & retry verification
        self._simulate_failure: bool = False
        self._simulate_permanent_error: bool = False

    @property
    def service_name(self) -> str:
        return "WHATSAPP"

    def is_configured(self) -> bool:
        return settings.is_whatsapp_configured()

    def is_mock_mode(self) -> bool:
        return settings.is_whatsapp_mock_active()

    async def is_healthy(self) -> bool:
        if self.is_mock_mode():
            return True
        return self.is_configured()

    def reset_mock_state(self) -> None:
        """Reset mock message registry and test failure flags."""
        self._mock_sent_messages.clear()
        self._simulate_failure = False
        self._simulate_permanent_error = False
        try:
            from app.services.whatsapp import whatsapp_service
            whatsapp_service.mock_provider.reset_mock_state()
        except Exception:
            pass

    def set_mock_failure(self, should_fail: bool = True, permanent: bool = False) -> None:
        """Inject simulated failure for automated testing."""
        self._simulate_failure = should_fail
        self._simulate_permanent_error = permanent
        try:
            from app.services.whatsapp import whatsapp_service
            whatsapp_service.mock_provider.set_mock_failure(should_fail, permanent)
        except Exception:
            pass

    @staticmethod
    def clean_phone_number(raw_phone: str) -> str:
        """Strip non-numeric characters for WhatsApp international format."""
        clean = "".join(filter(str.isdigit, raw_phone))
        # Ensure country code (default to 91 for India if 10 digits)
        if len(clean) == 10:
            clean = f"91{clean}"
        return clean

    async def send_template_message(
        self,
        to_phone: str,
        template_message: Optional[Union[WhatsAppTemplateMessage, str]] = None,
        template: Optional[Union[WhatsAppTemplateMessage, str]] = None,
        template_name: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp Business Cloud API template message.
        Accepts template_message, template object, or template_name string.
        In Mock Mode: Generates a deterministic mock message ID and simulates delivery.
        In Real Mode: Dispatches HTTP request to Meta Graph API v20.0.
        """
        if self._simulate_failure:
            if self._simulate_permanent_error:
                raise ValueError("WhatsApp Cloud API permanent error: Recipient phone number not registered on WhatsApp (131030)")
            raise RuntimeError("WhatsApp Cloud API temporary error: Network timeout / Rate limit (429)")

        cleaned_phone = self.clean_phone_number(to_phone)
        masked_phone = self.mask_string(to_phone, 3)

        # Normalize template input across all caller formats
        target = template_message if template_message is not None else (template if template is not None else template_name)
        if target is None:
            target = "marathon_notification"

        if isinstance(target, WhatsAppTemplateMessage):
            tpl_name = target.template_name
            tpl_lang = target.language_code
            tpl_components = target.components
            tpl_text = target.rendered_text
        else:
            tpl_name = str(target)
            tpl_lang = "en"
            tpl_components = components or [
                {"type": "body", "parameters": parameters or []}
            ]
            tpl_text = f"Template: {tpl_name}"

        # MOCK MODE OPERATION
        if self.is_mock_mode():
            clean_key = (idempotency_key or uuid.uuid4().hex[:12]).replace(":", "_")
            msg_id = f"MOCK_WHATSAPP_MSG_{clean_key}"
            
            mock_entry = {
                "id": msg_id,
                "recipient": masked_phone,
                "recipient_clean": cleaned_phone,
                "template": tpl_name,
                "status": "sent",
                "rendered_text": tpl_text,
                "idempotency_key": idempotency_key,
            }
            self._mock_sent_messages[msg_id] = mock_entry

            logger.info(
                f"[WHATSAPP MOCK] Sent Template '{tpl_name}' | "
                f"To: {masked_phone} | Message ID: {msg_id}"
            )

            return {
                "status": "success",
                "service": self.service_name,
                "message_id": msg_id,
                "recipient": masked_phone,
                "template": tpl_name,
                "delivery_status": "sent",
                "mock": True,
            }

        # REAL MODE OPERATION (Meta Graph API)
        api_version = settings.WHATSAPP_API_VERSION
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": cleaned_phone,
            "type": "template",
            "template": {
                "name": tpl_name,
                "language": {"code": tpl_lang},
                "components": tpl_components,
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"WhatsApp Cloud API retryable error: HTTP {resp.status_code} - {resp.text}")

            if resp.status_code not in [200, 201]:
                raise ValueError(f"WhatsApp Cloud API permanent error: HTTP {resp.status_code} - {resp.text}")

            data = resp.json()
            messages = data.get("messages", [{}])
            live_msg_id = messages[0].get("id") if messages else f"wamid_{uuid.uuid4().hex}"

            logger.info(f"[WHATSAPP LIVE] Sent '{tpl_name}' to {masked_phone} | ID: {live_msg_id}")

            return {
                "status": "success",
                "service": self.service_name,
                "message_id": live_msg_id,
                "recipient": masked_phone,
                "template": tpl_name,
                "delivery_status": "sent",
                "mock": False,
            }

    async def send_text_message(
        self,
        to_phone: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send direct text message (service window)."""
        masked_phone = self.mask_string(to_phone, 3)
        clean_key = (idempotency_key or uuid.uuid4().hex[:12]).replace(":", "_")
        msg_id = f"MOCK_WHATSAPP_MSG_{clean_key}"

        if self.is_mock_mode():
            logger.info(f"[WHATSAPP MOCK] Send Text Message | To: {masked_phone} | ID: {msg_id}")
            return {
                "status": "success",
                "service": self.service_name,
                "message_id": msg_id,
                "mock": True,
            }

        return {"status": "pending_live_implementation", "service": self.service_name, "mock": False}

    def update_mock_delivery_status(self, message_id: str, new_status: str) -> bool:
        """Update simulated status (e.g. sent -> delivered -> read) for testing."""
        if message_id in self._mock_sent_messages:
            self._mock_sent_messages[message_id]["status"] = new_status
            return True
        return False


whatsapp_client = WhatsAppIntegrationClient()
