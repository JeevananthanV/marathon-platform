import hmac
import hashlib
import pytest
from httpx import AsyncClient
from app.core.config import settings

VALID_PARTICIPANT = {
    "full_name": "Deepika Padukone",
    "email": "deepika.runner@example.com",
    "phone_number": "+919988776655",
    "date_of_birth": "1992-01-05",
    "gender": "FEMALE",
    "blood_group": "A+",
    "tshirt_size": "M",
    "emergency_contact_name": "Ranveer Singh",
    "emergency_contact_phone": "+919988776654",
    "city": "Mumbai",
    "state": "Maharashtra",
}


def generate_test_signature(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_payment_verification_success_flow(async_client: AsyncClient):
    # 1. Initiate registration
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": VALID_PARTICIPANT,
        },
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    order_id = init_data["razorpay_order_id"]
    reg_code = init_data["registration_code"]

    # 2. Simulate successful Razorpay client payment return
    payment_id = "pay_test_99887766"
    valid_signature = generate_test_signature(order_id, payment_id)

    verify_payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_signature,
    }

    verify_res = await async_client.post("/api/v1/payments/verify", json=verify_payload)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["status"] == "CONFIRMED"
    assert verify_data["registration_code"] == reg_code
    assert verify_data["bib_number"].startswith("HM-")
    assert verify_data["participant_name"] == VALID_PARTICIPANT["full_name"]

    # 3. Verify Registration details via GET endpoint
    detail_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert detail_res.status_code == 200
    reg_detail = detail_res.json()
    assert reg_detail["status"] == "CONFIRMED"
    assert reg_detail["bib_number"] == verify_data["bib_number"]
    assert reg_detail["confirmed_at"] is not None


@pytest.mark.asyncio
async def test_payment_verification_invalid_signature(async_client: AsyncClient):
    # Initiate registration
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                **VALID_PARTICIPANT,
                "email": "invalid.sig@example.com",
                "phone_number": "+919988776611",
            },
        },
    )
    assert init_res.status_code == 201
    order_id = init_res.json()["razorpay_order_id"]

    # Attempt verify with forged/tampered signature
    bad_verify_payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_fake_123",
        "razorpay_signature": "invalid_forged_signature_hash_12345",
    }

    bad_res = await async_client.post("/api/v1/payments/verify", json=bad_verify_payload)
    assert bad_res.status_code == 400
    assert "Invalid payment signature" in bad_res.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_registration_prevention(async_client: AsyncClient):
    runner_email = "duplicate.test@example.com"
    runner_phone = "+919988770000"

    # 1. First registration and confirmation
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                **VALID_PARTICIPANT,
                "email": runner_email,
                "phone_number": runner_phone,
            },
        },
    )
    assert init_res.status_code == 201
    order_id = init_res.json()["razorpay_order_id"]

    # Confirm it
    payment_id = "pay_test_dup_001"
    valid_sig = generate_test_signature(order_id, payment_id)
    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": valid_sig,
        },
    )
    assert verify_res.status_code == 200

    # 2. Attempt duplicate registration for the same category
    dup_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                **VALID_PARTICIPANT,
                "email": runner_email,
                "phone_number": runner_phone,
            },
        },
    )
    assert dup_res.status_code == 409
    assert "already registered" in dup_res.json()["detail"]
