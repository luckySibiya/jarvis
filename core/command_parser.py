"""Parse natural language input into structured commands using LLM APIs.

Provider chain: Google Gemini (free) → Groq (free) → Anthropic (paid fallback).
"""

import json
from dataclasses import dataclass, field

from google import genai
from groq import Groq
import anthropic

from config import (
    GOOGLE_API_KEY, GEMINI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
)
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Structured command after parsing."""
    category: str       # "web_auto", "desktop", "scrape", "system", "unknown"
    action: str         # Specific action
    args: dict = field(default_factory=dict)
    raw_input: str = ""


SYSTEM_PROMPT = """\
You are a command parser for a personal assistant called Jarvis. Your job is to \
interpret the user's natural language input and return a structured JSON command.

You MUST respond with ONLY valid JSON (no markdown, no explanation, no code fences). \
The JSON must have:
- "category": one of "web_auto", "desktop", "scrape", "system", "spotify", "chat"
- "action": the specific action to perform
- "args": a dictionary of arguments for the action

Available categories and actions:

web_auto (Selenium browser automation):
  - "google_search": Search Google. args: {"query": "search terms"}
  - "open_url": Open a URL. args: {"url": "https://..."}

desktop (PyAutoGUI desktop control):
  - "open_app": Open a macOS app. args: {"app_name": "Safari"}
  - "close_app": Close/quit a macOS app. args: {"app_name": "Safari"}
  - "type_text": Type text at cursor. args: {"text": "hello world"}
  - "screenshot": Take a screenshot. args: {}
  - "click_image": Click at coordinates. args: {"target": "500, 300"}

scrape (BeautifulSoup web scraping):
  - "weather": Get weather. args: {"city": "London"}
  - "news": Get news headlines. args: {"topic": "technology"} (topic can be "")
  - "stock_price": Get stock price. args: {"symbol": "AAPL"}
  - "scrape_url": Scrape a webpage. args: {"url": "https://..."}

spotify (Spotify music control):
  - "play": Play/resume Spotify. args: {}
  - "pause": Pause Spotify. args: {}
  - "next": Next track. args: {}
  - "previous": Previous track. args: {}
  - "current": What song is playing. args: {}
  - "play_search": Play a specific song/artist. args: {"query": "song or artist name"}

system (OS-level commands):
  - "time": Current time. args: {}
  - "date": Current date. args: {}
  - "battery": Battery level. args: {}
  - "wifi": Current Wi-Fi network. args: {}
  - "ip_address": Get IP addresses. args: {}
  - "disk_space": Available disk space. args: {}
  - "volume_up": Increase volume. args: {}
  - "volume_down": Decrease volume. args: {}
  - "volume_set": Set volume to level. args: {"level": 50}
  - "volume_mute": Mute. args: {}
  - "volume_unmute": Unmute. args: {}
  - "volume_get": Get current volume. args: {}
  - "brightness_up": Increase brightness. args: {}
  - "brightness_down": Decrease brightness. args: {}
  - "lock_screen": Lock the screen. args: {}
  - "sleep": Put Mac to sleep. args: {}
  - "restart": Restart Mac. args: {}
  - "shutdown": Shut down Mac. args: {}
  - "dark_mode_on": Enable dark mode. args: {}
  - "dark_mode_off": Disable dark mode. args: {}
  - "toggle_dark_mode": Toggle dark mode. args: {}
  - "wifi_on": Turn Wi-Fi on. args: {}
  - "wifi_off": Turn Wi-Fi off. args: {}
  - "bluetooth_on": Turn Bluetooth on. args: {}
  - "bluetooth_off": Turn Bluetooth off. args: {}
  - "empty_trash": Empty the Trash. args: {}
  - "show_desktop": Show desktop / minimize all. args: {}
  - "open_folder": Open folder in Finder. args: {"path": "/Users/..."}
  - "clipboard_read": Read clipboard. args: {}
  - "clipboard_write": Copy text to clipboard. args: {"text": "text to copy"}
  - "notify": Send macOS notification. args: {"message": "text", "title": "Jarvis"}
  - "do_not_disturb_on": Enable Do Not Disturb. args: {}
  - "do_not_disturb_off": Disable Do Not Disturb. args: {}
  - "set_timer": Set a timer. args: {"seconds": 300, "label": "tea timer"}
  - "cancel_timer": Cancel a timer. args: {"label": "tea timer"}
  - "calculate": Math calculation. args: {"expression": "2 + 2"}
  - "send_email": Send email. args: {"to": "a@b.com", "subject": "Hi", "body": "text"}
  - "run_command": Run any shell command. args: {"command": "ls -la"}

phone (Calls & messages — uses iPhone via macOS Continuity):
  - "call": Make a phone call. args: {"number": "+1234567890"}
  - "facetime": FaceTime video call. args: {"number": "+1234567890"}
  - "facetime_audio": FaceTime audio call. args: {"number": "+1234567890"}
  - "send_message": Send an iMessage/text. args: {"to": "+1234567890", "message": "hey"}
  - "read_messages": Read recent messages. args: {"contact": "John"} (contact can be "")

