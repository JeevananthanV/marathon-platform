import hmac
import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.integrations.whatsapp_cloud import whatsapp_client
from app.integrations.whatsapp_templates import (
    WhatsAppTemplateType,
    whatsapp_template_service,
)
from app.services.whatsapp_service import whatsapp_service
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.db.session import AsyncSessionLocal


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_wa_state():
    whatsapp_client.reset_mock_state()
    yield
    whatsapp_client.reset_mock_state()


# Helper to create a confirmed test registration
async def create_test_registration(async_client: AsyncClient, email: str, phone: str = "+919876500001") -> Dict:
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Dev Sharma",
                "email": email,
                "phone_number": phone,
                "date_of_birth": "1992-05-15",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "L",
                "emergency_contact_name": "Rita Sharma",
                "emergency_contact_phone": "+919876500002",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert init_res.status_code == 201
    return init_res.json()


# 1. Mock Registration Confirmation
@pytest.mark.asyncio
async def test_mock_registration_confirmation(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.reg@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_registration_confirmation(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["mock"] is True
        assert res["message_id"].startswith("MOCK_WHATSAPP_MSG_")
        assert "marathon_registration_confirmed" in res["template"]


# 2. Mock Payment Confirmation
@pytest.mark.asyncio
async def test_mock_payment_confirmation(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.pay@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_payment_confirmation(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["message_id"].startswith("MOCK_WHATSAPP_MSG_")
        assert "marathon_payment_confirmed" in res["template"]


# 3. Mock BIB Notification
@pytest.mark.asyncio
async def test_mock_bib_notification(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.bib@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_digital_pass(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert res["message_id"].startswith("MOCK_WHATSAPP_MSG_")
        assert "marathon_digital_pass_bib" in res["template"]


# 4. Mock 7-Day Reminder
@pytest.mark.asyncio
async def test_mock_7_day_reminder(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.rem7@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder_7_days(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert "marathon_reminder_7_days" in res["template"]


# 5. Mock 1-Day Reminder
@pytest.mark.asyncio
async def test_mock_1_day_reminder(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.rem1@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder_1_day(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert "marathon_reminder_1_day" in res["template"]


# 6. Mock Event-Day Reminder
@pytest.mark.asyncio
async def test_mock_event_day_reminder(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.rem0@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder_event_day(db=session, registration_id=reg_id)
        assert res["status"] == "SUCCESS"
        assert "marathon_reminder_event_day" in res["template"]


# 7. Template Variable Validation
def test_template_variable_validation():
    # Missing required field participant_name
    with pytest.raises(ValueError) as exc:
        whatsapp_template_service.render_template(
            template_type=WhatsAppTemplateType.REGISTRATION_CONFIRMATION,
            recipient_phone="+919876543210",
            data={"registration_code": "MX26-0001", "category_title": "10K"},
        )
    assert "Missing required fields" in str(exc.value)
    assert "participant_name" in str(exc.value)


# 8. Missing Participant Phone Number
@pytest.mark.asyncio
async def test_missing_participant_phone_number(async_client: AsyncClient):
    with pytest.raises(ValueError) as exc:
        whatsapp_template_service.render_template(
            template_type=WhatsAppTemplateType.PAYMENT_CONFIRMATION,
            recipient_phone="",
            data={"participant_name": "A", "registration_code": "B", "amount_inr": 100},
        )
    assert "Recipient phone number is required" in str(exc.value)


# 9. Duplicate Message Prevention
@pytest.mark.asyncio
async def test_duplicate_message_prevention(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.dup@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        # First send
        res1 = await whatsapp_service.send_registration_confirmation(db=session, registration_id=reg_id)
        assert res1["status"] == "SUCCESS"
        first_msg_id = res1["message_id"]

        # Duplicate send attempt
        res2 = await whatsapp_service.send_registration_confirmation(db=session, registration_id=reg_id)
        assert res2["status"] == "SUCCESS"
        assert res2.get("idempotent") is True
        assert res2["message_id"] == first_msg_id


# 10. Idempotency Audit Records in Integration Logs
@pytest.mark.asyncio
async def test_idempotency_audit_records(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.audit@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        await whatsapp_service.send_digital_pass(db=session, registration_id=reg_id)
        await whatsapp_service.send_digital_pass(db=session, registration_id=reg_id)

        # Check database: Exactly 1 SUCCESS integration log for DIGITAL_PASS
        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "WHATSAPP",
            IntegrationLog.event_type == "WHATSAPP_DIGITAL_PASS_BIB",
        )
        l_res = await session.execute(query)
        logs = l_res.scalars().all()
        assert len(logs) == 1
        assert logs[0].status == "SUCCESS"


# 11. Retryable WhatsApp Failure
@pytest.mark.asyncio
async def test_retryable_whatsapp_failure(async_client: AsyncClient):
    # Inject temporary network / 429 rate limit failure
    whatsapp_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "dev.retry@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder_7_days(db=session, registration_id=reg_id)
        assert res["status"] == "FAILED"
        assert res["retryable"] is True

        # Check logged failure
        query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "WHATSAPP",
        )
        l_res = await session.execute(query)
        log = l_res.scalar_one()
        assert log.status == "FAILED"


# 12. Permanent WhatsApp Failure
@pytest.mark.asyncio
async def test_permanent_whatsapp_failure(async_client: AsyncClient):
    # Inject permanent unregistered phone failure
    whatsapp_client.set_mock_failure(should_fail=True, permanent=True)

    reg_data = await create_test_registration(async_client, "dev.perm@example.com")
    reg_id = reg_data["registration_id"]

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder_1_day(db=session, registration_id=reg_id)
        assert res["status"] == "FAILED"
        assert res["retryable"] is False


# 13. Webhook Delivery Status Update
@pytest.mark.asyncio
async def test_webhook_delivery_status_update(async_client: AsyncClient):
    reg_data = await create_test_registration(async_client, "dev.webhook@example.com")
    reg_id = reg_data["registration_id"]

    # 1. Send confirmation message
    async with AsyncSessionLocal() as session:
        send_res = await whatsapp_service.send_registration_confirmation(db=session, registration_id=reg_id)
        msg_id = send_res["message_id"]

    # 2. Simulate Meta Webhook payload (delivered status)
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": "delivered",
                                    "timestamp": "1723960000",
                                    "recipient_id": "919876500001",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    wh_res = await async_client.post("/api/v1/webhooks/whatsapp", json=webhook_payload)
    assert wh_res.status_code == 200
    assert wh_res.json()["data"]["updated_count"] == 1


# 14. Invalid Webhook Request
@pytest.mark.asyncio
async def test_invalid_webhook_requests(async_client: AsyncClient):
    # GET Challenge verification with wrong verify token
    get_res = await async_client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_secret_token",
            "hub.challenge": "12345678",
        },
    )
    assert get_res.status_code == 403

    # Valid GET Challenge verification
    get_valid = await async_client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            "hub.challenge": "987654321",
        },
    )
    assert get_valid.status_code == 200
    assert get_valid.text == "987654321"


# 15. Successful Payment Remains CONFIRMED When WhatsApp Fails
@pytest.mark.asyncio
async def test_payment_remains_confirmed_when_whatsapp_fails(async_client: AsyncClient):
    # Inject WhatsApp failure
    whatsapp_client.set_mock_failure(should_fail=True, permanent=False)

    reg_data = await create_test_registration(async_client, "dev.payson@example.com")
    order_id = reg_data["razorpay_order_id"]
    reg_code = reg_data["registration_code"]

    pay_id = "pay_wa_fail_test_001"
    sig = generate_sig(order_id, pay_id)

    # Payment verification MUST succeed with HTTP 200 and CONFIRMED status
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
