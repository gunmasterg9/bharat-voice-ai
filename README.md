# 🇮🇳 Bharat Voice AI

**A production-quality multilingual AI Voice Assistant for India.**

Built for the **10 Days of AI Voice Agents | Voice for Bharat Edition** challenge.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Murf Falcon](https://img.shields.io/badge/TTS-Murf%20Falcon-6366F1)](https://murf.ai/api/docs/text-to-speech/streaming)
[![LiveKit](https://img.shields.io/badge/Transport-LiveKit-002cf2)](https://docs.livekit.io)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4285F4)](https://ai.google.dev/)
[![Deepgram](https://img.shields.io/badge/STT-Deepgram%20Nova--3-13EF93)](https://deepgram.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## Overview

Bharat Voice AI is a multilingual conversational assistant that speaks and understands Indian languages naturally. It uses a real-time voice pipeline:

```
User speaks → Deepgram STT → Google Gemini → Murf Falcon TTS → User hears
```

**Key Features:**
- 🗣️ **Multilingual** — Responds in the same language as the user (Hindi, English, Tamil, Bengali, etc.)
- ⚡ **Low latency** — Preemptive generation + Murf Falcon's 55ms model latency
- 🔇 **Noise cancellation** — Built-in BVC noise cancellation for clean audio
- 🔄 **Interrupt support** — Natural turn-taking with multilingual turn detection
- 🎯 **Voice-optimized** — Concise 1-3 sentence responses designed for spoken delivery

---

## Architecture

```mermaid
flowchart LR
    A[🎙️ User speaks] -->|audio| B[Deepgram STT]
    B -->|text| C[Gemini 2.5 Flash]
    C -->|response text| D[Murf Falcon TTS]
    D -->|audio| E[LiveKit]
    E -->|stream| F[🔊 User hears]

    style A fill:#444441,stroke:#888780,color:#fff
    style B fill:#185FA5,stroke:#85B7EB,color:#fff
    style C fill:#534AB7,stroke:#AFA9EC,color:#fff
    style D fill:#0F6E56,stroke:#5DCAA5,color:#fff
    style E fill:#D85A30,stroke:#F0997B,color:#fff
    style F fill:#444441,stroke:#888780,color:#fff
```

### Detailed Pipeline

```
Microphone → LiveKit Room → Noise Cancellation → Silero VAD
→ Deepgram Nova-3 STT → Multilingual Turn Detector
→ Gemini 2.5 Flash LLM → Sentence Tokenizer
→ Murf Falcon TTS (Anisha, en-IN) → LiveKit Room → Speaker
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Transport** | [LiveKit Agents SDK](https://docs.livekit.io/agents) | Real-time WebRTC audio |
| **STT** | [Deepgram Nova-3](https://deepgram.com) | Speech-to-text |
| **LLM** | [Google Gemini 2.5 Flash](https://ai.google.dev/) | Conversational AI |
| **TTS** | [Murf Falcon](https://murf.ai/api) | Text-to-speech (55ms latency) |
| **VAD** | [Silero VAD](https://github.com/snakers4/silero-vad) | Voice activity detection |
| **Turn Detection** | LiveKit Multilingual | End-of-turn detection |
| **Frontend** | Next.js + TypeScript | Web UI |

---

## Project Structure

```
bharat-voice-ai/
├── backend/
│   ├── src/
│   │   ├── agent.py                 # Entrypoint — orchestrates the pipeline
│   │   ├── agent/                   # Core agent package
│   │   │   ├── config.py            # Centralized configuration
│   │   │   ├── prompts.py           # System prompt (multilingual)
│   │   │   ├── gemini.py            # Gemini LLM integration
│   │   │   ├── voice_agent.py       # BharatVoiceAgent class
│   │   │   ├── logger.py            # Structured logging
│   │   │   └── utils.py             # Utilities & retry logic
│   │   └── services/                # Service factories
│   │       ├── stt.py               # Deepgram STT
│   │       ├── tts.py               # Murf Falcon TTS
│   │       └── llm.py               # LLM service
│   ├── tests/                       # LLM-judged evaluation tests
│   ├── .env.example                 # Environment variable template
│   ├── pyproject.toml               # Python dependencies
│   └── Dockerfile                   # Production container
├── frontend/                        # Next.js voice UI
├── Architecture.md                  # Detailed architecture document
└── README.md                        # This file
```

---

## Installation

### Prerequisites

- **Python** 3.10+
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
  ```bash
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Node.js** 18+ and **pnpm**
  ```bash
  npm install -g pnpm
  ```
- API keys for: [LiveKit](https://cloud.livekit.io/), [Murf AI](https://murf.ai/api/dashboard), [Deepgram](https://console.deepgram.com/), [Google AI Studio](https://aistudio.google.com/apikey)

### Step 1: Clone the repo

```bash
git clone https://github.com/gunmasterg9/bharat-voice-ai.git
cd bharat-voice-ai
```

### Step 2: Configure environment variables

```bash
# Backend
cd backend
cp .env.example .env.local
# Edit .env.local with your API keys

# Frontend
cd ../frontend
cp .env.example .env.local
# Edit .env.local with your LiveKit keys
```

| Variable | Where to get it | Required |
|----------|----------------|----------|
| `LIVEKIT_URL` | [LiveKit Cloud](https://cloud.livekit.io/) | ✅ |
| `LIVEKIT_API_KEY` | [LiveKit Cloud](https://cloud.livekit.io/) | ✅ |
| `LIVEKIT_API_SECRET` | [LiveKit Cloud](https://cloud.livekit.io/) | ✅ |
| `MURF_API_KEY` | [murf.ai/api](https://murf.ai/api/dashboard) | ✅ |
| `DEEPGRAM_API_KEY` | [deepgram.com](https://console.deepgram.com/) | ✅ |
| `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) | ✅ |

### Step 3: Install dependencies

```bash
# Backend
cd backend
uv sync
uv run python src/agent.py download-files

# Frontend
cd ../frontend
pnpm install
```

---

## Running

### Option A: All-in-one (from repo root)

```bash
# Windows (PowerShell)
.\start_app.ps1

# macOS/Linux
chmod +x start_app.sh && ./start_app.sh
```

### Option B: Separate terminals

```bash
# Terminal 1 — LiveKit Server (local dev)
livekit-server --dev

# Terminal 2 — Backend agent
cd backend && uv run python src/agent.py dev

# Terminal 3 — Frontend
cd frontend && pnpm dev
```

Then open **http://localhost:3000** and click **Start Talking**.

### Console mode (no frontend needed)

```bash
cd backend && uv run python src/agent.py console
```

---

## Configuration

### Voice

Change the Murf Falcon voice via environment variables in `.env.local`:

```env
MURF_VOICE=Anisha
MURF_LOCALE=en-IN
MURF_STYLE=Conversation
```

Available Indian voices:

| Voice | Language | Gender |
|-------|----------|--------|
| `Anisha` | Indian English | Female |
| `Pooja` | Indian English | Female |
| `Samar` | Indian English | Male |

Browse all 150+ voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)

### LLM Model

```env
GEMINI_MODEL=gemini-2.5-flash
```

### STT Model

```env
DEEPGRAM_MODEL=nova-3
```

---

## Screenshots

> *Screenshots will be added after the first successful demo session.*

| Welcome Screen | Active Conversation |
|:---:|:---:|
| *Coming soon* | *Coming soon* |

---

## Demo

> 🎬 *Demo video link will be added here.*

---

## Deployment

### Railway (Backend)

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1)

Set environment variables: `MURF_API_KEY`, `DEEPGRAM_API_KEY`, `GOOGLE_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

### Vercel (Frontend)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/murf-ai/murf-livekit-starter&root-directory=frontend)

Set environment variables: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `AGENT_NAME=bharat-voice-ai`

### Docker

```bash
cd backend
docker build -t bharat-voice-ai .
docker run --env-file .env.local bharat-voice-ai
```

---

## Roadmap

- [x] Multilingual voice pipeline (STT → LLM → TTS)
- [x] Structured logging with latency tracking
- [x] Error handling with graceful fallbacks
- [x] Modular architecture with service factories
- [x] Environment-based configuration
- [x] Regional language voice selection (Hindi, Tamil, Bengali TTS voices)
- [x] Conversation memory / context persistence
- [x] Function tools (weather, news, translation)
- [x] Analytics dashboard for call metrics
- [x] Multi-agent routing by language
- [x] Whisper fallback for low-resource languages

---

## Links

- [Murf API Docs](https://murf.ai/api/docs)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Agents Docs](https://docs.livekit.io/agents)
- [Deepgram Docs](https://developers.deepgram.com)
- [Google Gemini Docs](https://ai.google.dev/docs)
- [Voice for Bharat Challenge](https://github.com/murf-ai/voice-for-bharat-challenge-2026)

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built with ❤️ for Bharat
</p>
