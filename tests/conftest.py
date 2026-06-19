import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Override sensitive settings BEFORE any app code uses them
from app.core.config import settings
settings.SECRET_KEY = "test-secret-key-must-be-at-least-32-characters"
settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
settings.REDIS_URL = ""
settings.SPOTIFY_CLIENT_ID = "test-spotify-id"
settings.SPOTIFY_CLIENT_SECRET = "test-spotify-secret"
settings.TICKETMASTER_API_KEY = "test-ticketmaster-key"
settings.FRONTEND_URL = "http://localhost:5173"

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.circle import Circle, CircleUser
from app.core.security import create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db):
    user = User(
        spotify_id="spotify_test_user_1",
        email="testuser@example.com",
        display_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        access_token="fake_spotify_access_token",
        refresh_token="fake_spotify_refresh_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user(db):
    user = User(
        spotify_id="spotify_test_user_2",
        email="seconduser@example.com",
        display_name="Second User",
        avatar_url=None,
        access_token="fake_spotify_access_token_2",
        refresh_token="fake_spotify_refresh_token_2",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(second_user):
    token = create_access_token(second_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_circle(db, test_user):
    circle = Circle(name="Test Circle", invite_code="TESTINVITE1", created_by=test_user.id)
    db.add(circle)
    await db.flush()
    db.add(CircleUser(circle_id=circle.id, user_id=test_user.id, role="creator"))
    await db.commit()
    await db.refresh(circle)
    return circle


@pytest_asyncio.fixture
async def two_member_circle(db, test_user, second_user, test_circle):
    db.add(CircleUser(circle_id=test_circle.id, user_id=second_user.id, role="member"))
    await db.commit()
    await db.refresh(test_circle)
    return test_circle
