"""
Bharat Voice AI — Services Package

Service factory functions for STT, LLM, TTS, and Weather.
Each factory creates a configured, ready-to-use service instance.
"""

from services.weather import get_weather_service

__all__ = ["get_weather_service"]
