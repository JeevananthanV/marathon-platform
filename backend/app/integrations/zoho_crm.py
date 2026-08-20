import time
import uuid
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import BaseIntegration


class ZohoCRMIntegrationClient(BaseIntegration):
    """
    Zoho CRM Integration Client (Phase 5).
    Handles OAuth2 token refresh, search-before-create duplicate prevention,
    lead creation, lead updates, contact/registration tracking, and payment synchronization.
    """

    def __init__(self):
        self._cached_access_token: Optional[str] = None
        self._token_expiry_timestamp: float = 0.0
        # In-memory registry for mock mode testing (stores simulated Zoho leads)
        self._mock_crm_db: Dict[str, Dict[str, Any]] = {}
        # Simulated failure hooks for testing error handling & retry
        self._simulate_failure: bool = False
        self._simulate_permanent_error: bool = False

    @property
    def service_name(self) -> str:
        return "ZOHO_CRM"

    def is_configured(self) -> bool:
        return settings.is_zoho_configured()

    def is_mock_mode(self) -> bool:
        return settings.is_zoho_mock_active()

    async def is_healthy(self) -> bool:
        if self.is_mock_mode():
            return True
        return self.is_configured()

    async def health_check(self) -> Dict[str, Any]:
        """Check Zoho CRM integration health and connectivity status."""
        mode = "mock" if self.is_mock_mode() else "live"
        configured = self.is_configured()
        healthy = await self.is_healthy()
        return {
            "service": self.service_name,
            "status": "HEALTHY" if healthy else "UNCONFIGURED",
            "mode": mode,
            "configured": configured,
            "api_domain": settings.ZOHO_API_DOMAIN,
            "mock_records_count": len(self._mock_crm_db) if mode == "mock" else None,
        }

    def reset_mock_state(self) -> None:
        """Reset mock in-memory CRM database and failure injection flags."""
        self._mock_crm_db.clear()
        self._simulate_failure = False
        self._simulate_permanent_error = False

    def set_mock_failure(self, should_fail: bool = True, permanent: bool = False) -> None:
        """Enable or disable simulated API failure injection for testing."""
        self._simulate_failure = should_fail
        self._simulate_permanent_error = permanent

    async def get_access_token(self) -> str:
        """
        Obtain a valid Zoho CRM OAuth 2.0 access token.
        Uses cached token if still valid; otherwise exchanges refresh token for a new access token.
        """
        if self.is_mock_mode():
            return "mock_zoho_access_token_12345"

        now = time.time()
        if self._cached_access_token and now < (self._token_expiry_timestamp - 60):
            return self._cached_access_token

        token_url = f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/token"
        params = {
            "refresh_token": settings.ZOHO_REFRESH_TOKEN,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(token_url, params=params)
                if response.status_code != 200:
                    logger.error(
                        f"Failed to refresh Zoho CRM access token: HTTP {response.status_code} - {response.text}"
                    )
                    raise ValueError(f"Zoho token refresh failed: {response.text}")

                data = response.json()
                if "error" in data:
                    logger.error(f"Zoho token response contained error: {data['error']}")
                    raise ValueError(f"Zoho auth error: {data.get('error')}")

                self._cached_access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expiry_timestamp = now + expires_in

                logger.info("Successfully refreshed and cached Zoho CRM OAuth 2.0 access token.")
                return self._cached_access_token

            except Exception as e:
                logger.error(f"Exception during Zoho token refresh: {str(e)}")
                raise

    async def search_lead(self, email: str, phone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Search for an existing Lead in Zoho CRM by participant email (or phone).
        Enforces search-before-create to guarantee zero duplicate CRM leads.
        """
        if not email or not email.strip():
            return None

        clean_email = email.strip().lower()

        # MOCK MODE SEARCH
        if self.is_mock_mode():
            if self._simulate_failure:
                if self._simulate_permanent_error:
                    raise RuntimeError("Permanent Zoho CRM Error: Invalid credentials or deleted module")
                raise RuntimeError("Simulated Zoho CRM search API connection timeout / 500 error")

            for rec_id, record in self._mock_crm_db.items():
                rec_email = (record.get("Email") or record.get("email") or "").lower()
                if rec_email == clean_email:
                    logger.info(f"[ZOHO MOCK] Found existing lead for {clean_email}: {rec_id}")
                    return {"id": rec_id, **record}
            return None

        # REAL API SEARCH
        token = await self.get_access_token()
        search_url = f"{settings.ZOHO_API_DOMAIN}/crm/v2/Leads/search"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        params = {"email": clean_email}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(search_url, headers=headers, params=params)
                if response.status_code == 204:
                    return None
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("data", [])
                    return records[0] if records else None

                logger.warning(
                    f"Zoho search returned unexpected status HTTP {response.status_code}: {response.text}"
                )
                return None
            except Exception as e:
                logger.error(f"Zoho search API exception: {str(e)}")
                raise

    def _build_lead_payload(
        self,
        participant_data: Dict[str, Any],
        registration_data: Dict[str, Any],
        utm_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct standard Zoho CRM Leads module payload."""
        full_name = participant_data.get("full_name") or "Marathon Runner"
        name_parts = full_name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Runner"
        last_name = name_parts[1] if len(name_parts) > 1 else "(Participant)"

        utm = utm_data or {}
        return {
            "First_Name": first_name,
            "Last_Name": last_name,
            "Email": participant_data.get("email"),
            "Phone": participant_data.get("phone_number"),
            "Lead_Source": "Marathon Website Registration",
            "Race_Category": registration_data.get("category_title") or registration_data.get("category"),
            "Registration_Code": registration_data.get("registration_code"),
            "Bib_Number": registration_data.get("bib_number"),
            "Payment_Status": registration_data.get("payment_status", "SUCCESS"),
            "Registration_Status": registration_data.get("status", "CONFIRMED"),
            "Amount_Paid": registration_data.get("amount_inr") or registration_data.get("amount"),
            "City": participant_data.get("city"),
            "State": participant_data.get("state"),
            "Gender": participant_data.get("gender"),
            "Blood_Group": participant_data.get("blood_group"),
            "TShirt_Size": participant_data.get("tshirt_size"),
            "Emergency_Contact": participant_data.get("emergency_contact_name"),
            "Emergency_Phone": participant_data.get("emergency_contact_phone"),
            "UTM_Source": utm.get("utm_source"),
            "UTM_Medium": utm.get("utm_medium"),
            "UTM_Campaign": utm.get("utm_campaign"),
            "UTM_Content": utm.get("utm_content"),
            "UTM_Term": utm.get("utm_term"),
            "Referrer": utm.get("referrer"),
        }

    async def create_lead(
        self,
        participant_data: Dict[str, Any],
        registration_data: Dict[str, Any],
        utm_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new Lead in Zoho CRM."""
        crm_payload = self._build_lead_payload(participant_data, registration_data, utm_data)

        if self.is_mock_mode():
            if self._simulate_failure:
                if self._simulate_permanent_error:
                    raise RuntimeError("Permanent Zoho CRM Error: Invalid field or rejected schema")
                raise RuntimeError("Simulated Zoho CRM create API connection timeout / 500 error")

            zoho_id = f"mock_zoho_rec_{uuid.uuid4().hex[:10]}"
            self._mock_crm_db[zoho_id] = {
                "id": zoho_id,
                "_created_at": time.time(),
                **crm_payload,
            }
            logger.info(f"[ZOHO MOCK] Created new Lead {zoho_id} for {crm_payload.get('Email')}")
            return {
                "status": "success",
                "action": "created",
                "zoho_record_id": zoho_id,
                "service": self.service_name,
                "mock": True,
                "data": crm_payload,
            }

        token = await self.get_access_token()
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        create_url = f"{settings.ZOHO_API_DOMAIN}/crm/v2/Leads"
        body = {"data": [crm_payload]}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(create_url, headers=headers, json=body)
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"Zoho Lead creation failed: HTTP {resp.status_code} - {resp.text}")

            res_data = resp.json()
            record_info = res_data.get("data", [{}])[0].get("details", {})
            zoho_id = record_info.get("id") or "unknown"
            return {
                "status": "success",
                "action": "created",
                "zoho_record_id": zoho_id,
                "service": self.service_name,
                "mock": False,
                "data": crm_payload,
            }

    async def update_lead(
        self,
        lead_id: str,
        participant_data: Dict[str, Any],
        registration_data: Dict[str, Any],
        utm_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an existing Lead in Zoho CRM."""
        crm_payload = self._build_lead_payload(participant_data, registration_data, utm_data)

        if self.is_mock_mode():
            if self._simulate_failure:
                if self._simulate_permanent_error:
                    raise RuntimeError("Permanent Zoho CRM Error: Cannot update locked record")
                raise RuntimeError("Simulated Zoho CRM update API connection timeout / 500 error")

            if lead_id in self._mock_crm_db:
                self._mock_crm_db[lead_id].update({**crm_payload, "_updated_at": time.time()})
            else:
                self._mock_crm_db[lead_id] = {"id": lead_id, "_created_at": time.time(), **crm_payload}

            logger.info(f"[ZOHO MOCK] Updated Lead {lead_id} for {crm_payload.get('Email')}")
            return {
                "status": "success",
                "action": "updated",
                "zoho_record_id": lead_id,
                "service": self.service_name,
                "mock": True,
                "data": crm_payload,
            }

        token = await self.get_access_token()
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        update_url = f"{settings.ZOHO_API_DOMAIN}/crm/v2/Leads/{lead_id}"
        body = {"data": [crm_payload]}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(update_url, headers=headers, json=body)
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"Zoho Lead update failed: HTTP {resp.status_code} - {resp.text}")

            return {
                "status": "success",
                "action": "updated",
                "zoho_record_id": lead_id,
                "service": self.service_name,
                "mock": False,
                "data": crm_payload,
            }

    async def create_registration_contact(
        self,
        participant_data: Dict[str, Any],
        registration_data: Dict[str, Any],
        utm_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create or synchronize a participant contact for a confirmed registration."""
        return await self.sync_participant_lead(
            participant_data=participant_data,
            registration_data=registration_data,
            utm_data=utm_data,
        )

    async def update_registration(
        self,
        lead_id: str,
        registration_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update registration details (BIB, status, category) on existing Zoho record."""
        if self.is_mock_mode():
            if lead_id in self._mock_crm_db:
                self._mock_crm_db[lead_id].update({
                    "Registration_Code": registration_data.get("registration_code"),
                    "Bib_Number": registration_data.get("bib_number"),
                    "Registration_Status": registration_data.get("status"),
                    "Race_Category": registration_data.get("category_title"),
                    "_updated_at": time.time(),
                })
            return {"status": "success", "action": "registration_updated", "zoho_record_id": lead_id, "mock": True}

        token = await self.get_access_token()
        headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
        update_url = f"{settings.ZOHO_API_DOMAIN}/crm/v2/Leads/{lead_id}"
        body = {
            "data": [{
                "Registration_Code": registration_data.get("registration_code"),
                "Bib_Number": registration_data.get("bib_number"),
                "Registration_Status": registration_data.get("status"),
                "Race_Category": registration_data.get("category_title"),
            }]
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(update_url, headers=headers, json=body)
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"Zoho registration update failed: HTTP {resp.status_code} - {resp.text}")
            return {"status": "success", "action": "registration_updated", "zoho_record_id": lead_id, "mock": False}

    async def add_payment_information(
        self,
        lead_id: str,
        payment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synchronize payment confirmation details to existing Zoho record."""
        if self.is_mock_mode():
            if lead_id in self._mock_crm_db:
                self._mock_crm_db[lead_id].update({
                    "Payment_Status": payment_data.get("status", "SUCCESS"),
                    "Razorpay_Payment_ID": payment_data.get("payment_id"),
                    "Amount_Paid": payment_data.get("amount_inr"),
                    "Payment_Timestamp": payment_data.get("timestamp"),
                    "_updated_at": time.time(),
                })
            return {"status": "success", "action": "payment_updated", "zoho_record_id": lead_id, "mock": True}

        token = await self.get_access_token()
        headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
        update_url = f"{settings.ZOHO_API_DOMAIN}/crm/v2/Leads/{lead_id}"
        body = {
            "data": [{
                "Payment_Status": payment_data.get("status", "SUCCESS"),
                "Razorpay_Payment_ID": payment_data.get("payment_id"),
                "Amount_Paid": payment_data.get("amount_inr"),
                "Payment_Timestamp": payment_data.get("timestamp"),
            }]
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(update_url, headers=headers, json=body)
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"Zoho payment sync failed: HTTP {resp.status_code} - {resp.text}")
            return {"status": "success", "action": "payment_updated", "zoho_record_id": lead_id, "mock": False}

    async def sync_participant_lead(
        self,
        participant_data: Dict[str, Any],
        registration_data: Dict[str, Any],
        utm_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified method: Searches for existing lead by email before creating or updating.
        Guarantees that a runner is never duplicated in Zoho CRM.
        """
        email = participant_data.get("email")
        existing = await self.search_lead(email=email)

        if existing:
            lead_id = existing["id"]
            return await self.update_lead(
                lead_id=lead_id,
                participant_data=participant_data,
                registration_data=registration_data,
                utm_data=utm_data,
            )
        else:
            return await self.create_lead(
                participant_data=participant_data,
                registration_data=registration_data,
                utm_data=utm_data,
            )

    async def upsert_lead(
        self,
        lead_data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Alias for sync_participant_lead."""
        return await self.sync_participant_lead(
            participant_data=lead_data,
            registration_data=lead_data,
            utm_data=lead_data,
            idempotency_key=idempotency_key,
        )

    async def create_confirmed_contact(
        self,
        participant_data: Optional[Dict[str, Any]] = None,
        registration_data: Optional[Dict[str, Any]] = None,
        contact_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record confirmed contact/deal."""
        data = contact_data or participant_data or {}
        reg = registration_data or data
        return await self.sync_participant_lead(
            participant_data=data,
            registration_data=reg,
            idempotency_key=idempotency_key,
        )


zoho_client = ZohoCRMIntegrationClient()
