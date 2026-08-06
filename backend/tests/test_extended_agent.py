"""
Bharat Voice AI — Extended Feature Unit Tests

Tests for:
- Function Tools (Weather, News, Translation)
- Session Memory & Conversation Persistence
- Analytics & Latency Metrics Collector
- Language Router & Script Detection
- STT Fallback Handler
"""

import pytest

from agent.analytics import AnalyticsCollector
from agent.memory import ConversationMemoryStore
from agent.router import LanguageRouter
from agent.voice_agent import BharatVoiceAgent
from services.stt import FallbackSTT


def test_conversation_memory(tmp_path) -> None:
    """Test memory store session creation and history formatting."""
    memory_store = ConversationMemoryStore(memory_dir=tmp_path)
    session_id = "test_session_123"

    memory_store.add_turn(session_id, "user", "Namaste")
    memory_store.add_turn(session_id, "assistant", "Namaste! Kaise hain aap?")

    history = memory_store.get_formatted_history(session_id)
    assert "User: Namaste" in history
    assert "Assistant: Namaste! Kaise hain aap?" in history


def test_analytics_collector(tmp_path) -> None:
    """Test latency and turn metric recording."""
    analytics = AnalyticsCollector(analytics_dir=tmp_path)
    session_id = "test_session_analytics"

    metric = analytics.record_turn(
        session_id=session_id,
        stt_latency_ms=120.0,
        llm_latency_ms=350.0,
        tts_latency_ms=80.0,
        language="hi-IN",
    )

    assert metric.total_latency_ms == 550.0
    summary = analytics.get_summary()
    assert summary.total_turns == 1
    assert summary.avg_total_latency_ms == 550.0


def test_language_router() -> None:
    """Test regional script detection in language router."""
    router = LanguageRouter()

    hindi_profile = router.detect_language("नमस्ते, आप कैसे हैं?")
    assert hindi_profile.code == "hi"

    tamil_profile = router.detect_language("வணக்கம்")
    assert tamil_profile.code == "ta"

    english_profile = router.detect_language("Hello, how can you help me?")
    assert english_profile.code == "en"


@pytest.mark.asyncio
async def test_function_tools() -> None:
    """Test BharatVoiceAgent tool executions."""
    agent = BharatVoiceAgent(session_id="test_tool_session")

    weather_res = await agent.get_weather(context=None, location="Delhi")
    assert "28°C" in weather_res or "Delhi" in weather_res

    news_res = await agent.get_latest_news(context=None, category="technology")
    assert "AI" in news_res or "News" in news_res

    trans_res = await agent.translate_text(
        context=None, text="hello", target_language="Hindi"
    )
    assert "Namaste" in trans_res or "Hindi" in trans_res


def test_fallback_stt() -> None:
    """Test FallbackSTT wrapper initialization."""

    class MockSTT:
        model = "nova-3"

    mock = MockSTT()
    fallback = FallbackSTT(mock)
    assert fallback.model == "nova-3"
