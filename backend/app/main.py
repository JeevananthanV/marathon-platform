from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.security_headers import SecurityHeadersMiddleware, RateLimiterMiddleware
from app.api.v1.api_router import api_router
from app.db.session import engine, get_db, AsyncSessionLocal
from app.db.base import Base
from app.db.seed import seed_race_categories
from app.schemas.health import HealthResponse

# Initialize logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION})...")
    logger.info(f"Connecting to database: {settings.ASYNC_DATABASE_URL.split('@')[-1] if '@' in settings.ASYNC_DATABASE_URL else settings.ASYNC_DATABASE_URL}")
    
    # Auto-create tables for local testing / development if using SQLite or fresh db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed default race categories
    async with AsyncSessionLocal() as session:
        await seed_race_categories(session)
    
    logger.info("Database schema initialized and default categories verified.")
    yield
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Database engine disposed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 1. Security Headers Middleware (OWASP recommended)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate Limiting Middleware (DDoS & Brute Force Prevention)
app.add_middleware(RateLimiterMiddleware, default_limit=150, window_seconds=60)

# 3. GZip Compression Middleware (Performance Optimization for payloads > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Input validation failed. Please check your data.",
            "details": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# Root Health Check Endpoints (Satisfies GET /api/health and GET /health)
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def root_health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint checking application and database readiness."""
    db_status = "healthy"
    try:
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


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/api/health",
    }
