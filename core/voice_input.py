"""Microphone input using SpeechRecognition library."""

import speech_recognition as sr

from config import VOICE_TIMEOUT, VOICE_PHRASE_LIMIT, WAKE_WORD
from utils.logger import get_logger

logger = get_logger(__name__)

recognizer = sr.Recognizer()


def _get_mic_index() -> int | None:
    """Find the MacBook Pro Microphone index."""
    try:
        names = sr.Microphone.list_microphone_names()
        for i, name in enumerate(names):
            if "MacBook" in name and "Microphone" in name:
                return i
    except Exception:
        pass
    return None


def listen(timeout=None, phrase_limit=None) -> str | None:
    """Listen to microphone and return recognized text, or None on failure."""
    mic_index = _get_mic_index()
    t = timeout if timeout is not None else VOICE_TIMEOUT
    p = phrase_limit if phrase_limit is not None else VOICE_PHRASE_LIMIT

    with sr.Microphone(device_index=mic_index) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=t, phrase_time_limit=p)
            text = recognizer.recognize_google(audio)
            logger.info(f"Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None


def wait_for_wake_word() -> str | None:
    """Continuously listen until the wake word 'Jarvis' is heard.

    Returns the command portion after the wake word, or empty string
    if only the wake word was said (so we can prompt for a command).
    """
    mic_index = _get_mic_index()

    with sr.Microphone(device_index=mic_index) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)

        while True:
            try:
                # Listen with no timeout — blocks until speech is detected
                audio = recognizer.listen(source, phrase_time_limit=5)
                text = recognizer.recognize_google(audio).lower()
                logger.info(f"Background heard: {text}")

                if WAKE_WORD in text:
                    # Extract command after wake word if present
                    parts = text.split(WAKE_WORD, 1)
                    command = parts[1].strip() if len(parts) > 1 else ""
                    return command

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logger.error(f"Speech service error: {e}")
                continue
