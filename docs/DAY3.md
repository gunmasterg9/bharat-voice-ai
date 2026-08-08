# Day 3: Personalized Multilingual Frontend for Bharat Voice AI

Welcome to **Day 3** of the *10 Days of AI Voice Agents (Voice for Bharat Edition)* challenge.

---

## 🎯 Day 3 Objectives

1. **Voice-First User Interface**: Build a responsive, accessible, and modern frontend for **Bharat Voice AI** tailored for Indian users speaking in Hindi, Gujarati, English, and Hinglish/Gujlish.
2. **Strict 5-State Machine**: Implement single-source-of-truth state management covering:
   - `READY`
   - `CONNECTING`
   - `LISTENING`
   - `SPEAKING`
   - `CALL_ENDED`
3. **Clear Speaker Identification**: Distinct visual badges and volume dynamic waveforms for **User ("Listening to you")** vs **Agent ("Bharat Voice AI is speaking")**.
4. **Robust Error Handling**: Handle microphone permission blocks (`PERMISSION_ERROR`) and LiveKit network failures (`CONNECTION_ERROR`) cleanly without browser technical error dumps.
5. **Seamless Reconnection**: "Start Again" reconnects cleanly without requiring a full page refresh or leaking WebRTC streams/listeners.

---

## 🏗️ Frontend Architecture

```
frontend/
├── app-config.ts             # Global branding & configurations
├── app/
│   ├── layout.tsx            # Root layout with fonts & metadata
│   ├── page.tsx              # Main Next.js page
│   └── api/token/route.ts    # Secure LiveKit token endpoint
└── components/
    ├── VoiceAgent.tsx        # Master state machine & layout container
    ├── Header.tsx            # Top bar with branding & theme toggle
    ├── Footer.tsx            # Bottom bar with tagline & language pills
    ├── AgentStatus.tsx       # Active state header & speaker identification
    ├── VoiceButton.tsx       # Primary action button (Start, End, Restart)
    ├── AudioVisualizer.tsx   # Dual User/Agent audio volume visualizer
    ├── ConversationTranscript.tsx  # Compact live transcript drawer
    ├── PermissionError.tsx   # Microphone blocked error view
    └── ConnectionError.tsx   # Network connection error view
```

---

## 🔄 State Machine & User Flow

```
+-----------------------------------------------------------------------+
|                                READY                                  |
|  Display: "Bharat Voice AI"                                           |
|  Tagline: "Your voice. Your language. Your AI."                       |
|  Action: Click "Start Conversation" (Requires explicit user click)    |
+-----------------------------------+-----------------------------------+
                                    |
                                    v (Mic Check & session.start())
+-----------------------------------------------------------------------+
|                              CONNECTING                               |
|  Display: "Connecting..."                                             |
|  Supporting Text: "Please wait while we connect you to Bharat Voice AI"|
|  Behavior: Disabled repeated clicks, pulsing spinner                  |
+-----------------------------------+-----------------------------------+
                                    |
                                    v (Room Connected)
+-----------------------------------------------------------------------+
|                               LISTENING                               |
|  Speaker: User ("Listening to you")                                   |
|  Visual: User mic wave animation + live audio level dynamics           |
+-----------------------------------+-----------------------------------+
                                    |
                                    v (Agent responds via Murf Falcon)
+-----------------------------------------------------------------------+
|                               SPEAKING                                |
|  Speaker: Bharat Voice AI ("Bharat Voice AI is speaking")            |
|  Visual: Agent voice waveform animation                               |
+-----------------------------------+-----------------------------------+
                                    |
                                    v (User clicks "End Conversation")
+-----------------------------------------------------------------------+
|                              CALL_ENDED                               |
|  Display: "Conversation ended"                                        |
|  Supporting Text: "Thanks for talking with Bharat Voice AI."          |
|  Action: Click "Start Again" (Reconnects without page refresh)        |
+-----------------------------------------------------------------------+
```

---

## ⚠️ Error States & Recovery

### 1. Microphone Permission Error (`PERMISSION_ERROR`)
- **Trigger**: Browser denies mic permission (`NotAllowedError` / `NotFoundError`).
- **UI Display**: "Microphone access is blocked."
- **Recovery Guidance**: Step-by-step instructions on enabling mic access via browser address bar lock icon.
- **Action**: Prominent **"Try Again"** button re-initiates mic check and connection.

### 2. LiveKit Connection Error (`CONNECTION_ERROR`)
- **Trigger**: Server disconnect, offline network, or LiveKit token failure.
- **UI Display**: "Unable to connect"
- **Recovery Guidance**: "Please check your internet connection and try again."
- **Action**: Prominent **"Try Again"** button re-triggers connection.

---

## 📱 Mobile Responsiveness & Accessibility

- **Tested Resolutions**:
  - Mobile: `390 x 844` (iPhone 12/13/14)
  - Tablet: `768 x 1024` (iPad)
  - Desktop: `1440 x 900`
- **Accessibility**:
  - Explicit ARIA labels (`aria-label="Start voice conversation"`, `aria-label="End voice conversation"`).
  - High-contrast text compliance for light/dark modes.
  - Visible focus outlines for keyboard navigation.

---

## 🎥 Day 3 Demo Checklist

- [x] Page loads in `READY` state with tagline and language pills.
- [x] Click "Start Conversation" -> Transitions to `CONNECTING`.
- [x] Room connects -> Transitions to `LISTENING` ("Listening to you").
- [x] User speaks -> Visualizer reacts to local microphone input.
- [x] Agent responds -> Transitions to `SPEAKING` ("Bharat Voice AI is speaking").
- [x] Live transcript updates with You vs Agent messages.
- [x] Click "End Conversation" -> Transitions to `CALL_ENDED`.
- [x] Click "Start Again" -> Reconnects cleanly to `CONNECTING` -> `LISTENING` without page refresh.
