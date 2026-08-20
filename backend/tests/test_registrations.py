import pytest
from httpx import AsyncClient


VALID_PARTICIPANT = {
    "full_name": "Arjun Sharma",
    "email": "arjun.sharma@example.com",
    "phone_number": "+919876543210",
    "date_of_birth": "1995-05-15",
    "gender": "MALE",
    "blood_group": "O+",
    "tshirt_size": "L",
    "emergency_contact_name": "Pooja Sharma",
    "emergency_contact_phone": "+919876543211",
    "city": "Bengaluru",
    "state": "Karnataka",
}

VALID_UTM = {
    "utm_source": "instagram",
    "utm_medium": "story_ad",
    "utm_campaign": "monsoon_marathon_2026",
    "utm_term": "running_shoes",
    "utm_content": "video_ad_v1",
    "referrer": "https://instagram.com/ads",
}


@pytest.mark.asyncio
async def test_initiate_registration_success(async_client: AsyncClient):
    payload = {
        "category_id": "21K",
        "participant": VALID_PARTICIPANT,
        "utm": VALID_UTM,
        "terms_accepted": True,
        "communication_consent": True,
    }

    response = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert response.status_code == 201
    data = response.json()

    # 1. Verify Registration Code format (MX26-000001)
    assert "registration_code" in data
    assert data["registration_code"].startswith("MX26-")
    assert len(data["registration_code"]) == 11 # MX26-000001

    # 2. Verify Razorpay Order & Amount
    assert "razorpay_order_id" in data
    assert data["razorpay_order_id"].startswith("order_")
    assert data["amount_inr"] == 1499.0
    assert data["currency"] == "INR"
    assert "razorpay_key_id" in data


@pytest.mark.asyncio
async def test_get_registration_details_by_code(async_client: AsyncClient):
    # Initiate first
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                **VALID_PARTICIPANT,
                "email": "runner.10k@example.com",
                "phone_number": "+919876543222",
            },
            "utm": VALID_UTM,
        },
    )
    assert init_res.status_code == 201
    reg_code = init_res.json()["registration_code"]

    # Fetch details
    detail_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert detail_res.status_code == 200
    reg_data = detail_res.json()
    assert reg_data["registration_code"] == reg_code
    assert reg_data["status"] == "PENDING"
    assert reg_data["participant"]["email"] == "runner.10k@example.com"
    assert reg_data["category"]["code"] == "10K"


@pytest.mark.asyncio
async def test_registration_validation_errors(async_client: AsyncClient):
    # 1. Invalid email
    invalid_email_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {**VALID_PARTICIPANT, "email": "invalid-email"},
        },
    )
    assert invalid_email_res.status_code == 422

    # 2. Invalid phone number format
    invalid_phone_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {**VALID_PARTICIPANT, "phone_number": "123"},
        },
    )
    assert invalid_phone_res.status_code == 422

    # 3. Invalid Blood Group
    invalid_blood_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {**VALID_PARTICIPANT, "blood_group": "UNKNOWN"},
        },
    )
    assert invalid_blood_res.status_code == 422

    # 4. Invalid T-shirt size
    invalid_tshirt_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {**VALID_PARTICIPANT, "tshirt_size": "XXXXL"},
        },
    )
    assert invalid_tshirt_res.status_code == 422
