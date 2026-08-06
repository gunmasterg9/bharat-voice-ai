# Bharat Voice AI — Architecture Document

## 1. Overview

Bharat Voice AI is a production-quality multilingual AI Voice Assistant built on top of the
[murf-livekit-starter](https://github.com/murf-ai/murf-livekit-starter) repository.
It is designed for users across India, supporting natural multilingual conversations
powered by:

| Component        | Technology           | Role                          |
|------------------|----------------------|-------------------------------|
| Real-time Transport | LiveKit Agents SDK | WebRTC audio, session mgmt   |
| Speech-to-Text   | Deepgram Nova-3      | Converts user speech to text  |
| LLM              | Google Gemini 2.5 Flash | Generates conversational responses |
| Text-to-Speech   | Murf Falcon          | Converts LLM text to natural voice |
| VAD              | Silero VAD           | Voice activity detection      |
| Turn Detection   | LiveKit Multilingual | Determines conversation turns |

---

## 2. Voice Pipeline Architecture

```
┌──────────────┐
│  User speaks │
│  (microphone)│
└──────┬───────┘
       │ audio stream
       ▼
┌──────────────────┐
│   LiveKit Room   │  ◄── WebRTC transport
│   (audio input)  │
└──────┬───────────┘
       │ raw audio
       ▼
┌──────────────────┐
│  Noise Cancel    │  ◄── BVC / BVCTelephony
│  (livekit-plugins│
│   -noise-cancel) │
└──────┬───────────┘
       │ clean audio
       ▼
┌──────────────────┐
│   Silero VAD     │  ◄── Pre-loaded in prewarm()
│  (voice activity │
│    detection)    │
└──────┬───────────┘
       │ speech segments
       ▼
┌──────────────────┐
│  Deepgram STT    │  ◄── nova-3 model
│  (speech → text) │
└──────┬───────────┘
       │ transcribed text
       ▼
┌──────────────────┐
│  Turn Detector   │  ◄── Multilingual model
│  (end-of-turn    │
│   detection)     │
└──────┬───────────┘
       │ complete utterance
       ▼
┌──────────────────┐
│  Gemini 2.5      │  ◄── System prompt + user message
│  Flash LLM       │      Preemptive generation enabled
│  (text → text)   │
└──────┬───────────┘
       │ response text
       ▼
┌──────────────────┐
│  Murf Falcon TTS │  ◄── Anisha voice, en-IN
│  (text → audio)  │      Sentence tokenizer
│                  │      Text pacing enabled
└──────┬───────────┘
       │ synthesized audio
       ▼
┌──────────────────┐
│   LiveKit Room   │  ◄── WebRTC transport
│   (audio output) │
└──────┬───────────┘
       │ audio stream
       ▼
┌──────────────┐
│  User hears  │
│  (speaker)   │
└──────────────┘
```

---

## 3. Startup Flow

1. **`agent.py`** is executed via `uv run python src/agent.py dev|start|console`
2. **`dotenv`** loads `.env.local` for API keys
3. **`AgentServer()`** is created as the server instance
4. **`prewarm()`** is registered as `server.setup_fnc` — pre-loads Silero VAD model
5. **`@server.rtc_session`** registers the `my_agent` handler for incoming sessions
6. **`cli.run_app(server)`** starts the LiveKit agent CLI (dev/start/console modes)

When a user connects:
1. LiveKit dispatches to the registered agent
2. `my_agent(ctx)` creates an `AgentSession` with the full pipeline
3. `session.start()` initializes the pipeline and connects the `Assistant` agent
4. `ctx.connect()` joins the LiveKit room

---

## 4. Folder Structure (After Refactor)

```
murf-livekit-starter/
├── Architecture.md              # This document
├── README.md                    # Professional project README
├── start_app.ps1                # Windows launcher
├── start_app.sh                 # Linux/macOS launcher
│
├── backend/
│   ├── src/
│   │   ├── agent.py             # Slim entrypoint (orchestrator)
│   │   │
│   │   ├── agent/               # Core agent package
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Centralized configuration
│   │   │   ├── prompts.py       # System prompt constants
│   │   │   ├── gemini.py        # Gemini LLM wrapper
│   │   │   ├── voice_agent.py   # BharatVoiceAgent class
│   │   │   ├── logger.py        # Structured logging
│   │   │   └── utils.py         # Utilities
│   │   │
│   │   └── services/            # Service factories
│   │       ├── __init__.py
│   │       ├── tts.py           # Murf Falcon TTS
│   │       ├── stt.py           # Deepgram STT
│   │       └── llm.py           # LLM service
│   │
│   ├── tests/
│   │   └── test_agent.py        # LLM-judged eval suite
│   ├── .env.example             # Environment variable template
│   ├── pyproject.toml           # Python dependencies
│   ├── Dockerfile               # Production container
│   └── railway.toml             # Railway deploy config
│
└── frontend/                    # Next.js UI (minimal changes)
    ├── app-config.ts            # Updated branding
    └── ...                      # Unchanged
```

---

## 5. Configuration Strategy

All configuration flows through `agent/config.py`:

```
.env.local (or environment variables)
        │
        ▼
  agent/config.py (Settings dataclass)
        │
        ├──► services/stt.py    → Deepgram STT instance
        ├──► services/tts.py    → Murf Falcon TTS instance
        ├──► services/llm.py    → Gemini LLM instance
        └──► agent/voice_agent.py → BharatVoiceAgent
```

Required environment variables:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY` (or `GEMINI_API_KEY`)

---

## 6. Error Handling Strategy

| Layer | Handling |
|-------|----------|
| Startup | Fail-fast validation of all required API keys |
| STT | Catch Deepgram connection errors, log and retry |
| LLM | Timeout (30s), retry with exponential backoff, empty response fallback |
| TTS | Catch Murf API errors, log with latency |
| LiveKit | Connection error logging, graceful disconnect |
| Runtime | Structured exception logging with context |

---

## 7. Logging Strategy

Structured JSON-style logs with:
- **Timestamps** (ISO 8601)
- **Component tags** (`[STT]`, `[LLM]`, `[TTS]`, `[AGENT]`)
- **Latency tracking** for STT, LLM, and TTS operations
- **Session context** (room name, participant ID)
- **Error details** with stack traces

---

## 8. Key Design Decisions

1. **LiveKit plugin for pipeline**: The main voice pipeline uses `livekit.plugins.google.LLM()` 
   for native streaming integration. A standalone `google-genai` helper is available for 
   non-pipeline use cases.

2. **Sentence tokenization**: Murf TTS uses `SentenceTokenizer(min_sentence_len=2)` with 
   `text_pacing=True` for natural speech cadence.

3. **Preemptive generation**: Enabled to reduce perceived latency — the LLM starts generating 
   before the user finishes speaking.

4. **Multilingual turn detection**: Uses `MultilingualModel()` instead of the default English 
   turn detector, critical for Indian language support.

5. **Noise cancellation**: Dynamic selection between `BVC()` (standard) and `BVCTelephony()` 
   (SIP calls) based on participant type.
