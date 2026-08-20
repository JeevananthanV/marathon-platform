import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient
from app.core.config import settings

VALID_PARTICIPANT = {
    "full_name": "Karan Johar",
    "email": "karan.webhook@example.com",
    "phone_number": "+919776655443",
    "date_of_birth": "1988-03-20",
    "gender": "MALE",
    "blood_group": "B+",
    "tshirt_size": "XL",
    "emergency_contact_name": "Rohit Shetty",
    "emergency_contact_phone": "+919776655444",
    "city": "Delhi",
    "state": "Delhi",
}


def generate_webhook_signature(body: bytes, secret: str = settings.RAZORPAY_WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_payment_captured_and_idempotency(async_client: AsyncClient):
    # 1. Initiate registration
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": VALID_PARTICIPANT,
        },
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    order_id = init_data["razorpay_order_id"]
    reg_code = init_data["registration_code"]

    # 2. Simulate Razorpay payment.captured webhook
    webhook_event = {
        "entity": "event",
        "account_id": "acc_mock_12345",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_hook_11223344",
                    "order_id": order_id,
                    "amount": 89900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
        "created_at": 1755000000,
    }
    raw_body = json.dumps(webhook_event).encode("utf-8")
    valid_signature = generate_webhook_signature(raw_body)

    # Send webhook
    headers = {"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
    hook_res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_body, headers=headers)
    assert hook_res.status_code == 200
    hook_data = hook_res.json()
    assert hook_data["status"] == "processed"
    assert hook_data["registration_code"] == reg_code
    assert hook_data["bib_number"].startswith("10K-")

    # 3. Test Webhook Idempotency (resend exact same webhook payload)
    duplicate_res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_body, headers=headers)
    assert duplicate_res.status_code == 200
    duplicate_data = duplicate_res.json()
    assert duplicate_data["status"] == "already_processed"
    assert duplicate_data["idempotency"] is True


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(async_client: AsyncClient):
    payload = {"event": "payment.captured", "payload": {}}
    raw_body = json.dumps(payload).encode("utf-8")
    fake_sig = "fake_signature_hash_abcdef"

    headers = {"X-Razorpay-Signature": fake_sig, "Content-Type": "application/json"}
    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 400
    assert "Invalid webhook signature" in res.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_payment_failed_event(async_client: AsyncClient):
    # Initiate registration
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                **VALID_PARTICIPANT,
                "email": "failed.payment@example.com",
                "phone_number": "+919776655000",
            },
        },
    )
    assert init_res.status_code == 201
    order_id = init_res.json()["razorpay_order_id"]

    # Send payment.failed event
    fail_event = {
        "entity": "event",
        "account_id": "acc_mock_12345",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed_9999",
                    "order_id": order_id,
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Card was declined by issuing bank",
                }
            }
        },
        "created_at": 1755000000,
    }
    raw_body = json.dumps(fail_event).encode("utf-8")
    sig = generate_webhook_signature(raw_body)

    headers = {"X-Razorpay-Signature": sig, "Content-Type": "application/json"}
    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_body, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "payment_failed_recorded"
