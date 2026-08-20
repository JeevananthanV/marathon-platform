import hmac
import hashlib
import pytest
from httpx import AsyncClient
from app.core.config import settings


ADMIN_HEADERS = {"X-Admin-API-Key": settings.ADMIN_API_KEY}


def generate_test_signature(order_id: str, payment_id: str, secret: str = settings.RAZORPAY_KEY_SECRET) -> str:
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


async def seed_test_leads_and_registrations(async_client: AsyncClient):
    # 1. Register Runner 1 (10K, Instagram)
    r1 = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "10K",
            "participant": {
                "full_name": "Aakash Mehta",
                "email": "aakash.mehta@example.com",
                "phone_number": "+919811111111",
                "date_of_birth": "1994-06-15",
                "gender": "MALE",
                "blood_group": "O+",
                "tshirt_size": "L",
                "emergency_contact_name": "Rohan Mehta",
                "emergency_contact_phone": "+919811111112",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
            "utm": {
                "utm_source": "instagram",
                "utm_medium": "story_ad",
                "utm_campaign": "marathon_early_bird",
            },
        },
    )
    r1_data = r1.json()
    r1_order_id = r1_data["razorpay_order_id"]

    # 2. Register Runner 2 (21K, Facebook)
    r2 = await async_client.post(
        "/api/v1/registrations/initiate",
        json={
            "category_id": "21K",
            "participant": {
                "full_name": "Deepika Rao",
                "email": "deepika.rao@example.com",
                "phone_number": "+919822222222",
                "date_of_birth": "1996-03-20",
                "gender": "FEMALE",
                "blood_group": "A+",
                "tshirt_size": "M",
                "emergency_contact_name": "Suresh Rao",
                "emergency_contact_phone": "+919822222223",
                "city": "Bengaluru",
                "state": "Karnataka",
            },
            "utm": {
                "utm_source": "facebook",
                "utm_medium": "feed_ad",
                "utm_campaign": "marathon_21k_push",
            },
        },
    )
    r2_data = r2.json()

    # 3. Pay for Runner 1
    payment_id = "pay_mock_admin_001"
    valid_sig = generate_test_signature(r1_order_id, payment_id)
    await async_client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": r1_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": valid_sig,
        },
    )

    return r1_data, r2_data


@pytest.mark.asyncio
async def test_admin_auth_protection(async_client: AsyncClient):
    # 1. Missing Auth Header -> 401 Unauthorized
    res_no_auth = await async_client.get("/api/v1/admin/dashboard")
    assert res_no_auth.status_code == 401

    # 2. Invalid Key -> 401 Unauthorized
    res_bad_auth = await async_client.get(
        "/api/v1/admin/dashboard",
        headers={"X-Admin-API-Key": "wrong_key_12345"},
    )
    assert res_bad_auth.status_code == 401

    # 3. Valid X-Admin-API-Key Header -> 200 OK
    res_ok = await async_client.get("/api/v1/admin/dashboard", headers=ADMIN_HEADERS)
    assert res_ok.status_code == 200
    assert "total_leads" in res_ok.json()

    # 4. Valid Query Param Auth (for CSV exports) -> 200 OK
    res_query_auth = await async_client.get(
        f"/api/v1/admin/dashboard?admin_key={settings.ADMIN_API_KEY}"
    )
    assert res_query_auth.status_code == 200


@pytest.mark.asyncio
async def test_admin_dashboard_and_lead_lifecycle(async_client: AsyncClient):
    await seed_test_leads_and_registrations(async_client)

    dash_res = await async_client.get("/api/v1/admin/dashboard", headers=ADMIN_HEADERS)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_leads"] == 2
    assert dash["total_registrations"] == 2
    assert dash["paid_registrations"] == 1
    assert dash["pending_payments"] == 1
    assert dash["revenue_inr"] == 899.0
    assert dash["paid_participants_count"] == 1
    assert dash["average_order_value_inr"] == 899.0
    assert len(dash["categories"]) == 3
    assert len(dash["recent_registrations"]) == 2


