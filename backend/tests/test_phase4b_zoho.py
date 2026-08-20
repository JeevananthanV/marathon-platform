import hmac
import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.integrations.zoho_crm import zoho_client
from app.services.zoho_service import zoho_service
from app.models.registration import Registration
from app.models.participant import Participant
from app.models.integration_log import IntegrationLog
from app.db.session import AsyncSessionLocal


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def reset_zoho_state():
    zoho_client.reset_mock_state()
    yield
    zoho_client.reset_mock_state()


# 1. Mock Zoho Create
@pytest.mark.asyncio
async def test_mock_zoho_create_new_record():
    participant_data = {
        "full_name": "Rohan Mehra",
        "email": "rohan.mehra@example.com",
        "phone_number": "+919811223344",
        "city": "Bengaluru",
        "state": "Karnataka",
        "gender": "MALE",
        "blood_group": "O+",
        "tshirt_size": "L",
    }
    registration_data = {
        "registration_code": "MX26-000101",
        "bib_number": "HM-1101",
        "category_title": "21K Half Marathon",
        "amount_inr": 1499.0,
        "status": "CONFIRMED",
    }
    
    result = await zoho_client.sync_participant_lead(participant_data, registration_data)
    assert result["status"] == "success"
    assert result["action"] == "created"
    assert result["zoho_record_id"].startswith("mock_zoho_rec_")
    assert result["mock"] is True


# 2. Mock Zoho Update
@pytest.mark.asyncio
async def test_mock_zoho_update_existing_record():
    participant_data = {
        "full_name": "Rohan Mehra",
        "email": "rohan.mehra@example.com",
        "phone_number": "+919811223344",
        "city": "Bengaluru",
    }
    registration_data = {
        "registration_code": "MX26-000101",
        "bib_number": "HM-1101",
        "category_title": "21K Half Marathon",
    }
    
    # First sync -> Create
    res1 = await zoho_client.sync_participant_lead(participant_data, registration_data)
    first_id = res1["zoho_record_id"]
    assert res1["action"] == "created"

    # Second sync (same email) -> Update
    updated_participant = {**participant_data, "city": "Mysuru"}
    res2 = await zoho_client.sync_participant_lead(updated_participant, registration_data)
    assert res2["action"] == "updated"
    assert res2["zoho_record_id"] == first_id


# 3. Existing CRM Record Search
@pytest.mark.asyncio
async def test_existing_crm_record_matching():
    # Insert record into mock CRM
    zoho_client._mock_crm_db["rec_existing_01"] = {
        "id": "rec_existing_01",
        "Email": "existing.runner@example.com",
        "Phone": "+919876543000",
        "First_Name": "Anita",
    }

    found = await zoho_client.search_lead(email="existing.runner@example.com")
    assert found is not None
    assert found["id"] == "rec_existing_01"


# 4. New CRM Record Search returns None
@pytest.mark.asyncio
async def test_new_crm_record_search_returns_none():
    found = await zoho_client.search_lead(email="unknown.runner@example.com")
    assert found is None


# 5. Duplicate Prevention
@pytest.mark.asyncio
async def test_duplicate_prevention_on_multiple_syncs():
    part = {
        "full_name": "Sneha Reddy",
        "email": "sneha.reddy@example.com",
        "phone_number": "+919777888999",
    }
    reg = {"registration_code": "MX26-000202", "bib_number": "10K-1202", "category_title": "10K Timed Run"}

    # Sync 3 times
    res1 = await zoho_client.sync_participant_lead(part, reg)
    res2 = await zoho_client.sync_participant_lead(part, reg)
    res3 = await zoho_client.sync_participant_lead(part, reg)

    assert res1["zoho_record_id"] == res2["zoho_record_id"] == res3["zoho_record_id"]
    assert len(zoho_client._mock_crm_db) == 1


# 6. Successful Synchronization on Payment Verification Flow
@pytest.mark.asyncio
async def test_successful_synchronization_on_payment_confirmation(async_client: AsyncClient):
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Kavita Das",
                "email": "kavita.das@example.com",
                "phone_number": "+919888777666",
                "date_of_birth": "1994-06-25",
                "gender": "FEMALE",
                "blood_group": "A+",
                "tshirt_size": "M",
                "emergency_contact_name": "Rahul Das",
                "emergency_contact_phone": "+919888777665",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    order_id = init_data["razorpay_order_id"]
    reg_id = init_data["registration_id"]

    # Verify payment
    pay_id = "pay_zoho_test_001"
    sig = generate_sig(order_id, pay_id)
    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200

    # Check that participant has zoho_lead_id populated and integration_log is SUCCESS
    async with AsyncSessionLocal() as session:
        query = select(Participant).where(Participant.email == "kavita.das@example.com")
        p_res = await session.execute(query)
        participant = p_res.scalar_one()
        assert participant.zoho_lead_id is not None
        assert participant.zoho_lead_id.startswith("mock_zoho_rec_")

        log_query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "ZOHO_CRM",
        )
        l_res = await session.execute(log_query)
        log = l_res.scalar_one_or_none()
        assert log is not None
        assert log.status == "SUCCESS"


