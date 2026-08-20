import uuid
from typing import Dict, Any, Optional, List
from app.services.whatsapp.provider import BaseWhatsAppProvider
from app.core.logging import logger


class MockWhatsAppProvider(BaseWhatsAppProvider):
    """
    In-memory Mock WhatsApp Provider for local development, automated testing, and demos.
    Generates deterministic IDs and simulates message delivery transitions without external API calls.
    """

    def __init__(self):
        self._mock_sent_messages: Dict[str, Dict[str, Any]] = {}
        self._simulate_failure: bool = False
        self._simulate_permanent_error: bool = False

    @property
    def provider_name(self) -> str:
        return "MOCK"

    def is_configured(self) -> bool:
        return True

    def is_mock_mode(self) -> bool:
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "mode": "mock",
            "status": "healthy" if not self._simulate_failure else "simulated_outage",
            "configured": True,
        }

    def reset_mock_state(self) -> None:
        """Reset mock registry and failure simulation flags."""
        self._mock_sent_messages.clear()
        self._simulate_failure = False
        self._simulate_permanent_error = False

    def set_mock_failure(self, should_fail: bool = True, permanent: bool = False) -> None:
        """Inject simulated failure for automated testing."""
        self._simulate_failure = should_fail
        self._simulate_permanent_error = permanent

    @staticmethod
    def clean_phone_number(raw_phone: str) -> str:
        """Strip formatting and enforce international E.164 digits."""
        clean = "".join(filter(str.isdigit, raw_phone))
        if len(clean) == 10:
            clean = f"91{clean}" # Default to India (+91)
        return clean

    @staticmethod
    def mask_phone_number(phone: str, visible_digits: int = 3) -> str:
        """Mask middle digits of phone number for safe logging."""
        if not phone or len(phone) <= visible_digits * 2:
            return "***"
        prefix = phone[:visible_digits]
        suffix = phone[-visible_digits:]
        return f"{prefix}***{suffix}"

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
        language_code: str = "en",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._simulate_failure:
            if self._simulate_permanent_error:
                raise ValueError("WhatsApp Cloud API permanent error: Recipient phone number not registered on WhatsApp (131030)")
            raise RuntimeError("WhatsApp Cloud API temporary error: Network timeout / Rate limit (429)")

        cleaned_phone = self.clean_phone_number(to_phone)
        masked_phone = self.mask_phone_number(to_phone)

        clean_key = (idempotency_key or uuid.uuid4().hex[:12]).replace(":", "_").replace("-", "_")
        msg_id = f"MOCK_WHATSAPP_MSG_{clean_key}"

        mock_record = {
            "id": msg_id,
            "recipient": masked_phone,
            "recipient_clean": cleaned_phone,
            "template": template_name,
            "language": language_code,
            "parameters": parameters or [],
            "components": components or [],
            "status": "sent",
            "idempotency_key": idempotency_key,
        }
        self._mock_sent_messages[msg_id] = mock_record

        logger.info(f"[MOCK WHATSAPP] Sent Template '{template_name}' to {masked_phone} | Message ID: {msg_id}")

        return {
            "status": "success",
            "provider": self.provider_name,
            "message_id": msg_id,
            "recipient": masked_phone,
            "template": template_name,
            "delivery_status": "sent",
            "mock": True,
        }

    async def send_text_message(
        self,
        to_phone: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        masked_phone = self.mask_phone_number(to_phone)
        clean_key = (idempotency_key or uuid.uuid4().hex[:12]).replace(":", "_")
        msg_id = f"MOCK_WHATSAPP_TXT_{clean_key}"

        logger.info(f"[MOCK WHATSAPP] Sent Direct Text to {masked_phone} | Message ID: {msg_id}")
        return {
            "status": "success",
            "provider": self.provider_name,
            "message_id": msg_id,
            "recipient": masked_phone,
            "mock": True,
        }

    def update_mock_delivery_status(self, message_id: str, new_status: str) -> bool:
        """Simulate status transition (sent -> delivered -> read -> failed)."""
        if message_id in self._mock_sent_messages:
            self._mock_sent_messages[message_id]["status"] = new_status
            return True
        return False

    def validate_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> bool:
        """In mock mode, accept unless signature header explicitly indicates invalid test."""
        if signature_header and "invalid" in signature_header.lower():
            return False
        return True
