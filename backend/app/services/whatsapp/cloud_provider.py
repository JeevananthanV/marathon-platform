import hmac
import hashlib
import httpx
from typing import Dict, Any, Optional, List
from app.services.whatsapp.provider import BaseWhatsAppProvider
from app.core.config import settings
from app.core.logging import logger


class WhatsAppCloudAPIProvider(BaseWhatsAppProvider):
    """
    Official Meta WhatsApp Business Cloud API (Graph API v20.0) Provider.
    Dispatches outbound template messages and validates inbound webhook signatures.
    """

    @property
    def provider_name(self) -> str:
        return "WHATSAPP_CLOUD_API"

    def is_configured(self) -> bool:
        return bool(
            settings.WHATSAPP_ACCESS_TOKEN
            and settings.WHATSAPP_PHONE_NUMBER_ID
        )

    def is_mock_mode(self) -> bool:
        return settings.is_whatsapp_mock_active()

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "mode": "live" if not self.is_mock_mode() else "mock",
            "configured": self.is_configured(),
            "phone_number_id": settings.WHATSAPP_PHONE_NUMBER_ID[:4] + "***" if settings.WHATSAPP_PHONE_NUMBER_ID else None,
            "api_version": settings.WHATSAPP_API_VERSION,
        }

    @staticmethod
    def clean_phone_number(raw_phone: str) -> str:
        clean = "".join(filter(str.isdigit, raw_phone))
        if len(clean) == 10:
            clean = f"91{clean}"
        return clean

    @staticmethod
    def mask_phone_number(phone: str, visible_digits: int = 3) -> str:
        if not phone or len(phone) <= visible_digits * 2:
            return "***"
        return f"{phone[:visible_digits]}***{phone[-visible_digits:]}"

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
        language_code: str = "en",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("WhatsApp Cloud API credentials not configured (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID).")

        cleaned_phone = self.clean_phone_number(to_phone)
        masked_phone = self.mask_phone_number(to_phone)

        api_version = settings.WHATSAPP_API_VERSION
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        # Build payload components
        tpl_components = components or [
            {"type": "body", "parameters": parameters or []}
        ]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": cleaned_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
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
            live_msg_id = messages[0].get("id") if messages else "wamid_unknown"

            logger.info(f"[WHATSAPP LIVE] Sent '{template_name}' to {masked_phone} | ID: {live_msg_id}")

            return {
                "status": "success",
                "provider": self.provider_name,
                "message_id": live_msg_id,
                "recipient": masked_phone,
                "template": template_name,
                "delivery_status": "sent",
                "mock": False,
            }

    async def send_text_message(
        self,
        to_phone: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_phone = self.clean_phone_number(to_phone)
        masked_phone = self.mask_phone_number(to_phone)

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
            "type": "text",
            "text": {"body": message},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in [200, 201]:
                raise ValueError(f"WhatsApp Cloud API text error: HTTP {resp.status_code} - {resp.text}")
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "wamid_unknown")

            return {
                "status": "success",
                "provider": self.provider_name,
                "message_id": msg_id,
                "recipient": masked_phone,
                "mock": False,
            }

    def validate_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> bool:
        """
        Validate Meta X-Hub-Signature-256 header using WHATSAPP_APP_SECRET.
        """
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret:
            # If no secret configured, accept in mock mode or warning
            return True

        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header[7:]
        computed_sig = hmac.new(
            app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, computed_sig)
