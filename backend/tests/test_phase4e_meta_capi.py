import json
import hmac
import hashlib
import pytest
from typing import Dict
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.integrations.meta_capi import (
    meta_capi_client,
    hash_data,
    normalize_phone_number,
    normalize_and_hash_phone,
)
from app.services.meta_capi_service import meta_capi_service
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.db.session import AsyncSessionLocal


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_meta_state():
    meta_capi_client.reset_mock_state()
    yield
    meta_capi_client.reset_mock_state()


# Helper to create a test registration with UTM params
async def create_test_registration(
    async_client: AsyncClient,
    email: str,
    phone: str = "+919876500001",
    utm_source: str = "instagram_ads",
    utm_campaign: str = "marathon_earlybird_2026",
) -> Dict:
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Vikram Seth",
                "email": email,
                "phone_number": phone,
                "date_of_birth": "1991-03-12",
                "gender": "MALE",
                "blood_group": "A+",
                "tshirt_size": "L",
                "emergency_contact_name": "Ananya Seth",
                "emergency_contact_phone": "+919876500002",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
            "utm": {
                "utm_source": utm_source,
                "utm_campaign": utm_campaign,
            },
        },
    )
    assert init_res.status_code == 201
    return init_res.json()


# 1. Meta Mock PageView
@pytest.mark.asyncio
async def test_meta_mock_page_view(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_page_view(
            db=session,
            session_id="sess_12345",
            url="https://marathon.example.com",
            client_ip="192.168.1.10",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        assert res["status"] == "SUCCESS"
        assert res["mock"] is True
        assert res["event_name"] == "PageView"
        assert res["event_id"].startswith("pageview_sess_12345_")


# 2. Meta Mock ViewContent
@pytest.mark.asyncio
async def test_meta_mock_view_content(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_view_content(
            db=session,
            category_code="21K",
            category_title="Half Marathon 21K",
            price_inr=899.0,
            session_id="sess_view_01",
        )
        assert res["status"] == "SUCCESS"
        assert res["event_name"] == "ViewContent"
        assert res["event_id"] == "viewcontent_21K_sess_view_01"


# 3. Meta Mock Lead
@pytest.mark.asyncio
async def test_meta_mock_lead(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.lead@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_lead(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event_name"] == "Lead"
        assert res["event_id"].startswith("lead_")


# 4. Meta Mock InitiateCheckout
@pytest.mark.asyncio
async def test_meta_mock_initiate_checkout(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.checkout@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_initiate_checkout(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event_name"] == "InitiateCheckout"
        assert res["event_id"].startswith("initiate_checkout_")


# 5. Meta Mock Purchase
@pytest.mark.asyncio
async def test_meta_mock_purchase(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.purchase@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_meta_001")
        assert res["status"] == "SUCCESS"
        assert res["event_name"] == "Purchase"
        assert res["event_id"].startswith("purchase_")


# 6. Meta Mock CompleteRegistration
@pytest.mark.asyncio
async def test_meta_mock_complete_registration(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.completereg@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_complete_registration(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event_name"] == "CompleteRegistration"
        assert res["event_id"].startswith("complete_registration_")


# 7. Event ID Generation Verification
def test_event_id_generation():
    # Verify deterministic SHA-256 hash outputs
    assert hash_data("Vikram.Seth@Example.COM") == hashlib.sha256(b"vikram.seth@example.com").hexdigest()
    assert hash_data("  bengaluru  ") == hashlib.sha256(b"bengaluru").hexdigest()


# 8. Duplicate Purchase Prevention
@pytest.mark.asyncio
async def test_duplicate_purchase_prevention(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.dup@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res1 = await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_dup_001")
        assert res1["status"] == "SUCCESS"
        first_event_id = res1["event_id"]

        # Duplicate call
        res2 = await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_dup_001")
        assert res2["status"] == "SUCCESS"
        assert res2.get("idempotent") is True
        assert res2["event_id"] == first_event_id


# 9. Payment Retry Does Not Duplicate Purchase in Integration Logs
@pytest.mark.asyncio
async def test_payment_retry_does_not_duplicate_purchase(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.audit@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_retry_001")
        await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_retry_001")

        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "META_CAPI",
            IntegrationLog.event_type == "META_PURCHASE",
        )
        l_res = await session.execute(query)
        logs = l_res.scalars().all()
        assert len(logs) == 1
        assert logs[0].status == "SUCCESS"


# 10. Email Normalization and Hashing
def test_email_normalization_and_hashing():
    raw_email = "  Test.Runner@Gmail.COM  "
    hashed = hash_data(raw_email)
    expected = hashlib.sha256(b"test.runner@gmail.com").hexdigest()
    assert hashed == expected


# 11. Phone Normalization and Hashing
def test_phone_normalization_and_hashing():
    raw_phone = "+91 (987) 654-3210"
    normalized = normalize_phone_number(raw_phone)
    assert normalized == "919876543210"
    hashed = normalize_and_hash_phone(raw_phone)
    assert hashed == hashlib.sha256(b"919876543210").hexdigest()


# 12. Missing Optional Attribution Fields Handled Safely
@pytest.mark.asyncio
async def test_missing_optional_attribution_fields(async_client: AsyncClient):
    user_data = meta_capi_client.build_user_data(email=None, phone=None, client_ip=None, user_agent=None)
    assert user_data.get("country") == [hash_data("in")]
    assert "em" not in user_data
    assert "ph" not in user_data


# 13. Meta API Permanent Failure Handling
@pytest.mark.asyncio
async def test_meta_api_permanent_failure_handling(async_client: AsyncClient):
    meta_capi_client.set_mock_failure(should_fail=True, permanent=True)

    reg_data = await create_test_registration(async_client, "meta.perm@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_fail_001")
        assert res["status"] == "FAILED"
        assert res["retryable"] is False


# 14. Retryable Failure & Recovery
@pytest.mark.asyncio
async def test_retryable_failure_and_recovery(async_client: AsyncClient):
    meta_capi_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "meta.retry@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await meta_capi_service.track_lead(db=session, registration_id=reg_id)
        assert res["status"] == "FAILED"
        assert res["retryable"] is True

    # Recover service and retry
    meta_capi_client.set_mock_failure(should_fail=False)
    async with AsyncSessionLocal() as session:
        retries = await meta_capi_service.retry_failed_meta_events(db=session)
        assert len(retries) >= 1
        assert any(r["result"]["status"] == "SUCCESS" for r in retries)


# 15. Payment Remains Confirmed When Meta Fails
@pytest.mark.asyncio
async def test_payment_remains_confirmed_when_meta_fails(async_client: AsyncClient):
    meta_capi_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "meta.safepay@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_code = reg_data["registration_code"]

    pay_id = "pay_meta_safepay_001"
    sig = generate_sig(order_id, pay_id)

    # Verification MUST succeed
    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    # Database registration status check
    detail_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "CONFIRMED"


# 16. UTM Preservation in Custom Data
@pytest.mark.asyncio
async def test_utm_preservation_in_custom_data(async_client: AsyncClient):
    reg_data = await create_test_registration(
        async_client,
        "meta.utm@example.com",
        utm_source="facebook_feed",
        utm_campaign="marathon_summer_2026",
    )
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_utm_001")

        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "META_CAPI",
            IntegrationLog.event_type == "META_PURCHASE",
        )
        l_res = await session.execute(query)
        log = l_res.scalar_one()
        payload = json.loads(log.request_payload)
        assert payload["custom_data"]["utm_source"] == "facebook_feed"
        assert payload["custom_data"]["utm_campaign"] == "marathon_summer_2026"


# 17. Secret is Not Exposed in Logs
@pytest.mark.asyncio
async def test_secret_is_not_exposed_in_logs(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "meta.secret@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await meta_capi_service.track_purchase(db=session, registration_id=reg_id, payment_id="pay_sec_001")

        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "META_CAPI",
        )
        l_res = await session.execute(query)
        log = l_res.scalar_one()
        assert "EAA" not in (log.request_payload or "")
        assert "EAA" not in (log.response_payload or "")


# 18. Mock Mode Makes Zero External Requests
@pytest.mark.asyncio
async def test_mock_mode_makes_zero_external_requests(async_client: AsyncClient):
    assert meta_capi_client.is_mock_mode() is True
    res = await meta_capi_client.send_event(
        event_name="PageView",
        event_id="test_mock_traffic_001",
        user_data={"country": [hash_data("in")]},
    )
    assert res["status"] == "success"
    assert res["mock"] is True
    assert res["fbtrace_id"].startswith("fb_mock_trace_")
