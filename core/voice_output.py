"""Text-to-speech output using pyttsx3 (offline, cross-platform)."""

import pyttsx3

from config import VOICE_RATE, VOICE_VOLUME
from utils.logger import get_logger

logger = get_logger(__name__)

_engine = None


def _get_engine():
    """Lazy-initialize the TTS engine with Daniel (British male) voice."""
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", VOICE_RATE)
        _engine.setProperty("volume", VOICE_VOLUME)

        # Find Daniel voice — prefer enhanced/premium, fall back to compact
        voices = _engine.getProperty("voices")
        daniel = None
        for voice in voices:
            vid = voice.id.lower()
            if "daniel" in vid and "en-gb" in vid:
                if "enhanced" in vid or "premium" in vid:
                    daniel = voice.id
                    break
                daniel = voice.id
        if daniel:
            _engine.setProperty("voice", daniel)
            logger.info(f"Voice set to: {daniel}")
        else:
            logger.warning("Daniel voice not found, using system default")

    return _engine


def speak(text: str) -> None:
    """Speak text aloud and print it to console."""
    print(f"Jarvis: {text}")
    try:
        engine = _get_engine()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logger.error(f"TTS error: {e}")
