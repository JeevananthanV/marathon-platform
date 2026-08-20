import uuid
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import BaseIntegration


class N8NIntegrationClient(BaseIntegration):
    """
    n8n Workflow Automation Engine Integration Client (Phase 4D).
    Dispatches business automation events to n8n webhook triggers with HMAC/shared-secret security,
    deterministic Mock Mode, and failure simulation.
    """

    def __init__(self):
        # In-memory store for tracking mock dispatched events
        self._mock_triggered_events: Dict[str, Dict[str, Any]] = {}
        # Testing flags for failure simulation
        self._simulate_failure: bool = False
        self._simulate_permanent_error: bool = False

    @property
    def service_name(self) -> str:
        return "N8N"

    def is_configured(self) -> bool:
        return settings.is_n8n_configured()

    def is_mock_mode(self) -> bool:
        return settings.is_n8n_mock_active()

    async def is_healthy(self) -> bool:
        if self.is_mock_mode():
            return True
        return self.is_configured()

    def reset_mock_state(self) -> None:
        """Reset mock dispatched events registry and test failure flags."""
        self._mock_triggered_events.clear()
        self._simulate_failure = False
        self._simulate_permanent_error = False

    def set_mock_failure(self, should_fail: bool = True, permanent: bool = False) -> None:
        """Inject simulated failure for automated testing."""
        self._simulate_failure = should_fail
        self._simulate_permanent_error = permanent

    def verify_webhook_secret(self, provided_secret: Optional[str]) -> bool:
        """Verify inbound webhook shared secret against configured N8N_WEBHOOK_SECRET."""
        if not provided_secret or not settings.N8N_WEBHOOK_SECRET:
            return False
        return provided_secret.strip() == settings.N8N_WEBHOOK_SECRET.strip()

    async def trigger_event(
        self,
        event_name: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an n8n webhook workflow event.
        In Mock Mode: Generates a deterministic mock execution ID and records event locally.
        In Real Mode: Dispatches HTTP POST to n8n webhook listener with secret auth.
        """
        if self._simulate_failure:
            if self._simulate_permanent_error:
                raise ValueError("n8n workflow rejected event: Malformed event schema (400)")
            raise RuntimeError("n8n server unavailable: Connection refused / Timeout (503)")

        clean_key = (idempotency_key or uuid.uuid4().hex[:12]).replace(":", "_")
        event_id = f"MOCK_N8N_EVENT_{clean_key}"
        exec_id = f"n8n_exec_mock_{clean_key}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Construct standardized Event envelope
        event_envelope = {
            "event": event_name,
            "event_id": event_id,
            "timestamp": now_iso,
            "idempotency_key": idempotency_key,
            "data": payload,
        }

        # MOCK MODE OPERATION
        if self.is_mock_mode():
            self._mock_triggered_events[event_id] = {
                "event": event_name,
                "event_id": event_id,
                "execution_id": exec_id,
                "payload": payload,
                "timestamp": now_iso,
                "idempotency_key": idempotency_key,
            }

            logger.info(f"[N8N MOCK] Triggered Event '{event_name}' | ID: {event_id} | Exec: {exec_id}")

            return {
                "status": "success",
                "service": self.service_name,
                "event": event_name,
                "event_id": event_id,
                "execution_id": exec_id,
                "idempotency_key": idempotency_key,
                "mock": True,
            }

        # REAL MODE OPERATION (HTTP POST to n8n Webhook)
        webhook_slug = event_name.replace(".", "-")
        url = f"{settings.N8N_BASE_URL.rstrip('/')}/webhook/{webhook_slug}"

        headers = {
            "Content-Type": "application/json",
            "X-N8N-Webhook-Secret": settings.N8N_WEBHOOK_SECRET,
            "X-Event-Id": event_id,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=event_envelope)
            
            if resp.status_code >= 500 or resp.status_code == 429:
                raise RuntimeError(f"n8n server retryable error: HTTP {resp.status_code} - {resp.text}")

            if resp.status_code not in [200, 201, 202]:
                raise ValueError(f"n8n workflow rejected event: HTTP {resp.status_code} - {resp.text}")

            res_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            live_exec_id = res_data.get("executionId", f"n8n_exec_{uuid.uuid4().hex[:8]}")

            logger.info(f"[N8N LIVE] Event '{event_name}' accepted | Exec ID: {live_exec_id}")

            return {
                "status": "success",
                "service": self.service_name,
                "event": event_name,
                "event_id": event_id,
                "execution_id": live_exec_id,
                "idempotency_key": idempotency_key,
                "mock": False,
            }


n8n_client = N8NIntegrationClient()
