from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseWhatsAppProvider(ABC):
    """
    Abstract Interface for WhatsApp Messaging Providers.
    Allows swappable providers (Mock, Meta Graph API, Twilio, Gupshup, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the WhatsApp provider."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider credentials are fully configured."""
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Return True if operating in simulation/mock mode."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify provider availability and connection status."""
        pass

    @abstractmethod
    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
        language_code: str = "en",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a template-based message to the specified recipient phone number.
        Returns dictionary containing message_id, status, and metadata.
        """
        pass

    @abstractmethod
    async def send_text_message(
        self,
        to_phone: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a standard text message (if supported in customer service window)."""
        pass

    @abstractmethod
    def validate_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> bool:
        """Validate HMAC signature of incoming provider webhook payload."""
        pass
