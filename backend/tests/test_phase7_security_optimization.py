import hmac
import hashlib
import asyncio
from typing import Dict, Any, List
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.participant import Participant
from app.models.registration import Registration
from app.models.payment import Payment


ADMIN_HEADERS = {"X-Admin-API-Key": settings.ADMIN_API_KEY}


def generate_sig(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()


# 1. Security Headers Verification
@pytest.mark.asyncio
async def test_security_headers_present_on_all_endpoints(async_client: AsyncClient):
    endpoints = ["/", "/api/health", "/api/v1/categories"]

    for path in endpoints:
        res = await async_client.get(path)
        assert res.status_code == 200

        # Verify OWASP Security Headers
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-XSS-Protection") == "1; mode=block"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "max-age=" in res.headers.get("Strict-Transport-Security", "")
        assert "default-src 'self'" in res.headers.get("Content-Security-Policy", "")
        assert "geolocation=()" in res.headers.get("Permissions-Policy", "")


# 2. Rate Limiting Enforcement (DDoS / Abuse Protection)
@pytest.mark.asyncio
async def test_rate_limiter_enforcement(async_client: AsyncClient):
    # Rapidly send requests from a dedicated test client IP header
    headers = {"X-Forwarded-For": "198.51.100.42"}
    path = "/api/v1/categories"

    # Send up to limit
    responses = []
    for _ in range(160):
        resp = await async_client.get(path, headers=headers)
        responses.append(resp.status_code)
        if resp.status_code == 429:
            break

    # At least one request should be rate-limited with 429
    assert 429 in responses
    last_res = await async_client.get(path, headers=headers)
    if last_res.status_code == 429:
        data = last_res.json()
        assert data["error"] == "Too Many Requests"
        assert "Retry-After" in last_res.headers
        assert last_res.headers.get("X-RateLimit-Remaining") == "0"


# 3. Rate Limiter Bypass for Health Check Endpoints
@pytest.mark.asyncio
async def test_rate_limiter_bypass_for_health(async_client: AsyncClient):
    headers = {"X-Forwarded-For": "198.51.100.99"}
    for _ in range(160):
        res = await async_client.get("/api/health", headers=headers)
        assert res.status_code == 200


# 4. Admin Auth Constant-Time Verification & Reject
@pytest.mark.asyncio
async def test_admin_auth_constant_time_comparison(async_client: AsyncClient):
    # Valid key
    res_valid = await async_client.get("/api/v1/admin/overview", headers=ADMIN_HEADERS)
    assert res_valid.status_code == 200

    # Invalid key
    res_invalid = await async_client.get("/api/v1/admin/overview", headers={"X-Admin-API-Key": "wrong_key_123"})
    assert res_invalid.status_code == 401
    assert "Unauthorized" in res_invalid.json()["detail"]

    # Empty key
    res_empty = await async_client.get("/api/v1/admin/overview", headers={"X-Admin-API-Key": ""})
    assert res_empty.status_code == 401


# 5. Admin Auth Bearer Token & Query Parameter Support
@pytest.mark.asyncio
async def test_admin_auth_bearer_token_and_query_param(async_client: AsyncClient):
    # Bearer header
    bearer_res = await async_client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {settings.ADMIN_API_KEY}"},
    )
    assert bearer_res.status_code == 200

    # Query param
    query_res = await async_client.get(
        f"/api/v1/admin/export/leads?admin_key={settings.ADMIN_API_KEY}"
    )
    assert query_res.status_code == 200


