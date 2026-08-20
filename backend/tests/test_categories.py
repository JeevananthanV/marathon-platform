import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_race_categories(async_client: AsyncClient):
    response = await async_client.get("/api/v1/categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) >= 3

    codes = [c["code"] for c in categories]
    assert "5K" in codes
    assert "10K" in codes
    assert "21K" in codes

    for cat in categories:
        assert cat["price_inr"] > 0
        assert cat["slots_remaining"] >= 0
        assert "bib_prefix" in cat
        assert "distance_km" in cat


@pytest.mark.asyncio
async def test_get_single_category_by_code_and_id(async_client: AsyncClient):
    # Fetch by code
    res_code = await async_client.get("/api/v1/categories/21K")
    assert res_code.status_code == 200
    cat_data = res_code.json()
    assert cat_data["code"] == "21K"
    assert cat_data["title"] == "21K Half Marathon"
    assert cat_data["distance_km"] == 21.1

    # Fetch by UUID id
    cat_id = cat_data["id"]
    res_id = await async_client.get(f"/api/v1/categories/{cat_id}")
    assert res_id.status_code == 200
    assert res_id.json()["id"] == cat_id


@pytest.mark.asyncio
async def test_get_nonexistent_category(async_client: AsyncClient):
    response = await async_client.get("/api/v1/categories/INVALID_CATEGORY_CODE")
    assert response.status_code == 404
