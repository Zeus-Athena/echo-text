"""
Pytest Fixtures
共享测试夹具
"""

import asyncio
import io
import struct
import wave
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.user import User

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    """Create async engine for testing"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        await session.begin()
        yield session
        await session.rollback()


@pytest.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    """Get test client"""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def normal_user(db) -> User:
    """Create a normal user"""
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == "test@example.com"))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return existing_user

    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("password123"),
        role="user",
        can_use_admin_key=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def normal_user_token_headers(normal_user: User) -> dict:
    """Get token headers for normal user"""
    access_token = create_access_token(subject=str(normal_user.id))
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_wav_data():
    """
    Generate a valid WAV file with a 440Hz sine wave (1 second, 16kHz, mono, 16-bit).
    Returns WAV bytes.
    """
    sample_rate = 16000
    duration = 1.0  # seconds
    frequency = 440  # Hz (A4 note)
    amplitude = 16000  # 16-bit audio max is 32767

    num_samples = int(sample_rate * duration)
    samples = []

    import math

    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * math.sin(2 * math.pi * frequency * t))
        samples.append(value)

    # Create WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return buffer.getvalue()


@pytest.fixture
def silent_wav_data():
    """
    Generate a silent WAV file (1 second, 16kHz, mono, 16-bit).
    Returns WAV bytes.
    """
    sample_rate = 16000
    duration = 1.0
    num_samples = int(sample_rate * duration)

    # All zeros = silence
    samples = [0] * num_samples

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return buffer.getvalue()


@pytest.fixture
def short_wav_data():
    """
    Generate a very short WAV file (32ms, 16kHz, mono, 16-bit) for VAD testing.
    512 samples at 16kHz = 32ms, the exact input size for Silero VAD.
    """
    sample_rate = 16000
    num_samples = 512  # 32ms for VAD
    frequency = 440
    amplitude = 16000

    import math

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * math.sin(2 * math.pi * frequency * t))
        samples.append(value)

    # Create WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return buffer.getvalue()