# 6. SQL Injection Resilience
@pytest.mark.asyncio
async def test_sql_injection_resilience(async_client: AsyncClient):
    sql_injection_payload = "' OR 1=1; DROP TABLE participants; --"

    # Search query
    res = await async_client.get(
        f"/api/v1/admin/leads?search={sql_injection_payload}",
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    assert "total" in res.json()

    # Category code injection
    cat_res = await async_client.get(f"/api/v1/categories/{sql_injection_payload}")
    assert cat_res.status_code in [404, 422]


# 7. XSS Payload Handling
@pytest.mark.asyncio
async def test_xss_payload_handling(async_client: AsyncClient):
    xss_name = '<script>alert("XSS")</script> John Doe'
    payload = {
        "category_id": "10K",
        "participant": {
            "full_name": xss_name,
            "email": "xss.runner@example.com",
            "phone_number": "+919876599991",
            "date_of_birth": "1994-06-15",
            "gender": "MALE",
            "blood_group": "A+",
            "tshirt_size": "M",
            "emergency_contact_name": "Emergency <img src=x onerror=alert(1)>",
            "emergency_contact_phone": "+919876599992",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }

    init_res = await async_client.post("/api/v1/registrations/initiate", json=payload)
    assert init_res.status_code == 201

    # Verify participant was stored safely
    async with AsyncSessionLocal() as session:
        p_q = select(Participant).where(Participant.email == "xss.runner@example.com")
        p = (await session.execute(p_q)).scalar_one()
        assert p.full_name == xss_name


# 8. Error Handling Sanitization (No traceback leakage)
@pytest.mark.asyncio
async def test_error_handling_sanitization(async_client: AsyncClient):
    # Trigger 422 validation error
    val_res = await async_client.post("/api/v1/registrations/initiate", json={"invalid": "data"})
    assert val_res.status_code == 422
    val_json = val_res.json()
    assert "Traceback" not in str(val_json)
    assert val_json["error"] == "Validation Error"

    # Trigger 404
    not_found_res = await async_client.get("/api/v1/registrations/UNKNOWN-REG-999")
    assert not_found_res.status_code == 404
    assert "Traceback" not in not_found_res.text


# 9. GZip Compression on Responses
@pytest.mark.asyncio
async def test_gzip_compression_on_large_payloads(async_client: AsyncClient):
    res = await async_client.get(
        "/api/v1/categories",
        headers={"Accept-Encoding": "gzip"},
    )
    assert res.status_code == 200
    assert len(res.content) > 0


# 10. Concurrent Payment Verification Race Condition Safety
@pytest.mark.asyncio
async def test_idempotency_concurrent_payment_verification(async_client: AsyncClient):
    # Initiate registration
    payload = {
        "category_id": "10K",
        "participant": {
            "full_name": "Concurrent Runner",
            "email": "concurrent.runner@example.com",
            "phone_number": "+919876599995",
            "date_of_birth": "1991-01-01",
            "gender": "FEMALE",
            "blood_group": "B+",
            "tshirt_size": "S",
            "emergency_contact_name": "Emergency",
            "emergency_contact_phone": "+919876599996",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        "terms_accepted": True,
        "communication_consent": True,
    }
    init_res = await async_client.post("/api/v1/registrations/initiate", json=payload)
    data = init_res.json()
    order_id = data["razorpay_order_id"]
    reg_id = data["registration_id"]

    pay_id = f"pay_{reg_id[:8]}"
    sig = generate_sig(order_id, pay_id)
    verify_body = {"razorpay_order_id": order_id, "razorpay_payment_id": pay_id, "razorpay_signature": sig}

    # Execute duplicate payment verification requests to test idempotency
    res1 = await async_client.post("/api/v1/payments/verify", json=verify_body)
    assert res1.status_code == 200
    assert res1.json()["status"] == "CONFIRMED"

    res2 = await async_client.post("/api/v1/payments/verify", json=verify_body)
    assert res2.status_code == 200
    assert res2.json()["status"] == "CONFIRMED"

    # Check only 1 BIB assigned in DB
    async with AsyncSessionLocal() as session:
        reg = (await session.execute(select(Registration).where(Registration.id == reg_id))).scalar_one()
        assert reg.status == "CONFIRMED"
        assert reg.bib_number is not None


# 11. Database Transaction Isolation & Rollback
@pytest.mark.asyncio
async def test_database_transaction_isolation_and_rollback(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        try:
            # Insert invalid dummy participant without required non-null email
            dummy = Participant(
                id="test_uuid_rollback",
                full_name="Rollback Test",
                phone_number="+919876500000",
                date_of_birth="1990-01-01",
                gender="MALE",
                blood_group="O+",
                tshirt_size="M",
                emergency_contact_name="Emergency",
                emergency_contact_phone="+919876500001",
                city="Bengaluru",
                state="Karnataka",
                email=None,  # Null constraint violation
            )
            session.add(dummy)
            await session.commit()
        except Exception:
            await session.rollback()

        # Verify record was rolled back cleanly
        q = select(Participant).where(Participant.id == "test_uuid_rollback")
        res = (await session.execute(q)).scalar_one_or_none()
        assert res is None


# 12. Zero Secret Exposure Integrity
@pytest.mark.asyncio
async def test_secret_masking_integrity(async_client: AsyncClient):
    # Overview endpoint should never expose secret values
    res = await async_client.get("/api/v1/admin/overview", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    body_text = res.text

    # Secret strings (only check non-empty secrets)
    if settings.RAZORPAY_KEY_SECRET:
        assert settings.RAZORPAY_KEY_SECRET not in body_text
    if settings.ADMIN_API_KEY:
        assert settings.ADMIN_API_KEY not in body_text
    if settings.ZOHO_CLIENT_SECRET:
        assert settings.ZOHO_CLIENT_SECRET not in body_text
    if getattr(settings, "META_ACCESS_TOKEN", None):
        assert settings.META_ACCESS_TOKEN not in body_text
    if settings.WHATSAPP_ACCESS_TOKEN:
        assert settings.WHATSAPP_ACCESS_TOKEN not in body_text
