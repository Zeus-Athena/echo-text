import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from app.services.llm_service import LLMService
from app.services.websocket.translation_handler import TranslationHandler


# Mock LLM Service
class MockLLMService(LLMService):
    def __init__(self):
        self.translate = AsyncMock(return_value="Translated Text")


@pytest.fixture
def mock_llm_service():
    return MockLLMService()


@pytest.mark.asyncio
async def test_token_bucket_initialization(mock_llm_service):
    """Test Case 1: Initialization State"""
    # Initialize with Capacity=10, RPM=60 (1 token/sec)
    handler = TranslationHandler(llm_service=mock_llm_service, rpm_limit=60)

    # Check default capacity (should be 10 as planned)
    assert handler.capacity == 10
    # Check initial tokens (should be full)
    assert handler.tokens == 10
    # Check refill rate (60 RPM / 60s = 1.0)
    assert handler.refill_rate == 1.0


@pytest.mark.asyncio
async def test_token_bucket_burst(mock_llm_service):
    """Test Case 2: Burst Consumption"""
    handler = TranslationHandler(mock_llm_service, rpm_limit=60)
    handler.capacity = 10
    handler.tokens = 10

    start_time = time.monotonic()

    # Consume 10 tokens instantly
    for _ in range(10):
        await handler._wait_for_rate_limit()

    end_time = time.monotonic()

    # Should be very fast (no sleep), definitely < 0.1s
    assert end_time - start_time < 0.1
    # Tokens should be 0 (or very close to 0 if time passed slightly)
    assert handler.tokens <= 0.1


@pytest.mark.asyncio
async def test_token_bucket_depleted_throttling(mock_llm_service):
    """Test Case 3: Throttling when Depleted"""
    handler = TranslationHandler(mock_llm_service, rpm_limit=600)
    # RPM 600 = 10 tokens/sec -> 0.1s per token

    handler.capacity = 10
    handler.tokens = 0  # Force empty
    handler.last_update = time.monotonic()

    start_time = time.monotonic()

    # Request 1 token
    await handler._wait_for_rate_limit()

    end_time = time.monotonic()
    elapsed = end_time - start_time

    # Should wait roughly 0.1s
    assert 0.09 <= elapsed <= 0.2


@pytest.mark.asyncio
async def test_token_bucket_refill(mock_llm_service):
    """Test Case 4: Refill Mechanism"""
    handler = TranslationHandler(mock_llm_service, rpm_limit=60)  # 1 token/sec
    handler.capacity = 10
    handler.tokens = 0
    handler.last_update = time.monotonic() - 5.0  # Simulate 5 seconds passed

    # Trigger an update (the logic usually runs inside _wait_for_rate_limit,
    # but we need to check state before consuming.
    # We can create a dummy wait that consumes nothing or check internal logic if exposed.
    # For now, let's call _wait_for_rate_limit which updates then consumes 1)

    await handler._wait_for_rate_limit()

    # 5 seconds passed -> +5 tokens. Consumed 1 -> Remaining ~4
    assert 3.9 <= handler.tokens <= 4.1


@pytest.mark.asyncio
async def test_real_scenario_simulation(mock_llm_service):
    """Test Case 5: Real Scenario (Burst -> Pause -> Burst)"""
    # RPM=60 (1/s), Capacity=5 (Small capacity for testing)
    handler = TranslationHandler(mock_llm_service, rpm_limit=60)
    handler.capacity = 5
    handler.tokens = 5

    # 1. Burst 5 (should be instant)
    t0 = time.monotonic()
    for _ in range(5):
        await handler._wait_for_rate_limit()
    t1 = time.monotonic()
    assert t1 - t0 < 0.1
    assert handler.tokens <= 0.1

    # 2. Pause 2 seconds (should refill 2 tokens)
    await asyncio.sleep(2.05)

    # 3. Request 3 times
    # First 2 should be instant (consume the 2 refilled)
    # 3rd should wait ~1s (since rate is 1/s)

    t2 = time.monotonic()
    await handler._wait_for_rate_limit()  # Consumes token 1
    await handler._wait_for_rate_limit()  # Consumes token 2
    t3 = time.monotonic()

    # First 2 were instant?
    assert t3 - t2 < 0.1

    # 3rd request (Wait for 1s)
    await handler._wait_for_rate_limit()
    t4 = time.monotonic()

    # Should wait roughly 1s (0.9 - 1.2 range for buffer)
    assert 0.9 <= t4 - t3 <= 1.3
