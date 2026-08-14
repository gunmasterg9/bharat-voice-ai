"""
Bharat Voice AI — Agent Package

Production-quality multilingual AI Voice Assistant for India.
Built on LiveKit Agents, Murf Falcon TTS, Deepgram STT, and Google Gemini.
"""

__version__ = "1.0.0"
__app_name__ = "Bharat Voice AI"

from agent.specialist import BharatWeatherSpecialist
from agent.voice_agent import BharatVoiceAgent

__all__ = ["BharatVoiceAgent", "BharatWeatherSpecialist"]
