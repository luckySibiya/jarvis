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
- "category": one of "web_auto", "desktop", "scrape", "system", "chat", "unknown"
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

system (OS-level commands):
  - "time": Get current time. args: {}
  - "date": Get current date. args: {}

chat (Conversational responses):
  - "chat": General conversation, questions, jokes, opinions, greetings, or anything \
that is NOT a specific action above. args: {"message": "the user's full message"}

IMPORTANT: If the user is asking a question, making conversation, or saying something \
that doesn't map to a specific action above, ALWAYS use category "chat" with action \
"chat". Only use "unknown" if you truly cannot understand the input at all.

Rules:
- For URLs without http/https, prepend "https://"
- Stock symbols should be UPPERCASE
- Be smart about intent: "look up the weather in Paris" -> weather, \
"find me some good restaurants" -> google_search
- "open spotify" -> desktop.open_app, "open google.com" -> web_auto.open_url\
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
