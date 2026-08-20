import json
import hmac
import hashlib
import pytest
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.integrations import (
    zoho_client,
    whatsapp_client,
    n8n_client,
    meta_capi_client,
)
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.payment import Payment
from app.models.integration_log import IntegrationLog
from app.models.race_category import RaceCategory
from app.db.session import AsyncSessionLocal


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_all_mock_states():
    zoho_client.reset_mock_state()
    whatsapp_client.reset_mock_state()
    n8n_client.reset_mock_state()
    meta_capi_client.reset_mock_state()
    yield
    zoho_client.reset_mock_state()
    whatsapp_client.reset_mock_state()
    n8n_client.reset_mock_state()
    meta_capi_client.reset_mock_state()


# 1. Complete End-to-End Synthetic Runner Journey (Steps 1–20)
@pytest.mark.asyncio
async def test_e2e_complete_synthetic_runner_journey(async_client: AsyncClient):
    # Step 1-3: Ad Click -> Landing Page with UTMs & Meta PageView/ViewContent
    pv_res = await async_client.post(
        "/api/v1/meta/events",
        json={
            "event_name": "PageView",
            "session_id": "sess_demo_fb_01",
            "event_source_url": "https://marathon.example.com/?utm_source=facebook&utm_medium=paid_social&utm_campaign=marathon_2026&utm_content=10k_ad",
        },
    )
    assert pv_res.status_code == 200

    vc_res = await async_client.post(
        "/api/v1/meta/events",
        json={
            "event_name": "ViewContent",
            "category_code": "10K",
            "category_title": "Open 10K Run",
            "price_inr": 699.0,
            "session_id": "sess_demo_fb_01",
        },
    )
    assert vc_res.status_code == 200

    # Step 4-6: Complete Registration Form (Demo Runner)
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "Demo Runner",
                "email": "demo.runner@example.com",
                "phone_number": "+919999999999",
                "date_of_birth": "1995-05-15",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "M",
                "emergency_contact_name": "Demo Contact",
                "emergency_contact_phone": "+919999999998",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
            "utm": {
                "utm_source": "facebook",
                "utm_medium": "paid_social",
                "utm_campaign": "marathon_2026",
                "utm_content": "10k_ad",
            },
        },
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    reg_id = init_data["registration_id"]
    reg_code = init_data["registration_code"]
    order_id = init_data["razorpay_order_id"]
    assert reg_code.startswith("MX26-")

    # Step 7-10: Payment Test Mode Verification -> CONFIRMED
    pay_id = "pay_demo_e2e_99999"
    sig = generate_sig(order_id, pay_id)

    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": pay_id,
            "razorpay_signature": sig,
        },
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["status"] == "CONFIRMED"
    bib_number = verify_data["bib_number"]
    assert bib_number.startswith("10K-")

    # Step 11-12: Digital Race Pass Check
    pass_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert pass_res.status_code == 200
    pass_data = pass_res.json()
    assert pass_data["status"] == "CONFIRMED"
    assert pass_data["bib_number"] == bib_number
    assert pass_data["participant"]["full_name"] == "Demo Runner"
    assert pass_data["category"]["code"] == "10K"

    # Step 13-17: Cross-Channel Multi-Channel Integration Audit Logs
    async with AsyncSessionLocal() as session:
        query = select(IntegrationLog).where(IntegrationLog.registration_id == reg_id)
        l_res = await session.execute(query)
        logs = l_res.scalars().all()
        services = {log.service_name for log in logs}
        assert "ZOHO_CRM" in services
        assert "WHATSAPP" in services
        assert "N8N" in services
        assert "META_CAPI" in services
        assert len(logs) >= 4

    # Step 18-20: Pre-Race & Event-Day Reminder Workflow Simulations
    for r_type in ["reminder.7_days", "reminder.1_day", "reminder.event_day"]:
        sim_res = await async_client.post(
            "/api/v1/automation/simulate-event",
            json={"event": r_type, "registration_code": reg_code},
        )
        assert sim_res.status_code == 200
        assert sim_res.json()["status"] == "success"


# 2. Failure Isolation Scenario A: Meta CAPI Fails
@pytest.mark.asyncio
async def test_failure_isolation_scenario_a_meta_fails(async_client: AsyncClient):
    meta_capi_client.set_mock_failure(should_fail=True, permanent=False)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                "full_name": "Meta Fail Runner",
                "email": "meta.fail@example.com",
                "phone_number": "+919876543201",
                "date_of_birth": "1996-01-01",
                "gender": "FEMALE",
                "blood_group": "A+",
                "tshirt_size": "S",
                "emergency_contact_name": "Emergency",
                "emergency_contact_phone": "+919876543202",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    order_id = init_res.json()["razorpay_order_id"]
    reg_code = init_res.json()["registration_code"]

    pay_id = "pay_meta_iso_001"
    sig = generate_sig(order_id, pay_id)

    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    # Verify registration in DB is CONFIRMED
    check_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "CONFIRMED"


