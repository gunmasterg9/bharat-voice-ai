"""
Bharat Voice AI — Analytics Dashboard & Metrics Collector

Tracks real-time call performance metrics:
- STT Transcription Latency
- LLM Response Latency
- TTS Audio Generation Duration
- Total Turn-around Time
- Session Call Summaries
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)

DEFAULT_ANALYTICS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
)


@dataclass
class CallMetric:
    """Metrics recorded for a single interaction turn."""

    session_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    stt_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    user_speech_bytes: int = 0
    language_detected: str = "en-IN"


@dataclass
class AnalyticsSummary:
    """Aggregate statistics for call performance monitoring."""

    total_calls: int = 0
    total_turns: int = 0
    avg_stt_latency_ms: float = 0.0
    avg_llm_latency_ms: float = 0.0
    avg_tts_latency_ms: float = 0.0
    avg_total_latency_ms: float = 0.0


class AnalyticsCollector:
    """Collects, aggregates, and persists call performance metrics."""

    def __init__(self, analytics_dir: Path | str = DEFAULT_ANALYTICS_DIR) -> None:
        self.analytics_dir = Path(analytics_dir)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: list[CallMetric] = []
        self._load_history()

    def record_turn(
        self,
        session_id: str,
        stt_latency_ms: float,
        llm_latency_ms: float,
        tts_latency_ms: float,
        language: str = "en-IN",
    ) -> CallMetric:
        """Record performance metrics for a single conversation turn."""
        total_latency_ms = stt_latency_ms + llm_latency_ms + tts_latency_ms
        metric = CallMetric(
            session_id=session_id,
            stt_latency_ms=round(stt_latency_ms, 2),
            llm_latency_ms=round(llm_latency_ms, 2),
            tts_latency_ms=round(tts_latency_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            language_detected=language,
        )
        self.metrics_history.append(metric)
        logger.info(
            "Recorded Turn Metrics [Session: %s] | STT: %.1fms | LLM: %.1fms | TTS: %.1fms | Total: %.1fms",
            session_id,
            stt_latency_ms,
            llm_latency_ms,
            tts_latency_ms,
            total_latency_ms,
        )
        self._save_history()
        return metric

    def get_summary(self) -> AnalyticsSummary:
        """Calculate overall performance metrics summary."""
        if not self.metrics_history:
            return AnalyticsSummary()

        count = len(self.metrics_history)
        stt_sum = sum(m.stt_latency_ms for m in self.metrics_history)
        llm_sum = sum(m.llm_latency_ms for m in self.metrics_history)
        tts_sum = sum(m.tts_latency_ms for m in self.metrics_history)
        total_sum = sum(m.total_latency_ms for m in self.metrics_history)

        sessions = {m.session_id for m in self.metrics_history}

        return AnalyticsSummary(
            total_calls=len(sessions),
            total_turns=count,
            avg_stt_latency_ms=round(stt_sum / count, 2),
            avg_llm_latency_ms=round(llm_sum / count, 2),
            avg_tts_latency_ms=round(tts_sum / count, 2),
            avg_total_latency_ms=round(total_sum / count, 2),
        )

    def _save_history(self) -> None:
        filepath = self.analytics_dir / "metrics_history.json"
        try:
            data = [asdict(m) for m in self.metrics_history[-500:]]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to persist analytics metrics: %s", str(exc))

    def _load_history(self) -> None:
        filepath = self.analytics_dir / "metrics_history.json"
        if not filepath.exists():
            return
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            self.metrics_history = [CallMetric(**m) for m in data]
        except Exception as exc:
            logger.error("Failed to load metrics history: %s", str(exc))


# Global singleton instance
analytics_collector = AnalyticsCollector()
