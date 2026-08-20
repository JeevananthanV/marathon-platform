import os
import pytest
from httpx import AsyncClient, ASGITransport

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_marathon.db"
os.environ["DEBUG"] = "true"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_mock_123456"
os.environ["RAZORPAY_KEY_SECRET"] = "mock_secret_key_123456"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "mock_webhook_secret_123456"

from app.main import app
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.db.seed import seed_race_categories


@pytest.fixture(scope="session", autouse=True)
def clean_db_file():
    """Remove stale SQLite test db file before test session starts."""
    db_file = "./test_marathon.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    yield
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


@pytest.fixture(autouse=True)
async def setup_test_db():
    # Setup test tables and seed categories
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        await seed_race_categories(session)

    yield

    # Clean up records cleanly between tests without dropping schema tables
    async with AsyncSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != "race_categories":
                await session.execute(table.delete())
        await session.commit()


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
