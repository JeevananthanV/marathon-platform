from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


class BaseIntegration(ABC):
    """
    Abstract base class for all third-party marketing and automation integrations.
    Guarantees clean interfaces, health checking, mock mode routing, and non-blocking failure tolerance.
    """

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the integration service (e.g. ZOHO_CRM, WHATSAPP, N8N, META_CAPI)."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Verify if required environment variables are set."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if integration is operational and ready for requests."""
        pass

    def is_mock_mode(self) -> bool:
        """
        Determine if integration should run in development mock mode.
        Enabled if INTEGRATIONS_MOCK_MODE=True or if live credentials are not configured.
        """
        return settings.INTEGRATIONS_MOCK_MODE or not self.is_configured()

    @staticmethod
    def mask_string(val: Optional[str], keep_visible: int = 4) -> str:
        """Helper to mask sensitive runner contacts or tokens in logs."""
        if not val:
            return "[EMPTY]"
        if len(val) <= keep_visible * 2:
            return "***"
        return f"{val[:keep_visible]}****{val[-keep_visible:]}"
