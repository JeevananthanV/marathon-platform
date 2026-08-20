import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.integrations import (
    zoho_client,
    whatsapp_client,
    n8n_client,
    meta_capi_client,
)
from app.services.integration_dispatcher import integration_dispatcher
from app.models.registration import Registration
from app.models.integration_log import IntegrationLog
from app.db.session import AsyncSessionLocal


def test_integration_configuration_and_masking():
    # Test secret masking
    assert settings.mask_secret("") == "[NOT SET]"
    assert settings.mask_secret(None) == "[NOT SET]"
    assert settings.mask_secret("12345") == "***"
    assert settings.mask_secret("my_super_secret_token_1234") == "my_s...1234"

    # Test mock mode flag defaults
    assert settings.INTEGRATIONS_MOCK_MODE is True
    assert zoho_client.is_mock_mode() is True
    assert whatsapp_client.is_mock_mode() is True
    assert n8n_client.is_mock_mode() is True
    assert meta_capi_client.is_mock_mode() is True


@pytest.mark.asyncio
async def test_zoho_mock_adapter():
    lead_payload = {
        "full_name": "Priya Patel",
        "email": "priya.patel@example.com",
        "category": "10K",
        "utm_source": "instagram",
    }
    res = await zoho_client.upsert_lead(lead_payload, idempotency_key="test_lead_001")
    assert res["status"] == "success"
    assert res["service"] == "ZOHO_CRM"
    assert res["mock"] is True
    assert res["zoho_record_id"].startswith("mock_zoho_")

    contact_payload = {
        "registration_code": "MX26-000099",
        "bib_number": "10K-1099",
        "full_name": "Priya Patel",
    }
    deal_res = await zoho_client.create_confirmed_contact(contact_payload, idempotency_key="test_deal_001")
    assert deal_res["status"] == "success"
    assert deal_res["zoho_record_id"].startswith("mock_zoho_")


@pytest.mark.asyncio
async def test_whatsapp_mock_adapter():
    params = [{"type": "text", "text": "Priya Patel"}]
    res = await whatsapp_client.send_template_message(
        to_phone="+919876500000",
        template_name="marathon_pass_confirmed",
        parameters=params,
        idempotency_key="test_wa_001",
    )
    assert res["status"] == "success"
    assert res["service"] == "WHATSAPP"
    assert res["mock"] is True
    assert res["message_id"].startswith("MOCK_WHATSAPP_MSG_") or res["message_id"].startswith("wamid.mock_")


@pytest.mark.asyncio
async def test_n8n_mock_adapter():
    payload = {"event": "marathon.registration.confirmed", "amount": 899.0}
    res = await n8n_client.trigger_event("marathon.registration.confirmed", payload, idempotency_key="test_n8n_001")
    assert res["status"] == "success"
    assert res["service"] == "N8N"
    assert res["mock"] is True
    assert res["execution_id"].startswith("n8n_exec_mock_")


@pytest.mark.asyncio
async def test_meta_capi_mock_adapter_and_hashing():
    # Test SHA-256 normalizer and hasher
    email_hash = meta_capi_client.hash_sha256("  User.Test@Example.Com  ")
    assert len(email_hash) == 64 # Standard SHA256 hex length
    assert email_hash == meta_capi_client.hash_sha256("user.test@example.com")

    user_data = {
        "email": "user.test@example.com",
        "phone": "+91 98765 43210",
        "first_name": "Arjun",
        "city": "Bengaluru",
    }
    res = await meta_capi_client.send_event(
        event_name="Purchase",
        user_data=user_data,
        custom_data={"value": 1499.0, "currency": "INR"},
        event_id="test_ev_001",
    )
    assert res["status"] == "success"
    assert res["service"] == "META_CAPI"
    assert res["mock"] is True
    assert res["fbtrace_id"].startswith("fb_mock_trace_")


@pytest.mark.asyncio
async def test_integration_dispatcher_and_log_persistence(async_client: AsyncClient):
    # 1. Initiate a registration through API
    init_res = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Vikram Seth",
                "email": "vikram.seth@example.com",
                "phone_number": "+919876599999",
                "date_of_birth": "1990-08-10",
                "gender": "MALE",
                "blood_group": "B+",
                "tshirt_size": "L",
                "emergency_contact_name": "Anita Seth",
                "emergency_contact_phone": "+919876599998",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
        },
    )
    assert init_res.status_code == 201
    reg_id = init_res.json()["registration_id"]

    # 2. Dispatch all Phase 4 post-registration automations
    async with AsyncSessionLocal() as session:
        results = await integration_dispatcher.dispatch_registration_confirmed(
            db=session, registration_id=reg_id
        )

        assert results["zoho"] == "success"
        assert results["whatsapp"] == "success"
        assert results["n8n"] == "success"
        assert results["meta_capi"] == "success"

        # 3. Verify records stored in database integration_logs table
        query = select(IntegrationLog).where(IntegrationLog.registration_id == reg_id)
        logs_res = await session.execute(query)
        logs = logs_res.scalars().all()
        assert len(logs) == 4

        service_names = {log.service_name for log in logs}
        assert service_names == {"ZOHO_CRM", "WHATSAPP", "N8N", "META_CAPI"}

        for log in logs:
            assert log.status == "SUCCESS"
            assert log.retry_count == 0
            assert log.response_payload is not None
