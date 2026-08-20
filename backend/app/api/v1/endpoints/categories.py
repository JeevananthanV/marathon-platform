from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.race_category import RaceCategory
from app.schemas.race_category import RaceCategoryResponse

router = APIRouter()


@router.get("", response_model=List[RaceCategoryResponse], summary="List all active race categories")
async def list_race_categories(db: AsyncSession = Depends(get_db)):
    """Fetch all active marathon race categories (5K, 10K, 21K) with remaining capacity."""
    query = select(RaceCategory).where(RaceCategory.is_active == True).order_by(RaceCategory.distance_km.asc())
    result = await db.execute(query)
    categories = result.scalars().all()
    return categories


@router.get("/{category_id}", response_model=RaceCategoryResponse, summary="Get category by ID or Code")
async def get_race_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch specific race category by ID or code (5K, 10K, 21K)."""
    query = select(RaceCategory).where(
        (RaceCategory.id == category_id) | (RaceCategory.code == category_id.upper())
    )
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race category '{category_id}' not found.",
        )
    return category
