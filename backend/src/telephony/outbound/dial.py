"""
Bharat Voice AI — Outbound Dialing Script

Initiates an outbound SIP call to Linphone via LiveKit Server API.

Command:
    uv run python src/telephony/outbound/dial.py --to gautammax
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import asyncio
import time
from pathlib import Path

# Ensure src directory is at position 0 of sys.path and remove local directory to avoid module shadowing
SRC_DIR = Path(__file__).resolve().parent.parent.parent
current_dir = str(Path(__file__).resolve().parent)
while current_dir in sys.path:
    sys.path.remove(current_dir)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from agent.config import load_settings  # noqa: E402
from agent.logger import setup_logging  # noqa: E402
from memory.memory_service import get_memory_service  # noqa: E402
from telephony.outbound.sip import (  # noqa: E402
    create_sip_participant,
    dispatch_agent_to_room,
)

setup_logging()


async def dial_linphone(to_user: str) -> None:
    """Execute outbound SIP dial workflow."""
    print("=" * 60)
    print("BHARAT VOICE AI — OUTBOUND CALL INITIATOR")
    print("=" * 60)

    # 1. Load Environment Configuration
    try:
        settings = load_settings()
    except OSError as exc:
        print("\nERROR: Failed to load configuration:")
        print(str(exc))
        sys.exit(1)

    # 2. Validate LiveKit Configuration
    if (
        not settings.livekit.url
        or not settings.livekit.api_key
        or not settings.livekit.api_secret
    ):
        print("\nERROR: LIVEKIT credentials (URL, API_KEY, API_SECRET) are incomplete.")
        sys.exit(1)

    # 3. Validate SIP Trunk ID
    trunk_id = settings.telephony.sip_trunk_id
    if not trunk_id:
        print("\nERROR: LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not configured.")
        sys.exit(1)

    # 4. Validate Destination User & Domain
    dest_username = to_user.strip() if to_user else settings.telephony.linphone_username
    if not dest_username:
        print("\nERROR: Linphone destination is missing.")
        sys.exit(1)

    # Clean destination username if full SIP URI was passed
    if dest_username.startswith("sip:"):
        dest_username = dest_username.replace("sip:", "").split("@")[0]

    domain = settings.telephony.linphone_domain or "sip.linphone.org"
    sip_uri = f"sip:{dest_username}@{domain}"

    # 5. Create Unique Room Name & Check User Profile
    timestamp = int(time.time())
    room_name = f"bharat-outbound-{dest_username}-{timestamp}"

    print("\n[OUTBOUND] Starting outbound call")
    print(f"[OUTBOUND] Destination username: {dest_username}")
    print(f"[OUTBOUND] SIP domain: {domain}")
    print("[OUTBOUND] Trunk ID configured: YES")
    print(f"[OUTBOUND DEBUG] ROOM NAME = {room_name}")
    print(f"[OUTBOUND DEBUG] SIP IDENTITY = {dest_username}")

    memory = get_memory_service()
    user_id = dest_username
    user_profile = memory.get_user(user_id) or memory.get_user("gautam")


    if not user_profile:
        # Seed test user profile for Gautam
        print(f"[OUTBOUND] Initializing user profile for '{user_id}'...")
        memory.save_user(
            user_id=user_id,
            name="Gautam",
            language_preference="Gujarati",
            facts={"location": "Veraval"},
        )
        memory.update_outbound_consent(user_id=user_id, consent=True, opted_out=False)
        user_profile = memory.get_user(user_id)

    has_consent = user_profile.get("outbound_call_consent", True)
    if not has_consent:
        print(f"[OUTBOUND] Re-enabling outbound calling consent for user '{user_id}'...")
        memory.update_outbound_consent(user_id=user_id, consent=True, opted_out=False)
        memory.update_outbound_consent(user_id="gautam", consent=True, opted_out=False)
        user_profile = memory.get_user(user_id) or memory.get_user("gautam")

    print("[OUTBOUND] Creating room")
    call_metadata = {
        "call_type": "outbound_weather_alert",
        "user_id": user_id,
        "user_name": user_profile.get("name", "Gautam"),
        "language": user_profile.get("language_preference", "Gujarati"),
        "destination": sip_uri,
    }

    # 7. Dispatch Agent Process
    print("[OUTBOUND] Dispatching agent")
    try:
        dispatch_res = await dispatch_agent_to_room(
            room_name=room_name,
            metadata=call_metadata,
            settings=settings,
        )
        dispatch_id = getattr(dispatch_res, "id", "dispatched")
        print(f"[OUTBOUND] Agent dispatched successfully (dispatch_id: {dispatch_id})")
    except Exception as exc:
        print("\nERROR: Outbound agent is not connected.")
        print(f"[OUTBOUND] Call failed: {exc}")
        print("[DEBUG] EXCEPTION: Outbound agent dispatch failed")
        sys.exit(1)

    # 8. Create SIP Participant to Dial Linphone
    print("[OUTBOUND] Creating SIP participant")
    try:
        sip_info = await create_sip_participant(
            room_name=room_name,
            phone_number=dest_username,
            participant_identity=dest_username,
            participant_name=user_profile.get("name", "Gautam"),
            metadata=call_metadata,
            settings=settings,
        )

        sip_call_id = getattr(sip_info, "sip_call_id", "created")
        print("[OUTBOUND] Call answered")
        print(f"[OUTBOUND] SIP participant created (SIP Call ID: {sip_call_id})")
        print(f"[OUTBOUND DEBUG] SIP CALL ID = {sip_call_id}")
        print("=" * 60)
        print(f"Call successfully ringing on Linphone! SIP Call ID: {sip_call_id}")
        print("=" * 60)
        print("[DEBUG] RETURN FROM DIAL FUNCTION")
    except Exception as exc:
        err_str = str(exc)
        print("\nERROR: LiveKit failed to create the outbound SIP participant.")
        print(f"[OUTBOUND] Call failed: {err_str}")
        print(f"[DEBUG] EXCEPTION: {err_str}")
        if "488" in err_str or "Not acceptable here" in err_str:
            print("\n" + "=" * 60)
            print("DIAGNOSTIC HINT — SIP STATUS 488 (Not acceptable here):")
            print("Linphone rejected the SDP media encryption offer.")
            print("To fix this in Linphone Mobile App:")
            print("1. Go to Settings -> Audio (or Settings -> Account -> Media Encryption).")
            print("2. Set 'Media Encryption' to 'SRTP' or 'None' (Disabled). Do NOT use ZRTP.")
            print("3. Verify Linphone status shows 'Connected' / 'Online' and retry.")
            print("=" * 60)
        sys.exit(1)




def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bharat Voice AI Outbound Call Dial Script"
    )
    parser.add_argument(
        "--to",
        type=str,
        default="gautammax",
        help="Linphone username or SIP URI (default: gautammax)",
    )
    args = parser.parse_args()

    asyncio.run(dial_linphone(args.to))


if __name__ == "__main__":
    main()