@pytest.mark.asyncio
async def test_admin_lead_management_and_status_patch(async_client: AsyncClient):
    await seed_test_leads_and_registrations(async_client)

    # 1. Fetch leads list
    leads_res = await async_client.get("/api/v1/admin/leads", headers=ADMIN_HEADERS)
    assert leads_res.status_code == 200
    leads_data = leads_res.json()
    assert leads_data["total"] == 2
    assert len(leads_data["items"]) == 2

    # Find Deepika Rao (pending lead)
    deepika = next(item for item in leads_data["items"] if "Deepika" in item["name"])
    assert deepika["lead_status"] == "PAYMENT_PENDING"
    assert deepika["utm_source"] == "facebook"

    # Find Aakash Mehta (converted lead)
    aakash = next(item for item in leads_data["items"] if "Aakash" in item["name"])
    assert aakash["lead_status"] == "CONVERTED"

    # 2. Search leads by name
    search_res = await async_client.get(
        "/api/v1/admin/leads?search=Aakash", headers=ADMIN_HEADERS
    )
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["email"] == "aakash.mehta@example.com"

    # 3. Update Deepika's status to CONTACTED via PATCH
    patch_res = await async_client.patch(
        f"/api/v1/admin/leads/{deepika['id']}/status",
        headers=ADMIN_HEADERS,
        json={"status": "CONTACTED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["lead_status"] == "CONTACTED"

    # 4. Reject invalid status
    invalid_patch = await async_client.patch(
        f"/api/v1/admin/leads/{deepika['id']}/status",
        headers=ADMIN_HEADERS,
        json={"status": "INVALID_STATUS_XYZ"},
    )
    assert invalid_patch.status_code in [400, 422]


@pytest.mark.asyncio
async def test_admin_registrations_filtering_and_sorting(async_client: AsyncClient):
    await seed_test_leads_and_registrations(async_client)

    # 1. List all registrations
    regs_res = await async_client.get("/api/v1/admin/registrations", headers=ADMIN_HEADERS)
    assert regs_res.status_code == 200
    regs_data = regs_res.json()
    assert regs_data["total"] == 2

    # 2. Filter by status=CONFIRMED
    confirmed_res = await async_client.get(
        "/api/v1/admin/registrations?status=CONFIRMED", headers=ADMIN_HEADERS
    )
    assert confirmed_res.status_code == 200
    assert len(confirmed_res.json()["items"]) == 1
    assert confirmed_res.json()["items"][0]["status"] == "CONFIRMED"

    # 3. Filter by category=10K
    cat_res = await async_client.get(
        "/api/v1/admin/registrations?category=10K", headers=ADMIN_HEADERS
    )
    assert cat_res.status_code == 200
    assert len(cat_res.json()["items"]) == 1
    assert cat_res.json()["items"][0]["category_code"] == "10K"


@pytest.mark.asyncio
async def test_admin_analytics_and_funnel_calculations(async_client: AsyncClient):
    await seed_test_leads_and_registrations(async_client)

    # 1. Fetch Analytics
    analytics_res = await async_client.get("/api/v1/admin/analytics", headers=ADMIN_HEADERS)
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    # Funnel
    funnel = data["funnel"]
    assert funnel["total_leads"] == 2
    assert funnel["total_registered"] == 2
    assert funnel["total_paid"] == 1
    assert funnel["lead_to_reg_rate_pct"] == 100.0
    assert funnel["reg_to_paid_rate_pct"] == 50.0
    assert funnel["overall_conversion_rate_pct"] == 50.0

    # Categories
    categories = data["categories"]
    assert len(categories) == 3 # 5K, 10K, 21K
    codes = [c["category_code"] for c in categories]
    assert "5K" in codes and "10K" in codes and "21K" in codes

    # UTM Attribution
    utm_sources = data["utm_sources"]
    sources = [u["source"] for u in utm_sources]
    assert "instagram" in sources or "facebook" in sources

    # Revenue
    revenue = data["revenue"]
    assert revenue["total_revenue_inr"] == 899.0
    assert revenue["paid_participants_count"] == 1


@pytest.mark.asyncio
async def test_admin_csv_exports(async_client: AsyncClient):
    await seed_test_leads_and_registrations(async_client)

    # 1. Export Leads CSV
    leads_csv = await async_client.get(
        "/api/v1/admin/export/leads",
        headers=ADMIN_HEADERS,
    )
    assert leads_csv.status_code == 200
    assert "text/csv" in leads_csv.headers["content-type"]
    assert "marathon_leads.csv" in leads_csv.headers.get("content-disposition", "")
    content = leads_csv.text
    assert "Lead ID,Full Name,Email,Phone Number" in content
    assert "aakash.mehta@example.com" in content

    # 2. Export Registrations CSV
    regs_csv = await async_client.get(
        f"/api/v1/admin/export/registrations?admin_key={settings.ADMIN_API_KEY}"
    )
    assert regs_csv.status_code == 200
    assert "text/csv" in regs_csv.headers["content-type"]
    assert "marathon_registrations.csv" in regs_csv.headers.get("content-disposition", "")
    r_content = regs_csv.text
    assert "Registration ID,Registration Code,BIB Number" in r_content
    assert "MX26-" in r_content
