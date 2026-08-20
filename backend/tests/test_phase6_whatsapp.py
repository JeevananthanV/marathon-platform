import hmac
import hashlib
from typing import Dict, Any, Optional, List
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, date
from sqlalchemy import select

from app.core.config import settings
from app.services.whatsapp import (
    whatsapp_service,
    reminder_scheduler,
    WhatsAppTemplateType,
    delivery_handler,
)
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.whatsapp_message import WhatsAppMessage
from app.db.session import AsyncSessionLocal


ADMIN_HEADERS = {"X-Admin-API-Key": "marathon_admin_secret_2026"}


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_whatsapp_state():
    whatsapp_service.mock_provider.reset_mock_state()
    yield
    whatsapp_service.mock_provider.reset_mock_state()


# Helper to create a confirmed runner
async def create_confirmed_runner(
    async_client: AsyncClient,
    email: str = "runner.wa@example.com",
    phone: str = "+919876543210",
    consent: bool = True,
) -> Dict[str, Any]:
    payload = {
        "category_id": "10K",
        "participant": {
            "full_name": "WhatsApp Test Runner",
            "email": email,
            "phone_number": phone,
            "date_of_birth": "1993-04-15",
            "gender": "MALE",
            "blood_group": "B+",
            "tshirt_size": "L",
            "emergency_contact_name": "Emergency Contact",
            "emergency_contact_phone": "+919876543211",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": consent,
    }
    init_res = await async_client.post("/api/v1/registrations/initiate", json=payload)
    init_data = init_res.json()
    reg_id = init_data["registration_id"]
    order_id = init_data["razorpay_order_id"]

    # Verify payment
    pay_id = f"pay_{reg_id[:8]}"
    sig = generate_sig(order_id, pay_id)
    await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )

    # Update participant whatsapp_consent if needed
    async with AsyncSessionLocal() as session:
        p_query = select(Participant).where(Participant.email == email)
        participant = (await session.execute(p_query)).scalar_one()
        participant.whatsapp_consent = consent
        await session.commit()

    return {"registration_id": reg_id, "order_id": order_id, "email": email, "phone": phone}


