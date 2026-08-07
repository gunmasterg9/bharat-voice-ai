# Bharat Voice AI — Backend Architecture

The backend of **Bharat Voice AI** is built on Python using the **LiveKit Agents SDK**, **Murf Falcon TTS**, **Deepgram Nova-3 STT**, and **Google Gemini 2.5 Flash**.

---

## Architecture Overview

```
backend/src/
├── agent.py          # Slim Orchestrator & LiveKit Entrypoint
├── agent/
│   ├── config.py     # Environment validation & pipeline settings
│   ├── prompts.py    # Structured Day 2 System Prompt (IDENTITY, OBJECTIVES, KNOWLEDGE, LANGUAGE, GUARDRAILS, ESCALATION, STYLE, VOICE RULES)
│   ├── guardrails.py # Safety Guardrail Engine & Refusal Rules
│   ├── language.py   # Language & Script Detection (HI, GU, EN, Hinglish, Gujlish)
│   ├── memory.py     # Persistent Session Memory Manager
│   ├── voice_agent.py# Core BharatVoiceAgent class & function tools
│   ├── logger.py     # Structured logging & latency metrics
│   ├── router.py     # Multi-language router adapter
│   ├── analytics.py  # Latency metrics aggregator
│   └── utils.py      # Timing decorators & retry helpers
└── services/
    ├── gemini.py     # Google Gemini LLM Integration
    ├── stt.py        # Deepgram Nova-3 STT Service
    ├── tts.py        # Murf Falcon TTS Service
    └── llm.py        # LLM Factory Abstraction
```

---

## Running the Backend

```bash
cd backend
uv sync
uv run python src/agent.py dev
```

For console terminal testing:

```bash
uv run python src/agent.py console
```

---

## Running Tests & Linter

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```
