# Day 1: Get Your Voice Agent Talking — Technical Architecture

## Overview
Day 1 establishes the core streaming WebRTC voice pipeline connecting Speech-to-Text (STT), Large Language Model (LLM), and Text-to-Speech (TTS).

## Architecture Stack
- **STT**: Deepgram Nova-3 (`model="nova-3"`, multilingual real-time streaming)
- **LLM**: Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **TTS**: Murf Falcon & Falcon 2 (~100ms streaming latency, `Anisha` voice)
- **VAD & Turn Detection**: Silero VAD & LiveKit `MultilingualModel`
- **Orchestrator**: LiveKit Agents SDK `livekit-agents ~1.4`

## Pipeline Flow
```
User Audio Input -> LiveKit RTC -> Deepgram Nova-3 STT -> Google Gemini LLM -> Murf Falcon TTS -> LiveKit Audio Track Output
```