# 3. Failure Isolation Scenario B: Zoho CRM Fails
@pytest.mark.asyncio
async def test_failure_isolation_scenario_b_zoho_fails(async_client: AsyncClient):
    zoho_client.set_mock_failure(should_fail=True, permanent=False)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                "full_name": "Zoho Fail Runner",
                "email": "zoho.fail@example.com",
                "phone_number": "+919876543203",
                "date_of_birth": "1996-01-01",
                "gender": "MALE",
                "blood_group": "B+",
                "tshirt_size": "M",
                "emergency_contact_name": "Emergency",
                "emergency_contact_phone": "+919876543204",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    order_id = init_res.json()["razorpay_order_id"]
    reg_code = init_res.json()["registration_code"]

    pay_id = "pay_zoho_iso_001"
    sig = generate_sig(order_id, pay_id)

    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    check_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "CONFIRMED"


# 4. Failure Isolation Scenario C: WhatsApp Fails
@pytest.mark.asyncio
async def test_failure_isolation_scenario_c_whatsapp_fails(async_client: AsyncClient):
    whatsapp_client.set_mock_failure(should_fail=True, permanent=False)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                "full_name": "WhatsApp Fail Runner",
                "email": "wa.fail@example.com",
                "phone_number": "+919876543205",
                "date_of_birth": "1996-01-01",
                "gender": "FEMALE",
                "blood_group": "AB+",
                "tshirt_size": "L",
                "emergency_contact_name": "Emergency",
                "emergency_contact_phone": "+919876543206",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    order_id = init_res.json()["razorpay_order_id"]
    reg_code = init_res.json()["registration_code"]

    pay_id = "pay_wa_iso_001"
    sig = generate_sig(order_id, pay_id)

    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    check_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "CONFIRMED"


# 5. Failure Isolation Scenario D: n8n Fails
@pytest.mark.asyncio
async def test_failure_isolation_scenario_d_n8n_fails(async_client: AsyncClient):
    n8n_client.set_mock_failure(should_fail=True, permanent=False)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                "full_name": "n8n Fail Runner",
                "email": "n8n.fail@example.com",
                "phone_number": "+919876543207",
                "date_of_birth": "1996-01-01",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "XL",
                "emergency_contact_name": "Emergency",
                "emergency_contact_phone": "+919876543208",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    order_id = init_res.json()["razorpay_order_id"]
    reg_code = init_res.json()["registration_code"]

    pay_id = "pay_n8n_iso_001"
    sig = generate_sig(order_id, pay_id)

    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    check_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "CONFIRMED"


# 6. Idempotency Across All Channels
@pytest.mark.asyncio
async def test_idempotency_across_all_channels(async_client: AsyncClient):
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "Idempotent Runner",
                "email": "idem.runner@example.com",
                "phone_number": "+919876543209",
                "date_of_birth": "1993-07-20",
                "gender": "MALE",
                "blood_group": "A+",
                "tshirt_size": "M",
                "emergency_contact_name": "Emergency",
                "emergency_contact_phone": "+919876543210",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    reg_id = init_res.json()["registration_id"]
    order_id = init_res.json()["razorpay_order_id"]
    pay_id = "pay_idem_001"
    sig = generate_sig(order_id, pay_id)

    # First verify
    res1 = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert res1.status_code == 200

    # Repeated verify call
    res2 = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert res2.status_code == 200

    # Verify counts in DB
    async with AsyncSessionLocal() as session:
        # Check payments count
        p_res = await session.execute(select(Payment).where(Payment.registration_id == reg_id))
        payments = p_res.scalars().all()
        assert len(payments) == 1


# 7. Security Signatures & Input Hardening
@pytest.mark.asyncio
async def test_security_signature_and_input_hardening(async_client: AsyncClient):
    # Bad payment signature
    bad_verify = await async_client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "order_non_existent",
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "fake_signature",
        },
    )
    assert bad_verify.status_code == 404

    # XSS / SQL Injection in participant inputs
    xss_init = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "<script>alert('xss')</script> Robert'); DROP TABLE participants;--",
                "email": "xss.test@example.com",
                "phone_number": "+919876543211",
                "date_of_birth": "1990-01-01",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "L",
                "emergency_contact_name": "Contact",
                "emergency_contact_phone": "+919876543212",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert xss_init.status_code == 201
    reg_code = xss_init.json()["registration_code"]

    # Ensure tables still exist and query safely
    get_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert get_res.status_code == 200
    assert "Robert" in get_res.json()["participant"]["full_name"]


# 8. Operations Dashboard Overview & Demo Reset
@pytest.mark.asyncio
async def test_admin_operations_overview_and_demo_reset(async_client: AsyncClient):
    admin_headers = {"X-Admin-API-Key": settings.ADMIN_API_KEY}

    # Overview metrics
    overview_res = await async_client.get("/api/v1/admin/overview", headers=admin_headers)
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert "registrations" in data
    assert "payments" in data
    assert "categories" in data
    assert "integrations" in data

    # Detailed registration list
    list_res = await async_client.get("/api/v1/admin/registrations", headers=admin_headers)
    assert list_res.status_code == 200
    res_data = list_res.json()
    items = res_data.get("items", res_data) if isinstance(res_data, dict) else res_data
    assert isinstance(items, list)

    # Safe demo reset
    reset_res = await async_client.post("/api/v1/admin/demo-reset", headers=admin_headers)
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "success"

    # Verify counts reset to 0
    after_overview = await async_client.get("/api/v1/admin/overview", headers=admin_headers)
    assert after_overview.json()["registrations"]["total"] == 0
    assert after_overview.json()["payments"]["total_transactions"] == 0
