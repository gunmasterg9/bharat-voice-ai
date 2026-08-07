# Day 2 Learned Guidelines — 10 Days of AI Voice Agents (Voice for Bharat Edition)

Source: Dr. Abhishek's Day 2 Video: "Give Your Agent a Personality, a Job, and Limits"

## Core System Architecture & Prompt Design Rules

1. **Structured Section Layout**:
   Prompt must explicitly contain:
   - `IDENTITY`: Name, role, organization/persona, female agreement rules for Hindi/Gujarati.
   - `OBJECTIVES`: 2-3 specific call outcomes defining a successful interaction.
   - `KNOWLEDGE`: Exact scope boundaries (Stop at live prices, medical diagnosis, financial approvals, legal advice).
   - `LANGUAGE`: Auto-detection & style mirroring (English, Hindi, Gujarati, Hinglish, Gujlish).
   - `GUARDRAILS`: Strict refusal triggers, Never-Claims policy, reusable escalation script.
   - `STYLE`: Speech-first delivery (10-20 word sentences, natural pauses, spoken numbers as words, no screen elements).

2. **Refusal & Escalation Standard**:
   Refusal must immediately return the standardized escalation path:
   > "I'm sorry, I can't safely help with that. Please contact the appropriate professional or official service. Is there something else I can help you with today?"

3. **Silence Handling Protocol**:
   - Turn 1 Silence: "Are you still there?"
   - Turn 2 Silence: "No problem. Feel free to come back anytime. Goodbye."

4. **Speech-First Optimization**:
   Never generate bullet points, numbered lists, markdown symbols, or text longer than 20 words per sentence.
