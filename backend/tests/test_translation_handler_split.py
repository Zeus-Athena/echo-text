
from unittest.mock import AsyncMock

import pytest

from app.services.websocket.translation_handler import TranslationHandler


class MockLLMService:
    def __init__(self):
        self.translate = AsyncMock()

@pytest.fixture
def handler():
    llm_service = MockLLMService()
    # default buffer_duration=2.0 (throttle mode)
    return TranslationHandler(llm_service, buffer_duration=2.0)

def test_split_text(handler):
    # Case 1: Standard
    text = "Hello world. This is a test."
    parts = handler._split_text(text)
    # Now expecting stripped results
    assert parts == ["Hello world.", "This is a test."]

    # Case 2: No punctuation
    text = "Hello world"
    parts = handler._split_text(text)
    assert parts == ["Hello world"]

    # Case 3: Trailing fragment
    text = "Hello world. This is"
    parts = handler._split_text(text)
    assert parts == ["Hello world.", "This is"]

    # Case 4: Multiple punctuation
    text = "Hello! How are you? I am fine."
    parts = handler._split_text(text)
    assert parts == ["Hello!", "How are you?", "I am fine."]

    # Case 5: Chinese punctuation
    text = "你好。这是一个测试！"
    parts = handler._split_text(text)
    assert parts == ["你好。", "这是一个测试！"]

@pytest.mark.asyncio
async def test_handle_transcript_sequential(handler):
    handler.llm_service.translate.side_effect = ["译文1", "译文2"]
    
    text = "Sentence one. Sentence two."
    
    handler._buffer = ""
    # This should trigger flush because it ends with punctuation
    results = await handler.handle_transcript(text, is_final=True)
    
    assert len(results) == 2
    assert results[0]["text"] == "译文1"
    assert results[1]["text"] == "译文2"
    
    assert handler.llm_service.translate.call_count == 2
    calls = handler.llm_service.translate.call_args_list
    assert calls[0][0][0] == "Sentence one."
    assert calls[1][0][0] == "Sentence two." 

@pytest.mark.asyncio
async def test_handle_transcript_buffers_fragment(handler):
    # Case where there is a fragment (no punctuation, short) -> Should buffer
    handler.llm_service.translate.side_effect = []
    
    text = "Part A"
    results = await handler.handle_transcript(text, is_final=True)
    
    assert len(results) == 0
    assert "Part A" in handler._buffer

@pytest.mark.asyncio
async def test_flush_handles_split(handler):
    # Verify flush splits content correctly
    handler.llm_service.translate.side_effect = ["Trans A", "Trans B"]
    handler._buffer = "Part A. Part B" # Manually set buffer like it accumulated
    
    results = await handler.flush()
    
    assert len(results) == 2
    assert results[0]["text"] == "Trans A"
    assert results[1]["text"] == "Trans B"
    
    calls = handler.llm_service.translate.call_args_list
    assert calls[0][0][0] == "Part A."
    assert calls[1][0][0] == "Part B"

@pytest.mark.asyncio
async def test_fast_mode_split(handler):
    # Test fast mode (buffer_duration=0) final result split
    handler.buffer_duration = 0
    handler.llm_service.translate.side_effect = ["Fast1", "Fast2"]
    
    text = "Fast A. Fast B."
    results = await handler.handle_transcript(text, is_final=True)
    
    assert len(results) == 2
    assert results[0]["text"] == "Fast1"
    assert results[1]["text"] == "Fast2"
