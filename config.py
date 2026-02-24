"""All configuration constants for Jarvis."""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM API settings (Gemini primary, Groq fallback, Anthropic optional)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Voice settings
VOICE_RATE = 160                    # Words per minute for TTS (slower = more Jarvis-like)
VOICE_VOLUME = 1.0                  # 0.0 to 1.0
VOICE_TIMEOUT = 5                   # Seconds to wait for speech
VOICE_PHRASE_LIMIT = 10             # Max seconds per phrase

# Selenium settings
BROWSER = "chrome"
HEADLESS = False
IMPLICIT_WAIT = 10                  # Seconds

# Web scraping settings
REQUEST_TIMEOUT = 10                # Seconds
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Desktop automation
PYAUTOGUI_PAUSE = 0.5              # Seconds between PyAutoGUI actions
PYAUTOGUI_FAILSAFE = True          # Move mouse to corner to abort

# Command settings
WAKE_WORD = "jarvis"
EXIT_COMMANDS = ["exit", "quit", "goodbye", "shut down", "stop"]
