"""Parse natural language input into structured commands using LLM APIs.

Provider chain: Gemini → Groq (70B) → Groq (8B backup) → Anthropic → keyword fallback.
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
    category: str
    action: str
    args: dict = field(default_factory=dict)
    raw_input: str = ""


# Compact system prompt — ~1200 tokens instead of ~4000
SYSTEM_PROMPT = """\
You are a command parser. Return ONLY valid JSON: {"category":"...","action":"...","args":{...}}

Categories and actions (args in parentheses):

web_auto: google_search(query), open_url(url)
desktop: open_app(app_name), close_app(app_name), type_text(text), screenshot(), click_image(target)
scrape: weather(city), news(topic), stock_price(symbol), scrape_url(url)
spotify: play(), pause(), next(), previous(), current(), play_search(query)
system: time(), date(), battery(), wifi(), ip_address(), disk_space(), \
volume_up(), volume_down(), volume_set(level), volume_mute(), volume_unmute(), volume_get(), \
brightness_up(), brightness_down(), lock_screen(), sleep(), restart(), shutdown(), \
dark_mode_on(), dark_mode_off(), toggle_dark_mode(), wifi_on(), wifi_off(), \
bluetooth_on(), bluetooth_off(), empty_trash(), show_desktop(), open_folder(path), \
clipboard_read(), clipboard_write(text), notify(message,title), \
do_not_disturb_on(), do_not_disturb_off(), set_timer(seconds,label), cancel_timer(label), \
calculate(expression), send_email(to,subject,body), run_command(command), \
read_emails(count), read_email_detail(index), read_file(path), read_calendar(days), \
read_reminders(), add_reminder(text), add_event(title,date,time), \
read_notes(), create_note(title,body), read_selected()
phone: call(number), facetime(number), facetime_audio(number), send_message(to,message), read_messages(contact)
knowledge: wikipedia(topic), define(word), translate(text,to_language), synonym(word), \
movie(title), tv_show(title), sports(sport,team), recipe(dish), joke(), fact(), quote(), \
convert(expression), country(country), timezone(city), days_until(date_str)
smart_home: lights_on(room), lights_off(room), set_brightness(level,room), \
set_thermostat(temperature), scene(name), status()
device: airplay(device), audio_output(device), find_my(device), airdrop(path), \
connect_bluetooth(device), disconnect_bluetooth(device), list_bluetooth(), screen_mirror(device)
memory: remember(key,value), recall(key), forget(key), save_contact(name,number,email), \
get_contact(name), set_preference(key,value), get_preference(key), list_memory()
network: scan(), who_is_connected(), device_count(), ping(target), speed_test(), local_ip()
routine: create(name,commands), run(name), list(), delete(name)
chat: chat(message) — for conversation, questions, greetings, anything not above

Rules:
- phone commands (call/text/message) even without details → use phone category with empty args
- "play music"→spotify.play, "play Drake"→spotify.play_search
- "open Safari"→desktop.open_app, "open google.com"→web_auto.open_url
- Timer: spoken time→seconds (5 minutes=300)
- URLs: prepend https:// if missing
- Stock symbols: UPPERCASE
- Unknown/conversation→chat.chat\
"""

# Backup Groq model — smaller, separate rate limits
GROQ_BACKUP_MODEL = "llama-3.1-8b-instant"


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


_gemini_disabled = False
_groq_disabled = False
_groq_backup_disabled = False


def _build_context_prompt(user_input: str) -> str:
    """Build the prompt with conversation context."""
    try:
        from modules.chat import get_history
        history = get_history()
        if history:
            recent = history[-4:]  # Reduced from 6 to save tokens
            context_lines = [
                f"{'User' if m['role'] == 'user' else 'Jarvis'}: {m['content'][:100]}"
                for m in recent
            ]
            context = "\n".join(context_lines)
            return f"Context:\n{context}\n\nInput: {user_input}"
    except Exception:
        pass
    return f"Input: {user_input}"


def _try_gemini(user_input: str) -> dict | None:
    global _gemini_disabled
    if not GOOGLE_API_KEY or _gemini_disabled:
        return None
    try:
        prompt = _build_context_prompt(user_input)
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
        )
        result = _parse_json(response.text)
        logger.info(f"Gemini parsed: {result}")
        return result
    except Exception as e:
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "429" in err:
            logger.warning("Gemini quota exhausted, disabling for session")
            _gemini_disabled = True
        else:
            logger.warning(f"Gemini failed: {err[:100]}")
        return None


def _try_groq(user_input: str) -> dict | None:
    global _groq_disabled
    if not GROQ_API_KEY or _groq_disabled:
        return None
    try:
        prompt = _build_context_prompt(user_input)
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0,
        )
        result = _parse_json(response.choices[0].message.content)
        logger.info(f"Groq parsed: {result}")
        return result
    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            logger.warning("Groq 70B rate limited, disabling for session")
            _groq_disabled = True
        else:
            logger.warning(f"Groq failed: {err[:120]}")
        return None


def _try_groq_backup(user_input: str) -> dict | None:
    """Try smaller Groq model — separate rate limits from 70B."""
    global _groq_backup_disabled
    if not GROQ_API_KEY or _groq_backup_disabled:
        return None
    try:
        prompt = _build_context_prompt(user_input)
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_BACKUP_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0,
        )
        result = _parse_json(response.choices[0].message.content)
        logger.info(f"Groq backup parsed: {result}")
        return result
    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            logger.warning("Groq 8B rate limited, disabling for session")
            _groq_backup_disabled = True
        else:
            logger.warning(f"Groq backup failed: {err[:120]}")
        return None


def _try_anthropic(user_input: str) -> dict | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        prompt = _build_context_prompt(user_input)
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(message.content[0].text)
        logger.info(f"Anthropic parsed: {result}")
        return result
    except Exception as e:
        logger.warning(f"Anthropic failed: {str(e)[:120]}")
        return None


# Provider chain: free first, small models as backup, paid last
_PROVIDERS = [
    ("Gemini", _try_gemini),
    ("Groq", _try_groq),
    ("Groq-backup", _try_groq_backup),
    ("Anthropic", _try_anthropic),
]


def parse_command(user_input: str) -> Command:
    """Parse user input using LLM APIs with keyword fallback."""
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

    # All LLM providers failed — use keyword-based fallback
    logger.warning("All LLMs failed, using keyword fallback")
    try:
        from core.nlp_engine import keyword_parse
        result = keyword_parse(text)
        if result:
            logger.info(f"Keyword fallback: {result}")
            return Command(
                category=result.get("category", "unknown"),
                action=result.get("action", "unknown"),
                args=result.get("args", {}),
                raw_input=text,
            )
    except Exception as e:
        logger.warning(f"Keyword fallback failed: {e}")

    # Ultimate fallback — send to chat
    return Command(category="chat", action="chat",
                   args={"message": text}, raw_input=text)


def parse_multi_command(user_input: str) -> list[Command]:
    """Parse input that may contain multiple commands."""
    try:
        from core.nlp_engine import split_commands
        parts = split_commands(user_input.strip())
    except Exception:
        parts = [user_input.strip()]

    return [parse_command(part) for part in parts]
