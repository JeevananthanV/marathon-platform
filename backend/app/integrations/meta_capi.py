import hashlib
import uuid
import time
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import BaseIntegration


def hash_data(value: Optional[str]) -> Optional[str]:
    """Normalize and SHA-256 hash sensitive identifiers according to Meta CAPI specification."""
    if not value or not str(value).strip():
        return None
    normalized = str(value).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_phone_number(raw_phone: Optional[str]) -> Optional[str]:
    """Strip all non-numeric characters and prepend default country code (91) for India if needed."""
    if not raw_phone or not str(raw_phone).strip():
        return None
    clean = "".join(filter(str.isdigit, str(raw_phone)))
    if len(clean) == 10:
        clean = f"91{clean}"
    return clean


def normalize_and_hash_phone(raw_phone: Optional[str]) -> Optional[str]:
    clean = normalize_phone_number(raw_phone)
    if not clean:
        return None
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


class MetaCAPIIntegrationClient(BaseIntegration):
    """
    Official Meta Conversions API (CAPI) Integration Adapter (Phase 4E).
    Supports Graph API v20.0 server-side funnel tracking (PageView, ViewContent, Lead,
    InitiateCheckout, Purchase, CompleteRegistration) with customer matching hashing and deterministic Mock Mode.
    """

    def __init__(self):
        # In-memory store for tracking mock dispatched CAPI events
        self._mock_sent_events: Dict[str, Dict[str, Any]] = {}
        # Testing failure flags
        self._simulate_failure: bool = False
        self._simulate_permanent_error: bool = False

    @property
    def service_name(self) -> str:
        return "META_CAPI"

    def is_configured(self) -> bool:
        return settings.is_meta_capi_configured()

    def is_mock_mode(self) -> bool:
        return settings.is_meta_capi_mock_active()

    async def is_healthy(self) -> bool:
        if self.is_mock_mode():
            return True
        return self.is_configured()

    def reset_mock_state(self) -> None:
        """Reset mock event registry and test failure flags."""
        self._mock_sent_events.clear()
        self._simulate_failure = False
        self._simulate_permanent_error = False

    def set_mock_failure(self, should_fail: bool = True, permanent: bool = False) -> None:
        """Inject simulated failure for automated testing."""
        self._simulate_failure = should_fail
        self._simulate_permanent_error = permanent

    @staticmethod
    def hash_sha256(value: Optional[str]) -> Optional[str]:
        """Normalize and hash SHA-256 utility method."""
        return hash_data(value)

    @staticmethod
    def build_user_data(
        email: Optional[str] = None,
        phone: Optional[str] = None,
        full_name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Construct Meta customer matching object.
        Applies SHA-256 normalization and hashing to PII fields.
        Leaves technical client IP & User Agent unhashed per Meta specs.
        """
        user_data: Dict[str, Any] = {}

        if email:
            h_em = hash_data(email)
            if h_em:
                user_data["em"] = [h_em]

        if phone:
            h_ph = normalize_and_hash_phone(phone)
            if h_ph:
                user_data["ph"] = [h_ph]

        if full_name:
            parts = full_name.strip().split(maxsplit=1)
            fn = parts[0] if parts else full_name
            ln = parts[1] if len(parts) > 1 else ""
            h_fn = hash_data(fn)
            if h_fn:
                user_data["fn"] = [h_fn]
            if ln:
                h_ln = hash_data(ln)
                if h_ln:
                    user_data["ln"] = [h_ln]

        if city:
            h_ct = hash_data(city)
            if h_ct:
                user_data["ct"] = [h_ct]

        if state:
            h_st = hash_data(state)
            if h_st:
                user_data["st"] = [h_st]

        user_data["country"] = [hash_data("in")]

        # Technical client attribution parameters (unhashed per Meta Graph API specs)
        if client_ip:
            user_data["client_ip_address"] = client_ip
        if user_agent:
            user_data["client_user_agent"] = user_agent
        if fbc:
            user_data["fbc"] = fbc
        if fbp:
            user_data["fbp"] = fbp

        return user_data

    async def send_event(
        self,
        event_name: str,
        user_data: Dict[str, Any],
        custom_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
        action_source: str = "website",
    ) -> Dict[str, Any]:
        """
        Send server-side event to Meta Conversions API.
        In Mock Mode: Records event locally with deterministic ID.
        In Real Mode: Dispatches HTTP request to Meta Graph API v20.0.
        """
        if self._simulate_failure:
            if self._simulate_permanent_error:
                raise ValueError("Meta CAPI rejected event: Invalid access token or Pixel ID (400)")
            raise RuntimeError("Meta CAPI server timeout / rate limit (500)")

        clean_event_id = event_id or f"ev_{uuid.uuid4().hex[:12]}"

        event_payload = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "event_id": clean_event_id,
            "action_source": action_source,
            "event_source_url": event_source_url or "https://marathon.example.com",
            "user_data": user_data,
            "custom_data": custom_data or {},
        }

        # MOCK MODE OPERATION
        if self.is_mock_mode():
            mock_id = f"MOCK_META_EVENT_{event_name}_{clean_event_id}"
            self._mock_sent_events[mock_id] = {
                "event_name": event_name,
                "event_id": clean_event_id,
                "payload": event_payload,
                "timestamp": int(time.time()),
            }

            logger.info(f"[META CAPI MOCK] Tracked '{event_name}' | Event ID: {clean_event_id}")

            return {
                "status": "success",
                "service": self.service_name,
                "event_name": event_name,
                "event_id": clean_event_id,
                "events_received": 1,
                "fbtrace_id": f"fb_mock_trace_{uuid.uuid4().hex[:12]}",
                "mock": True,
            }

        # REAL MODE OPERATION (Meta Graph API v20.0)
        pixel_id = settings.META_PIXEL_ID
        api_version = settings.META_API_VERSION
        url = f"https://graph.facebook.com/{api_version}/{pixel_id}/events"

        params = {"access_token": settings.META_ACCESS_TOKEN}
        body: Dict[str, Any] = {"data": [event_payload]}
        if settings.META_TEST_EVENT_CODE:
            body["test_event_code"] = settings.META_TEST_EVENT_CODE

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, params=params, json=body)
            
            if resp.status_code >= 500 or resp.status_code == 429:
                raise RuntimeError(f"Meta CAPI retryable error: HTTP {resp.status_code} - {resp.text}")

            if resp.status_code not in [200, 201]:
                raise ValueError(f"Meta CAPI permanent error: HTTP {resp.status_code} - {resp.text}")

            res_data = resp.json()
            logger.info(f"[META CAPI LIVE] Tracked '{event_name}' | Event ID: {clean_event_id} | Trace: {res_data.get('fbtrace_id')}")

            return {
                "status": "success",
                "service": self.service_name,
                "event_name": event_name,
                "event_id": clean_event_id,
                "events_received": res_data.get("events_received", 1),
                "fbtrace_id": res_data.get("fbtrace_id"),
                "mock": False,
            }


meta_capi_client = MetaCAPIIntegrationClient()
