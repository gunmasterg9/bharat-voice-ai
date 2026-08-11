"""
Bharat Voice AI — Outbound Call Test Script

Usage:
    uv run python scripts/test_outbound_call.py --user-id gautam --phone +919876543210
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend/src to path and switch cwd to backend
backend_dir = Path(__file__).resolve().parent.parent / "backend"
backend_src = backend_dir / "src"
sys.path.insert(0, str(backend_src))
os.chdir(backend_dir)

from agent.config import load_settings
from agent.logger import setup_logging
from memory.memory_service import get_memory_service, mask_phone_number
from services.weather import get_weather_service
from telephony.call_manager import OutboundCallManager

setup_logging()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger test outbound call for Day 6.")
    parser.add_argument("--user-id", default="gautam", help="User ID to call")
    parser.add_argument("--phone", default="", help="Phone number (defaults to OUTBOUND_TEST_PHONE_NUMBER)")
    parser.add_argument("--location", default="Veraval", help="Saved location for weather check")
    parser.add_argument("--language", default="Gujarati", help="Preferred call language")
    parser.add_argument("--force", action="store_true", help="Bypass alert decision guardrails")

    args = parser.parse_args()

    settings = load_settings()
    memory = get_memory_service()

    # Pre-populate demo profile for Gautam if missing
    profile = memory.get_user(args.user_id)
    phone_to_use = args.phone or settings.telephony.outbound_test_phone_number or "+919876543210"

    print("=" * 60)
    print("  BHARAT VOICE AI — OUTBOUND CALL TEST LAUNCHER")
    print("=" * 60)
    print(f"  Target User ID: {args.user_id}")
    print(f"  Phone Number  : {mask_phone_number(phone_to_use)}")
    print(f"  Location      : {args.location}")
    print(f"  Language      : {args.language}")
    print(f"  Test Mode     : {settings.telephony.outbound_test_mode}")
    print("=" * 60)

    if not profile:
        print(f"[SETUP] Pre-populating demo user profile for '{args.user_id}'...")
        memory.save_user(
            user_id=args.user_id,
            name="Gautam",
            language_preference=args.language,
            facts={"location": args.location},
        )
        memory.update_user_phone(user_id=args.user_id, phone_number=phone_to_use, verified=True)
        memory.update_outbound_consent(user_id=args.user_id, consent=True, opted_out=False)
        profile = memory.get_user(args.user_id)
        print("[SETUP] Profile pre-populated successfully!")

    # Fetch live weather data for location
    weather_svc = get_weather_service()
    weather_res = await weather_svc.get_weather_data(location=args.location)
    weather_data = weather_res.get("data", {"precipitation_probability": 85, "condition": "Moderate rain"})

    manager = OutboundCallManager(settings=settings, memory_service=memory)
    res = await manager.place_outbound_call(
        phone_number=phone_to_use,
        user_id=args.user_id,
        reason="high_rain_probability",
        language=args.language,
        weather_data=weather_data,
        bypass_decision_checks=args.force,
    )

    print("\n" + "=" * 60)
    print("  OUTBOUND CALL RESULT")
    print("=" * 60)
    print(f"  Success : {res.get('success')}")
    print(f"  Status  : {res.get('status')}")
    print(f"  Call ID : {res.get('call_id')}")
    print(f"  Room    : {res.get('room_name')}")
    print(f"  Message : {res.get('message')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
