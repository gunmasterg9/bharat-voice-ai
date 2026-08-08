# Day 3 Implementation Analysis & Design Document

**Project:** Bharat Voice AI (10 Days of AI Voice Agents — Voice for Bharat Edition)  
**Task:** Day 3 Challenge — Personalized Multilingual Voice AI Frontend

---

## 1. Existing Frontend Architecture Analysis

### Core Tech Stack
- **Framework:** Next.js (App Router, React 19, TypeScript)
- **Voice Infrastructure:** `@livekit/components-react` (`useSession`, `useAgent`, `useVoiceAssistant`, `useSessionMessages`, `RoomAudioRenderer`)
- **Styling & UI:** Tailwind CSS, shadcn/ui components (`button`, `alert`, `sonner`), `lucide-react` & `@phosphor-icons/react`
- **Animations:** `motion/react` (Framer Motion)
- **Token Route:** `frontend/app/api/token/route.ts` issuing LiveKit access tokens to frontend clients.

### Connection Flow
1. User interacts with UI -> Invokes `start()` provided by `useSession()`.
2. `useSession` issues a request to `TokenSource.endpoint('/api/token')`.
3. `/api/token` uses `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` to mint a room token and returns server details (`wsUrl`, `token`).
4. `@livekit/components-react` connects to the LiveKit server room.
5. The Python backend (`backend/src/agent.py`) receives a room job, prewarms VAD, initializes STT (Deepgram), LLM (Gemini), and TTS (Murf Falcon), and greets the user.

### Discovered Components & Structure
- `frontend/app-config.ts`: Global configuration for branding, title, and feature flags.
- `frontend/components/app/app.tsx`: Roots the session with `AgentSessionProvider`, debug hooks, and toast alerts.
- `frontend/components/app/view-controller.tsx`: Controls transition between `WelcomeView` (disconnected) and `AgentSessionView_01` (connected).
- `frontend/components/agents-ui/`: Contains lower-level LiveKit visualizers, control bars, chat transcripts, and audio session wrappers.

---

## 2. Proposed Day 3 State Flow & State Machine

The interface will implement an explicit single source of truth for the voice agent state:

```
[ READY ] ──(Click Start + Mic Check)──> [ CONNECTING ] ──(Connected)──> [ LISTENING ]
    ▲                                           │                             │  ▲
    │                                     (Error/Fail)                   (Agent Speaking)
    │                                           │                             ▼  │
 [ CALL_ENDED ] ◄──(Click End Call)─────────────┴────────────────────── [ SPEAKING ]
    │
    └──(Click Start Again)──> [ CONNECTING ]
```

### Exact 5 Required States:
1. **`READY`**: Initial hero view with tagline, language highlights, explicit "Start Conversation" primary button with microphone icon. Mic is NOT auto-started.
2. **`CONNECTING`**: Shows "Connecting..." state with "Please wait while we connect you to Bharat Voice AI.", pulsing loader, and disabled duplicate clicks.
3. **`LISTENING`**: Displays "Listening to you" with animated mic indicator & live audio visualizer for user audio input.
4. **`SPEAKING`**: Displays "Bharat Voice AI is speaking" with speaker animation & live audio visualizer for Murf Falcon agent voice.
5. **`CALL_ENDED`**: Displays "Conversation ended", "Thanks for talking with Bharat Voice AI.", and a prominent "Start Again" button that reconnects without page refresh.

### Handled Error States:
- **`PERMISSION_ERROR`**: Displayed if microphone permission is denied or device is unavailable. Shows "Microphone access is blocked.", step-by-step instructions, and a "Try Again" button.
- **`CONNECTION_ERROR`**: Displayed if LiveKit connection fails or network drops. Shows "Unable to connect", internet troubleshooting tips, and a "Try Again" button.

---

## 3. Files to be Created & Modified

### New Files to Create:
- `DAY3_IMPLEMENTATION.md` (This documentation file)
- `docs/DAY3.md` (Comprehensive Day 3 documentation and user guide)
- `docs/screenshots/.gitkeep` (Placeholder directory for screenshots)
- `frontend/components/Header.tsx` (Top bar with branding, LiveKit status indicator, and theme switcher)
- `frontend/components/Footer.tsx` (Bottom bar with tagline and multilingual pills)
- `frontend/components/AgentStatus.tsx` (Active status banner, speaker indicator, and state descriptions)
- `frontend/components/VoiceButton.tsx` (Primary action button for Start, End, and Restart)
- `frontend/components/AudioVisualizer.tsx` (Responsive visualizer supporting both local microphone input and remote agent audio)
- `frontend/components/ConversationTranscript.tsx` (Compact live transcript drawer for You vs Bharat Voice AI)
- `frontend/components/PermissionError.tsx` (Friendly mic permission error card with step-by-step recovery)
- `frontend/components/ConnectionError.tsx` (Connection error card with retry mechanism)
- `frontend/components/VoiceAgent.tsx` (Master container combining state machine, LiveKit hooks, and UI components)

### Existing Files to Modify:
- `frontend/app-config.ts` (Update branding, page title, supporting copy, and defaults)
- `frontend/components/app/view-controller.tsx` (Render the new voice-first `VoiceAgent` component)
- `README.md` (Update project documentation with Day 3 features, state machine, and design decisions)