system (continued — reading & PIM):
  - "read_emails": Read latest inbox emails. args: {"count": 5}
  - "read_email_detail": Read full content of email N. args: {"index": 1}
  - "read_file": Read a file aloud. args: {"path": "/Users/.../file.txt"}
  - "read_calendar": Read upcoming calendar events. args: {"days": 1}
  - "read_reminders": Read pending reminders. args: {}
  - "add_reminder": Add a reminder. args: {"text": "Buy groceries"}
  - "add_event": Add a calendar event. args: {"title": "Meeting", "date": "2026-03-01", "time": "14:00"}
  - "read_notes": Read recent notes from Notes app. args: {}
  - "create_note": Create a note. args: {"title": "Ideas", "body": "Some text"}
  - "read_selected": Read the currently selected text on screen. args: {}

chat (Conversational responses):
  - "chat": General conversation, questions, jokes, opinions, greetings, or anything \
that is NOT a specific action above. args: {"message": "the user's full message"}

IMPORTANT: If the user is asking a question, making conversation, or saying something \
that doesn't map to a specific action above, ALWAYS use category "chat" with action \
"chat". Never use "unknown".

Rules:
- For URLs without http/https, prepend "https://"
- Stock symbols should be UPPERCASE
- Timer: convert spoken time to seconds (e.g. "5 minutes" -> 300, "1 hour" -> 3600)
- "play some music" or "play Spotify" -> spotify.play
- "play Drake" or "play Bohemian Rhapsody" -> spotify.play_search
- "what's playing" or "current song" -> spotify.current
- "open spotify" -> desktop.open_app, "open google.com" -> web_auto.open_url
- "set volume to 50" -> system.volume_set with level 50
- "what's 25 times 4" or "calculate 100/3" -> system.calculate
- "lock my computer" -> system.lock_screen
- "turn on dark mode" -> system.dark_mode_on
- "send email to john@gmail.com about meeting" -> system.send_email
- "call 0712345678" or "call mom" -> phone.call
- "facetime John" -> phone.facetime
- "send a message to John saying I'm on my way" -> phone.send_message
- "read my messages" -> phone.read_messages
- "check my emails" or "read my emails" -> system.read_emails
- "read the first email" -> system.read_email_detail with index 1
- "what's on my calendar" -> system.read_calendar
- "read my reminders" -> system.read_reminders
- "remind me to buy groceries" -> system.add_reminder
- "add a meeting on March 1st at 2pm" -> system.add_event
- "read my notes" -> system.read_notes
- "create a note called Ideas" -> system.create_note
- "read what's selected" or "read the screen" -> system.read_selected
- "read this file /path/to/file" -> system.read_file\
"""


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


_gemini_disabled = False


def _try_gemini(user_input: str) -> dict | None:
    """Try Google Gemini API."""
    global _gemini_disabled
    if not GOOGLE_API_KEY or _gemini_disabled:
        return None
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{SYSTEM_PROMPT}\n\nUser input: {user_input}",
        )
        result = _parse_json(response.text)
        logger.info(f"Gemini parsed: {result}")
        return result
    except Exception as e:
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "429" in err:
            logger.warning("Gemini quota exhausted, disabling for this session")
            _gemini_disabled = True
        else:
            logger.warning(f"Gemini failed: {err[:100]}")
        return None


def _try_groq(user_input: str) -> dict | None:
    """Try Groq API (Llama 3)."""
    if not GROQ_API_KEY:
        return None
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            max_tokens=256,
            temperature=0,
        )
        result = _parse_json(response.choices[0].message.content)
        logger.info(f"Groq parsed: {result}")
        return result
    except Exception as e:
        logger.warning(f"Groq failed: {e}")
        return None


def _try_anthropic(user_input: str) -> dict | None:
    """Try Anthropic Claude API (paid fallback)."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_input}],
        )
        result = _parse_json(message.content[0].text)
        logger.info(f"Anthropic parsed: {result}")
        return result
    except Exception as e:
        logger.warning(f"Anthropic failed: {e}")
        return None


# Provider chain: free first, paid last
_PROVIDERS = [
    ("Gemini", _try_gemini),
    ("Groq", _try_groq),
    ("Anthropic", _try_anthropic),
]


def parse_command(user_input: str) -> Command:
    """Parse user input using LLM APIs with fallback chain."""
    text = user_input.strip()

    for name, provider in _PROVIDERS:
        result = provider(text)
        if result:
            logger.info(f"Parsed by {name}")
            return Command(
                category=result.get("category", "unknown"),
                action=result.get("action", "unknown"),
                args=result.get("args", {}),
                raw_input=text,
            )

    logger.error("All LLM providers failed")
    return Command(category="unknown", action="unknown", raw_input=text)
