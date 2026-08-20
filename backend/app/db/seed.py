import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.race_category import RaceCategory
from app.core.logging import logger

DEFAULT_CATEGORIES = [
    {
        "code": "5K",
        "title": "5K Fun Run",
        "distance_km": 5.0,
        "price_inr": 499.00,
        "max_capacity": 500,
        "bib_prefix": "5K",
        "min_age": 8,
        "start_time": "06:30 AM",
        "is_active": True,
    },
    {
        "code": "10K",
        "title": "10K Timed Run",
        "distance_km": 10.0,
        "price_inr": 899.00,
        "max_capacity": 500,
        "bib_prefix": "10K",
        "min_age": 12,
        "start_time": "06:00 AM",
        "is_active": True,
    },
    {
        "code": "21K",
        "title": "21K Half Marathon",
        "distance_km": 21.1,
        "price_inr": 1499.00,
        "max_capacity": 300,
        "bib_prefix": "HM",
        "min_age": 18,
        "start_time": "05:30 AM",
        "is_active": True,
    },
]


async def seed_race_categories(db: AsyncSession) -> None:
    """Seed initial race categories (5K, 10K, 21K) if they do not exist."""
    for cat_data in DEFAULT_CATEGORIES:
        query = select(RaceCategory).where(RaceCategory.code == cat_data["code"])
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if not existing:
            category = RaceCategory(
                id=str(uuid.uuid4()),
                title=cat_data["title"],
                code=cat_data["code"],
                distance_km=cat_data["distance_km"],
                price_inr=cat_data["price_inr"],
                max_capacity=cat_data["max_capacity"],
                current_count=0,
                bib_prefix=cat_data["bib_prefix"],
                min_age=cat_data["min_age"],
                start_time=cat_data["start_time"],
                is_active=cat_data["is_active"],
            )
            db.add(category)
            logger.info(f"Seeded race category: {cat_data['code']} - {cat_data['title']}")

    await db.commit()
