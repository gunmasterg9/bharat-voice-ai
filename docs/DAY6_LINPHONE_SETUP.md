# Day 6: Linphone Mobile & Desktop SIP Setup Guide

## Linphone Account Details
- **Username**: `<YOUR_LINPHONE_USERNAME>`
- **SIP Domain**: `sip.linphone.org`
- **SIP Address**: `sip:<YOUR_LINPHONE_USERNAME>@sip.linphone.org`
- **Proxy / Registrar**: `sip:sip.linphone.org`

## LiveKit Outbound SIP Trunk
- **Trunk ID**: `<YOUR_LIVEKIT_SIP_OUTBOUND_TRUNK_ID>`
- **Trunk Name**: `linphone-trunk`
- **Transport**: `SIP_TRANSPORT_TLS`
- **Environment Variable**: `LIVEKIT_SIP_OUTBOUND_TRUNK_ID=<YOUR_LIVEKIT_SIP_OUTBOUND_TRUNK_ID>`

## Mobile App Setup Checklist (Critical for Audio)
1. **Account Registration**: Open Linphone -> Accounts -> Ensure account `sip:<YOUR_LINPHONE_USERNAME>@sip.linphone.org` shows green **Connected** status.
2. **Media Encryption**:
   - Go to **Settings -> Account -> Media Encryption** (or **Settings -> Audio**).
   - Set **Media Encryption** to **SRTP** or **None** (Disabled).
   - ⚠️ **Do NOT select ZRTP** (ZRTP causes immediate SDP 488 rejection and call drop).
3. **Audio Codecs**: Ensure **PCMU (G.711 u-law)** and **Opus** are enabled in Audio Codec preferences.

## Testing Outbound Calls
1. **Start Agent Worker** (Terminal 1):
   ```bash
   cd backend
   uv run python src/telephony/outbound/agent.py dev
   ```
2. **Dial Outbound Call** (Terminal 2):
   ```bash
   cd backend
   uv run python src/telephony/outbound/dial.py --to <YOUR_LINPHONE_USERNAME>
   ```
