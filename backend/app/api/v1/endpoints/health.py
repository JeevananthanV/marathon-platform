from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def check_health(db: AsyncSession = Depends(get_db)):
    """Health check endpoint checking application and database readiness."""
    db_status = "healthy"
    try:
        # Perform simple probe query
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database health check failed: {str(e)}")
        db_status = "degraded"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        database=db_status,
    )
