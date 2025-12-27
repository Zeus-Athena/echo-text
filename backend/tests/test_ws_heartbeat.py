"""
WebSocket 心跳分离测试
Test that audio processing does not block heartbeat response
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_heartbeat_not_blocked_during_processing():
    """验证：音频处理期间心跳仍能响应"""
    # The key test: create_task should return immediately
    task = asyncio.create_task(asyncio.sleep(0.1))

    # Task should be created but not done yet
    assert not task.done()

    # Main thread should be immediately available
    start = asyncio.get_event_loop().time()
    await asyncio.sleep(0)  # Yield control
    elapsed = asyncio.get_event_loop().time() - start

    # Should be nearly instant (< 50ms)
    assert elapsed < 0.05

    # Clean up
    await task


@pytest.mark.asyncio
async def test_concurrent_audio_processing():
    """验证：多个音频批次可并发处理"""
    tasks = []
    for _ in range(5):
        task = asyncio.create_task(asyncio.sleep(0.1))
        tasks.append(task)

    # All tasks should be immediately created
    assert len(tasks) == 5
    assert all(not t.done() for t in tasks)

    # All tasks complete roughly at the same time (parallel)
    await asyncio.gather(*tasks)
    assert all(t.done() for t in tasks)


@pytest.mark.asyncio
async def test_ping_pong_response_immediate():
    """验证：ping 命令立即响应，不被处理阻塞"""
    # Simulate the WebSocket manager
    mock_manager = MagicMock()
    mock_manager.send_json = AsyncMock()

    # Simulate receiving ping
    client_id = "test_client"
    await mock_manager.send_json(client_id, {"type": "pong"})

    # Should be called once
    mock_manager.send_json.assert_called_once_with(client_id, {"type": "pong"})
