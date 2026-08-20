import hmac
import hashlib
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.integrations.zoho_crm import zoho_client


ADMIN_HEADERS = {"X-Admin-API-Key": "marathon_admin_secret_2026"}


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_zoho_lead_creation_on_registration(async_client: AsyncClient):
    """
    Test that initiating a registration creates/synchronizes a Zoho CRM lead in mock mode.
    """
    zoho_client.reset_mock_state()

    payload = {
        "category_id": "5K",
        "participant": {
            "full_name": "Zoho Lead Runner",
            "email": "zoho.lead.runner@example.com",
            "phone_number": "+919876543210",
            "date_of_birth": "1994-05-12",
            "gender": "FEMALE",
            "blood_group": "B+",
            "tshirt_size": "M",
            "emergency_contact_name": "Contact Person",
            "emergency_contact_phone": "+919876543211",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "utm": {
            "utm_source": "instagram",
            "utm_medium": "story",
            "utm_campaign": "zoho_test_campaign",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }

    resp = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert resp.status_code in [200, 201]
    data = resp.json()
    reg_code = data["registration_code"]

    # Verify Zoho client recorded lead
    lead = await zoho_client.search_lead(email="zoho.lead.runner@example.com")
    assert lead is not None
    assert lead["First_Name"] == "Zoho"
    assert lead["Last_Name"] == "Lead Runner"
    assert lead["UTM_Source"] == "instagram"
    assert lead["UTM_Campaign"] == "zoho_test_campaign"
    assert lead["Registration_Code"] == reg_code


@pytest.mark.asyncio
async def test_zoho_payment_update_synchronization(async_client: AsyncClient):
    """
    Test that verifying payment updates the existing Zoho CRM lead with payment & BIB details.
    """
    zoho_client.reset_mock_state()

    payload = {
        "category_id": "10K",
        "participant": {
            "full_name": "Payment Sync Runner",
            "email": "payment.sync.runner@example.com",
            "phone_number": "+919876543212",
            "date_of_birth": "1990-08-20",
            "gender": "MALE",
            "blood_group": "O+",
            "tshirt_size": "L",
            "emergency_contact_name": "Emergency Person",
            "emergency_contact_phone": "+919876543213",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }

    # 1. Initiate
    reg_resp = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert reg_resp.status_code in [200, 201]
    reg_data = reg_resp.json()
    order_id = reg_data["razorpay_order_id"]
    reg_code = reg_data["registration_code"]

    # 2. Verify Payment
    pay_id = "pay_zoho_test_123456"
    sig = generate_sig(order_id, pay_id)
    verify_resp = await async_client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": pay_id,
            "razorpay_signature": sig,
        },
    )
    assert verify_resp.status_code == 200

    # 3. Verify Zoho CRM lead was updated with confirmed payment and bib number
    lead = await zoho_client.search_lead(email="payment.sync.runner@example.com")
    assert lead is not None
    assert lead["Payment_Status"] == "SUCCESS"
    assert lead["Registration_Code"] == reg_code
    assert lead.get("Bib_Number") is not None


@pytest.mark.asyncio
async def test_zoho_duplicate_prevention_on_multiple_registrations(async_client: AsyncClient):
    """
    Test that multiple registrations from the same participant email update the existing Zoho lead.
    """
    zoho_client.reset_mock_state()

    payload1 = {
        "category_id": "5K",
        "participant": {
            "full_name": "Same Email Runner",
            "email": "duplicate.test.runner@example.com",
            "phone_number": "+919876543214",
            "date_of_birth": "1992-03-15",
            "gender": "MALE",
            "blood_group": "A+",
            "tshirt_size": "M",
            "emergency_contact_name": "Contact 1",
            "emergency_contact_phone": "+919876543215",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }

    resp1 = await async_client.post("/api/v1/registrations/initiate", json=payload1)
    assert resp1.status_code in [200, 201]

    # Second registration attempt by same email
    payload2 = {**payload1, "category_id": "21K"}
    resp2 = await async_client.post("/api/v1/registrations/initiate", json=payload2)
    assert resp2.status_code in [200, 201]

    # Count records in mock DB
    records_with_email = [
        r for r in zoho_client._mock_crm_db.values()
        if (r.get("Email") or "").lower() == "duplicate.test.runner@example.com"
    ]
    assert len(records_with_email) == 1, "Duplicate lead was created in Zoho CRM!"


@pytest.mark.asyncio
async def test_zoho_failure_isolation_and_error_logging(async_client: AsyncClient):
    """
    Test that when Zoho CRM fails, registration STILL SUCCEEDS and failure is tracked in DB.
    """
    zoho_client.reset_mock_state()
    zoho_client.set_mock_failure(should_fail=True)

    payload = {
        "category_id": "5K",
        "participant": {
            "full_name": "Zoho Fail Runner",
            "email": "zoho.fail.runner@example.com",
            "phone_number": "+919876543216",
            "date_of_birth": "1995-10-10",
            "gender": "FEMALE",
            "blood_group": "B-",
            "tshirt_size": "S",
            "emergency_contact_name": "Emergency Contact",
            "emergency_contact_phone": "+919876543217",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }

    # Registration must succeed despite Zoho downtime
    resp = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert resp.status_code in [200, 201]
    data = resp.json()
    reg_id = data["registration_id"]

    # Check Admin registrations endpoint shows FAILED zoho_sync_status
    admin_reg_resp = await async_client.get("/api/v1/admin/registrations", headers=ADMIN_HEADERS)
    assert admin_reg_resp.status_code == 200
    registrations = admin_reg_resp.json()["items"]
    target = next((r for r in registrations if r["registration_id"] == reg_id), None)
    assert target is not None
    assert target["zoho_sync_status"] == "FAILED"

    # Reset failure flag
    zoho_client.set_mock_failure(should_fail=False)


@pytest.mark.asyncio
async def test_zoho_admin_endpoints_and_manual_retry(async_client: AsyncClient):
    """
    Test Zoho status endpoint, manual registration sync, and bulk retry endpoint.
    """
    zoho_client.reset_mock_state()
    zoho_client.set_mock_failure(should_fail=True)

    # 1. Create registration while Zoho is down
    payload = {
        "category_id": "10K",
        "participant": {
            "full_name": "Retry Sync Runner",
            "email": "retry.sync.runner@example.com",
            "phone_number": "+919876543218",
            "date_of_birth": "1988-12-05",
            "gender": "MALE",
            "blood_group": "AB+",
            "tshirt_size": "XL",
            "emergency_contact_name": "Contact Person",
            "emergency_contact_phone": "+919876543219",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }
    reg_resp = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert reg_resp.status_code in [200, 201]
    reg_id = reg_resp.json()["registration_id"]

    # 2. Check Zoho status endpoint
    status_resp = await async_client.get("/api/v1/admin/zoho/status", headers=ADMIN_HEADERS)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["mode"] == "mock"
    assert status_data["failed_count"] >= 1

    # 3. Test Admin Auth Protection (401 without key)
    unauth_resp = await async_client.get("/api/v1/admin/zoho/status")
    assert unauth_resp.status_code == 401

    # 4. Fix Zoho and trigger manual single sync
    zoho_client.set_mock_failure(should_fail=False)
    sync_resp = await async_client.post(f"/api/v1/admin/zoho/sync/{reg_id}", headers=ADMIN_HEADERS)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["status"] == "SUCCESS"
    assert sync_data["zoho_record_id"] is not None

    # 5. Test bulk retry endpoint
    retry_resp = await async_client.post("/api/v1/admin/zoho/retry-failed?limit=50", headers=ADMIN_HEADERS)
    assert retry_resp.status_code == 200
    retry_data = retry_resp.json()
    assert "total_processed" in retry_data
    assert "successful" in retry_data