# 1. WhatsApp Consent Enforcement
@pytest.mark.asyncio
async def test_whatsapp_consent_enforcement(async_client: AsyncClient):
    # Runner with consent
    runner_with_consent = await create_confirmed_runner(async_client, email="consent.yes@example.com", phone="+919876543291", consent=True)
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner_with_consent["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        assert res["status"] == "SUCCESS"
        assert res["mock"] is True

    # Runner without consent
    runner_no_consent = await create_confirmed_runner(async_client, email="consent.no@example.com", phone="+919876543292", consent=False)
    async with AsyncSessionLocal() as session:
        res_no = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner_no_consent["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        assert res_no["status"] == "FAILED"
        assert res_no.get("consent_required") is True


# 2. Registration Confirmation Workflow
@pytest.mark.asyncio
async def test_whatsapp_registration_confirmation(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="reg.conf@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_registration_confirmation(
            db=session,
            registration_id=runner["registration_id"],
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.REGISTRATION_CONFIRMATION.value


# 3. Payment Confirmation Workflow
@pytest.mark.asyncio
async def test_whatsapp_payment_confirmation(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="pay.conf@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_payment_confirmation(
            db=session,
            registration_id=runner["registration_id"],
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.PAYMENT_CONFIRMATION.value


# 4. Reminder 7 Days Before Event
@pytest.mark.asyncio
async def test_whatsapp_reminder_scheduling_7_days(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="rem7@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.REMINDER_7_DAYS.value


# 5. Reminder 3 Days Before Event
@pytest.mark.asyncio
async def test_whatsapp_reminder_scheduling_3_days(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="rem3@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_3_DAYS,
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.REMINDER_3_DAYS.value


# 6. Reminder 1 Day Before Event
@pytest.mark.asyncio
async def test_whatsapp_reminder_scheduling_1_day(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="rem1@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_1_DAY,
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.REMINDER_1_DAY.value


# 7. Race Morning Alert
@pytest.mark.asyncio
async def test_whatsapp_reminder_scheduling_race_morning(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="race.morning@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_RACE_DAY,
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.REMINDER_RACE_DAY.value


# 8. Post-Event Thank You & Timing
@pytest.mark.asyncio
async def test_whatsapp_post_event_message(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="thanks@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.POST_EVENT_THANKS,
        )
        assert res["status"] == "SUCCESS"
        assert res["template"] == WhatsAppTemplateType.POST_EVENT_THANKS.value


# 9. Idempotency & Duplicate Prevention
@pytest.mark.asyncio
async def test_whatsapp_idempotency_and_duplicate_prevention(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="idempotency@example.com")
    async with AsyncSessionLocal() as session:
        # First send
        res1 = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        assert res1["status"] == "SUCCESS"
        assert not res1.get("idempotent")

        # Second send (must be marked idempotent and not create duplicate message)
        res2 = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        assert res2["status"] == "SUCCESS"
        assert res2.get("idempotent") is True

        # Check only 1 message record in database
        idempotency_key = f"whatsapp:{WhatsAppTemplateType.REMINDER_7_DAYS.value}:{runner['registration_id']}"
        q = select(WhatsAppMessage).where(WhatsAppMessage.idempotency_key == idempotency_key)
        records = (await session.execute(q)).scalars().all()
        assert len(records) == 1


# 10. Failed Message & Error Logging
@pytest.mark.asyncio
async def test_whatsapp_failed_message_and_error_logging(async_client: AsyncClient):
    whatsapp_service.mock_provider.set_mock_failure(should_fail=True)
    runner = await create_confirmed_runner(async_client, email="fail.test@example.com")

    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_1_DAY,
        )
        assert res["status"] == "FAILED"
        assert res["retryable"] is True

        # Verify recorded as FAILED in whatsapp_messages table
        idempotency_key = f"whatsapp:{WhatsAppTemplateType.REMINDER_1_DAY.value}:{runner['registration_id']}"
        q = select(WhatsAppMessage).where(WhatsAppMessage.idempotency_key == idempotency_key)
        msg = (await session.execute(q)).scalar_one_or_none()
        assert msg is not None
        assert msg.status == "FAILED"
        assert msg.error_message is not None

    whatsapp_service.mock_provider.set_mock_failure(should_fail=False)


# 11. Retry Single Failed Message
@pytest.mark.asyncio
async def test_whatsapp_retry_single_failed_message(async_client: AsyncClient):
    whatsapp_service.mock_provider.set_mock_failure(should_fail=True)
    runner = await create_confirmed_runner(async_client, email="retry.single@example.com")

    # Generate failed message
    async with AsyncSessionLocal() as session:
        await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_3_DAYS,
        )
        idempotency_key = f"whatsapp:{WhatsAppTemplateType.REMINDER_3_DAYS.value}:{runner['registration_id']}"
        msg = (await session.execute(select(WhatsAppMessage).where(WhatsAppMessage.idempotency_key == idempotency_key))).scalar_one()
        msg_id = msg.id

    # Heal provider and trigger admin retry endpoint
    whatsapp_service.mock_provider.set_mock_failure(should_fail=False)
    retry_res = await async_client.post(f"/api/v1/admin/whatsapp/messages/{msg_id}/retry", headers=ADMIN_HEADERS)
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "SUCCESS"


# 12. Batch Retry All Failed Messages
@pytest.mark.asyncio
async def test_whatsapp_retry_all_failed_messages(async_client: AsyncClient):
    whatsapp_service.mock_provider.set_mock_failure(should_fail=True)
    runner = await create_confirmed_runner(async_client, email="retry.bulk@example.com")

    async with AsyncSessionLocal() as session:
        await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_RACE_DAY,
        )

    # Heal provider and trigger bulk retry
    whatsapp_service.mock_provider.set_mock_failure(should_fail=False)
    bulk_res = await async_client.post("/api/v1/admin/whatsapp/retry-failed?limit=50", headers=ADMIN_HEADERS)
    assert bulk_res.status_code == 200
    data = bulk_res.json()
    assert data["total_processed"] >= 1
    assert data["successful"] >= 1


# 13. Webhook Delivery Status Transitions
@pytest.mark.asyncio
async def test_whatsapp_webhook_status_transitions(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="webhook.flow@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_payment_confirmation(
            db=session,
            registration_id=runner["registration_id"],
        )
        msg_id = res["message_id"]

    # 1. Webhook for DELIVERED
    delivered_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": "delivered",
                                    "recipient_id": "919876543210",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    hook_res = await async_client.post("/api/v1/webhooks/whatsapp", json=delivered_payload)
    assert hook_res.status_code == 200

    async with AsyncSessionLocal() as session:
        msg = (await session.execute(select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == msg_id))).scalar_one()
        assert msg.status == "DELIVERED"
        assert msg.delivered_at is not None

    # 2. Webhook for READ
    read_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": "read",
                                    "recipient_id": "919876543210",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    hook_res2 = await async_client.post("/api/v1/webhooks/whatsapp", json=read_payload)
    assert hook_res2.status_code == 200

    async with AsyncSessionLocal() as session:
        msg2 = (await session.execute(select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == msg_id))).scalar_one()
        assert msg2.status == "READ"
        assert msg2.read_at is not None


# 14. Webhook Failure Status Update
@pytest.mark.asyncio
async def test_whatsapp_webhook_failure_update(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="webhook.fail@example.com")
    async with AsyncSessionLocal() as session:
        res = await whatsapp_service.send_reminder(
            db=session,
            registration_id=runner["registration_id"],
            template_type=WhatsAppTemplateType.REMINDER_7_DAYS,
        )
        msg_id = res["message_id"]

    failed_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": msg_id,
                                    "status": "failed",
                                    "recipient_id": "919876543210",
                                    "errors": [{"message": "User unreachable on WhatsApp"}],
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    hook_res = await async_client.post("/api/v1/webhooks/whatsapp", json=failed_payload)
    assert hook_res.status_code == 200

    async with AsyncSessionLocal() as session:
        msg = (await session.execute(select(WhatsAppMessage).where(WhatsAppMessage.provider_message_id == msg_id))).scalar_one()
        assert msg.status == "FAILED"
        assert msg.failed_at is not None


# 15. Webhook Challenge Verification (GET)
@pytest.mark.asyncio
async def test_whatsapp_webhook_challenge_verification(async_client: AsyncClient):
    # Valid challenge
    res = await async_client.get(
        f"/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN}&hub.challenge=test_challenge_12345"
    )
    assert res.status_code == 200
    assert res.text == "test_challenge_12345"

    # Invalid token (must return 403)
    res_bad = await async_client.get(
        "/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_123"
    )
    assert res_bad.status_code == 403


# 16. Webhook Invalid Signature Rejection
@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_signature_rejection(async_client: AsyncClient):
    res = await async_client.post(
        "/api/v1/webhooks/whatsapp",
        headers={"X-Hub-Signature-256": "sha256=invalid_signature_hash"},
        json={"entry": []},
    )
    assert res.status_code == 401


# 17. Mock Provider Deterministic IDs
@pytest.mark.asyncio
async def test_whatsapp_mock_provider_deterministic_ids():
    provider = whatsapp_service.mock_provider
    res = await provider.send_template_message(
        to_phone="+919876543210",
        template_name="marathon_reg_confirmation",
        idempotency_key="deterministic_key_001",
    )
    assert res["status"] == "success"
    assert res["message_id"] == "MOCK_WHATSAPP_MSG_deterministic_key_001"
    assert res["mock"] is True


# 18. Missing Credentials Fallback (Mock Mode)
@pytest.mark.asyncio
async def test_whatsapp_missing_credentials_fallback():
    assert settings.is_whatsapp_mock_active() is True
    provider = whatsapp_service.get_provider()
    assert provider.is_mock_mode() is True
    health = await provider.health_check()
    assert health["mode"] == "mock"
    assert health["status"] == "healthy"


# 19. Invalid Phone Number Handling
@pytest.mark.asyncio
async def test_whatsapp_invalid_phone_number_handling(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="empty.phone@example.com", phone="+919876543210")
    
    # Remove phone number in DB
    async with AsyncSessionLocal() as session:
        p_q = select(Participant).where(Participant.email == "empty.phone@example.com")
        p = (await session.execute(p_q)).scalar_one()
        p.phone_number = ""
        await session.commit()

        res = await whatsapp_service.send_payment_confirmation(db=session, registration_id=runner["registration_id"])
        assert res["status"] == "FAILED"
        assert "Missing participant phone number" in res["error"]


# 20. Admin Stats & Messages List API
@pytest.mark.asyncio
async def test_whatsapp_admin_stats_and_messages_list(async_client: AsyncClient):
    runner = await create_confirmed_runner(async_client, email="admin.wa.test@example.com")
    async with AsyncSessionLocal() as session:
        await whatsapp_service.send_payment_confirmation(db=session, registration_id=runner["registration_id"])

    # 1. Admin Stats Endpoint
    stats_res = await async_client.get("/api/v1/admin/whatsapp/stats", headers=ADMIN_HEADERS)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_messages" in stats
    assert "sent_count" in stats

    # 2. Admin Messages List Endpoint
    list_res = await async_client.get("/api/v1/admin/whatsapp/messages?page=1&page_size=10", headers=ADMIN_HEADERS)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert "total" in list_data
    assert "items" in list_data
    assert len(list_data["items"]) >= 1

    # 3. Process Due Reminders Endpoint
    rem_res = await async_client.post("/api/v1/whatsapp/reminders/process-due?limit=10", headers=ADMIN_HEADERS)
    assert rem_res.status_code == 200
    rem_data = rem_res.json()
    assert rem_data["status"] == "success"
    assert "total_evaluated" in rem_data
