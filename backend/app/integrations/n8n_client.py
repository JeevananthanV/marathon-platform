import uuid
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import BaseIntegration


class N8nIntegrationClient(BaseIntegration):
    """
    n8n Workflow Automation Integration Adapter (Phase 4A Architecture & Mock Adapter).
    Dispatches asynchronous automation triggers for multi-channel workflows and scheduled reminders.
    """

    @property
    def service_name(self) -> str:
        return "N8N"

    def is_configured(self) -> bool:
        return settings.is_n8n_configured()

    async def is_healthy(self) -> bool:
        if self.is_mock_mode():
            return True
        return self.is_configured()

    async def trigger_event(
        self,
        event_name: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an n8n webhook workflow event (e.g. registration.confirmed, payment.reminder).
        In mock mode: Simulates workflow dispatch without making external HTTP requests.
        """
        if self.is_mock_mode():
            simulated_exec_id = f"n8n_exec_mock_{uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key or event_name).hex[:12]}"
            logger.info(
                f"[N8N AUTOMATION MOCK] Trigger Event: '{event_name}' | "
                f"Payload Keys: {list(payload.keys())} | Mock Exec ID: {simulated_exec_id}"
            )
            return {
                "status": "success",
                "service": self.service_name,
                "event": event_name,
                "execution_id": simulated_exec_id,
                "mock": True,
            }

        # Phase 4D Live Implementation placeholder
        logger.info(f"Preparing n8n live webhook trigger for event '{event_name}' (Phase 4D)")
        return {
            "status": "pending_live_implementation",
            "service": self.service_name,
            "mock": False,
        }


n8n_client = N8nIntegrationClient()
