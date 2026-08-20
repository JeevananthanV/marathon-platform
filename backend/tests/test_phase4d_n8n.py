import hmac
import hashlib
import pytest
from typing import Dict
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.integrations.n8n import n8n_client
from app.services.n8n_service import n8n_service
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.db.session import AsyncSessionLocal


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_n8n_state():
    n8n_client.reset_mock_state()
    yield
    n8n_client.reset_mock_state()


# Helper to create a test registration
async def create_test_registration(async_client: AsyncClient, email: str, phone: str = "+919876500001") -> Dict:
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Arjun Mehta",
                "email": email,
                "phone_number": phone,
                "date_of_birth": "1994-06-20",
                "gender": "MALE",
                "blood_group": "B+",
                "tshirt_size": "M",
                "emergency_contact_name": "Kavita Mehta",
                "emergency_contact_phone": "+919876500002",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert init_res.status_code == 201
    return init_res.json()


# 1. n8n Mock Event Delivery
@pytest.mark.asyncio
async def test_n8n_mock_event_delivery(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.mock@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_registration_confirmed(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["mock"] is True
        assert res["event_id"].startswith("MOCK_N8N_EVENT_")
        assert res["execution_id"].startswith("n8n_exec_mock_")


# 2. Valid Webhook Authentication
@pytest.mark.asyncio
async def test_valid_webhook_authentication(async_client: AsyncClient):
    res = await async_client.get(
        "/api/v1/automation/eligible-participants",
        headers={"X-N8N-Webhook-Secret": settings.N8N_WEBHOOK_SECRET},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


# 3. Invalid Webhook Authentication
@pytest.mark.asyncio
async def test_invalid_webhook_authentication(async_client: AsyncClient):
    res = await async_client.get(
        "/api/v1/automation/eligible-participants",
        headers={"X-N8N-Webhook-Secret": "invalid_wrong_secret"},
    )
    assert res.status_code == 403


# 4. Missing Authentication Header
@pytest.mark.asyncio
async def test_missing_authentication(async_client: AsyncClient):
    res = await async_client.get("/api/v1/automation/eligible-participants")
    assert res.status_code == 401


# 5. Duplicate Event Prevention
@pytest.mark.asyncio
async def test_duplicate_event_prevention(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.dup@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res1 = await n8n_service.dispatch_payment_captured(db=session, registration_id=reg_id)
        res2 = await n8n_service.dispatch_payment_captured(db=session, registration_id=reg_id)
        assert res2["status"] == "SUCCESS"
        assert res2.get("idempotent") is True
        assert res2["event_id"] == res1["event_id"]


# 6. Idempotent Event Processing (Audit Record Verification)
@pytest.mark.asyncio
async def test_idempotent_event_processing(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.audit@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await n8n_service.dispatch_bib_assigned(db=session, registration_id=reg_id)
        await n8n_service.dispatch_bib_assigned(db=session, registration_id=reg_id)

        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "N8N",
            IntegrationLog.event_type == "N8N_BIB_ASSIGNED",
        )
        l_res = await session.execute(query)
        logs = l_res.scalars().all()
        assert len(logs) == 1
        assert logs[0].status == "SUCCESS"


# 7. registration.confirmed Event
@pytest.mark.asyncio
async def test_registration_confirmed_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.reg@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_registration_confirmed(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event"] == "registration.confirmed"


# 8. payment.captured Event
@pytest.mark.asyncio
async def test_payment_captured_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.pay@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_payment_captured(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event"] == "payment.captured"


# 9. bib.assigned Event
@pytest.mark.asyncio
async def test_bib_assigned_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.bib@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_bib_assigned(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["event"] == "bib.assigned"


# 10. 7-Day Reminder
@pytest.mark.asyncio
async def test_7_day_reminder_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.rem7@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_id = reg_data["registration_id"]

    # Confirm registration first via payment verify
    pay_id = "pay_n8n_rem7_001"
    sig = generate_sig(order_id, pay_id)
    await async_client.post("/api/v1/payments/verify", json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig})

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_reminder(db=session, registration_id=reg_id, reminder_type="7_days")
        assert res["status"] == "SUCCESS"
        assert res["event"] == "reminder.7_days"


# 11. 1-Day Reminder
@pytest.mark.asyncio
async def test_1_day_reminder_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.rem1@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_id = reg_data["registration_id"]

    pay_id = "pay_n8n_rem1_001"
    sig = generate_sig(order_id, pay_id)
    await async_client.post("/api/v1/payments/verify", json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig})

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_reminder(db=session, registration_id=reg_id, reminder_type="1_day")
        assert res["status"] == "SUCCESS"
        assert res["event"] == "reminder.1_day"


# 12. Event-Day Reminder
@pytest.mark.asyncio
async def test_event_day_reminder_event(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.rem0@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_id = reg_data["registration_id"]

    pay_id = "pay_n8n_rem0_001"
    sig = generate_sig(order_id, pay_id)
    await async_client.post("/api/v1/payments/verify", json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig})

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_reminder(db=session, registration_id=reg_id, reminder_type="event_day")
        assert res["status"] == "SUCCESS"
        assert res["event"] == "reminder.event_day"


# 13. Unconfirmed Participant Excluded from Reminders
@pytest.mark.asyncio
async def test_unconfirmed_participant_excluded_from_reminders(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "n8n.unconf@example.com")
    reg_id = reg_data["registration_id"]
    # Registration is in PENDING_PAYMENT status

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_reminder(db=session, registration_id=reg_id, reminder_type="7_days")
        assert res["status"] == "SKIPPED"
        assert res["eligible"] is False
        assert "not CONFIRMED" in res["reason"]


# 14. Failed n8n Delivery Logging
@pytest.mark.asyncio
async def test_failed_n8n_delivery_logging(async_client: AsyncClient):
    n8n_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "n8n.fail@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await n8n_service.dispatch_registration_confirmed(db=session, registration_id=reg_id)
        assert res["status"] == "FAILED"
        assert res["retryable"] is True

        # Check logged FAILED entry
        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "N8N",
        )
        l_res = await session.execute(query)
        log = l_res.scalar_one()
        assert log.status == "FAILED"


# 15. Retryable n8n Failure & Recovery
@pytest.mark.asyncio
async def test_retryable_n8n_failure_and_recovery(async_client: AsyncClient):
    # Fail first
    n8n_client.set_mock_failure(should_fail=True, permanent=False)
    reg_data = await create_test_registration(async_client, "n8n.recov@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await n8n_service.dispatch_registration_confirmed(db=session, registration_id=reg_id)

    # Recover service and retry
    n8n_client.set_mock_failure(should_fail=False)

    async with AsyncSessionLocal() as session:
        retries = await n8n_service.retry_failed_n8n_events(db=session)
        assert len(retries) >= 1
        assert any(r["result"]["status"] == "SUCCESS" for r in retries)


# 16. Payment Remains Successful When n8n Is Unavailable
@pytest.mark.asyncio
async def test_payment_remains_confirmed_when_n8n_is_unavailable(async_client: AsyncClient):
    n8n_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "n8n.safepay@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_code = reg_data["registration_code"]

    pay_id = "pay_n8n_safepay_001"
    sig = generate_sig(order_id, pay_id)

    # Verify payment MUST succeed with HTTP 200 and CONFIRMED status
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