# 7. Zoho API Failure Handling
@pytest.mark.asyncio
async def test_zoho_api_failure_logging(async_client: AsyncClient):
    # Enable simulated failure
    zoho_client.set_mock_failure(True)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "Aditya Roy",
                "email": "aditya.fail@example.com",
                "phone_number": "+919777111222",
                "date_of_birth": "1991-03-12",
                "gender": "MALE",
                "blood_group": "B+",
                "tshirt_size": "XL",
                "emergency_contact_name": "Siddharth Roy",
                "emergency_contact_phone": "+919777111223",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert init_res.status_code == 201
    reg_id = init_res.json()["registration_id"]

    # Trigger sync under failure condition
    async with AsyncSessionLocal() as session:
        result = await zoho_service.sync_registration_to_zoho(db=session, registration_id=reg_id)
        assert result["status"] == "FAILED"
        assert result["retryable"] is True

        # Check integration_log
        log_query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "ZOHO_CRM",
        )
        l_res = await session.execute(log_query)
        log = l_res.scalar_one()
        assert log.status == "FAILED"
        assert log.error_message is not None


# 8. Retryable Failure Recovery
@pytest.mark.asyncio
async def test_retry_failed_zoho_sync(async_client: AsyncClient):
    # 1. Fail first
    zoho_client.set_mock_failure(True)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "5K",
            "participant": {
                "full_name": "Neha Sharma",
                "email": "neha.retry@example.com",
                "phone_number": "+919666555444",
                "date_of_birth": "1998-11-20",
                "gender": "FEMALE",
                "blood_group": "O+",
                "tshirt_size": "S",
                "emergency_contact_name": "Varun Sharma",
                "emergency_contact_phone": "+919666555445",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    reg_id = init_res.json()["registration_id"]

    async with AsyncSessionLocal() as session:
        await zoho_service.sync_registration_to_zoho(db=session, registration_id=reg_id)

    # 2. Heal service and trigger retry
    zoho_client.set_mock_failure(False)

    async with AsyncSessionLocal() as session:
        retry_reports = await zoho_service.retry_failed_zoho_syncs(db=session)
        assert len(retry_reports) >= 1
        assert any(r["registration_id"] == reg_id for r in retry_reports)

        # Confirm status updated to SUCCESS
        log_query = select(IntegrationLog).where(
            IntegrationLog.registration_id == reg_id,
            IntegrationLog.service_name == "ZOHO_CRM",
        )
        l_res = await session.execute(log_query)
        logs = l_res.scalars().all()
        assert len(logs) >= 1
        assert any(log.status == "SUCCESS" for log in logs)


# 9. Invalid Credentials Handling
def test_invalid_credentials_handling():
    assert settings.is_zoho_configured() is False # In default test mode, keys are blank
    assert zoho_client.is_mock_mode() is True # Safely defaults to mock mode


# 10. Successful Payment Remains CONFIRMED When Zoho Fails
@pytest.mark.asyncio
async def test_payment_remains_confirmed_when_zoho_fails(async_client: AsyncClient):
    # Inject Zoho failure
    zoho_client.set_mock_failure(True)

    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Sunil Chhetri",
                "email": "sunil.chhetri@example.com",
                "phone_number": "+919111222333",
                "date_of_birth": "1984-08-03",
                "gender": "MALE",
                "blood_group": "AB+",
                "tshirt_size": "M",
                "emergency_contact_name": "Sonam Bhattacharya",
                "emergency_contact_phone": "+919111222334",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    init_data = init_res.json()
    order_id = init_data["razorpay_order_id"]
    reg_code = init_data["registration_code"]

    pay_id = "pay_zoho_fail_test_001"
    sig = generate_sig(order_id, pay_id)

    # Payment verification must SUCCEED with HTTP 200
    verify_res = await async_client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    # Registration must be CONFIRMED in database
    detail_res = await async_client.get(f"/api/v1/registrations/{reg_code}")
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "CONFIRMED"


# 11. Idempotent Retry Does Not Duplicate
@pytest.mark.asyncio
async def test_idempotent_retry_does_not_duplicate(async_client: AsyncClient):
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "Manish Paul",
                "email": "manish.paul@example.com",
                "phone_number": "+919333444555",
                "date_of_birth": "1987-04-10",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "L",
                "emergency_contact_name": "Sanyukta Paul",
                "emergency_contact_phone": "+919333444556",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    reg_id = init_res.json()["registration_id"]

    async with AsyncSessionLocal() as session:
        res1 = await zoho_service.sync_registration_to_zoho(db=session, registration_id=reg_id)
        assert res1["status"] == "SUCCESS"
        first_id = res1["zoho_record_id"]

        # Run sync again
        res2 = await zoho_service.sync_registration_to_zoho(db=session, registration_id=reg_id)
        assert res2["status"] == "SUCCESS"
        assert res2["zoho_record_id"] == first_id
        assert res2["action"] == "updated"
