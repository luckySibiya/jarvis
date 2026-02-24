"""Advanced NLP preprocessing engine for Jarvis.

Enhances the command parser with:
- Multi-command splitting ("turn off lights and play jazz" -> 2 commands)
- Keyword-based fallback parsing when LLM providers are unavailable
- Entity extraction (phone numbers, emails, URLs, dates, numbers)
- Confidence scoring to gauge reliability of parsed results
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Action verbs used by the multi-command splitter to decide whether text
# following "and" is a new command rather than part of the same phrase.
# ---------------------------------------------------------------------------
_ACTION_VERBS = frozenset({
    "open", "close", "play", "pause", "stop", "resume",
    "turn", "set", "search", "call", "send", "read",
    "check", "what", "how", "get", "make", "take",
    "run", "show", "create", "add", "remind", "define",
    "translate", "look", "skip", "next", "mute", "unmute",
    "lock", "sleep", "restart", "shutdown", "calculate",
    "google", "wikipedia", "screenshot", "toggle",
    "increase", "decrease", "enable", "disable", "empty",
})

# Compound connectors that *always* indicate a command boundary (order
# matters -- longer phrases first so they match before shorter ones).
_ALWAYS_SPLIT = [
    " and then ",
    " and also ",
    " after that ",
    " then ",
]

# Phrases where " and " is part of the expression, not a separator.
_PROTECTED_PHRASES = [
    "rock and roll",
    "search and rescue",
    "lock and load",
    "mac and cheese",
    "salt and pepper",
    "bread and butter",
    "peanut butter and jelly",
    "trial and error",
    "pros and cons",
    "back and forth",
    "up and down",
    "left and right",
    "black and white",
    "in and out",
    "on and off",
    "come and go",
    "rise and shine",
    "hide and seek",
    "rhythm and blues",
    "r and b",
    "bed and breakfast",
    "law and order",
    "peace and quiet",
    "safe and sound",
    "simon and garfunkel",
    "hall and oates",
    "guns and roses",
    "drag and drop",
    "copy and paste",
    "cut and paste",
    "buy and sell",
]


# =========================================================================
# 1. Multi-command splitting
# =========================================================================

def split_commands(text: str) -> list[str]:
    """Split compound commands joined by 'and', 'then', 'also', 'after that'.

    Be careful not to split inside phrases like 'rock and roll' or
    'search and rescue'.  Returns a list of individual command strings.
    """
    if not text or not text.strip():
        return []

    working = text.strip()

    # --- phase 1: protect known compound phrases -------------------------
    # Replace protected phrases with placeholders so they survive splitting.
    placeholders: dict[str, str] = {}
    lower = working.lower()
    for phrase in _PROTECTED_PHRASES:
        if phrase in lower:
            placeholder = f"\x00PH{len(placeholders)}\x00"
            placeholders[placeholder] = phrase
            # Case-insensitive replacement while preserving original casing
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            working = pattern.sub(placeholder, working, count=1)
            lower = working.lower()

    # --- phase 2: split on unambiguous connectors ------------------------
    parts = [working]
    for connector in _ALWAYS_SPLIT:
        new_parts = []
        for part in parts:
            segments = part.lower().split(connector)
            if len(segments) == 1:
                new_parts.append(part)
            else:
                # Reconstruct original-case segments by tracking offsets
                idx = 0
                for seg_lower in segments:
                    seg_len = len(seg_lower)
                    new_parts.append(part[idx:idx + seg_len])
                    idx += seg_len + len(connector)
        parts = new_parts

    # --- phase 3: split on " and " only when the right side starts -------
    #     with an action verb.
    final_parts: list[str] = []
    for part in parts:
        sub_parts = _split_on_and(part)
        final_parts.extend(sub_parts)

    # --- phase 4: restore protected phrases and clean up -----------------
    result: list[str] = []
    for part in final_parts:
        for placeholder, original in placeholders.items():
            part = part.replace(placeholder, original)
        cleaned = part.strip()
        if cleaned:
            result.append(cleaned)

    return result if result else [text.strip()]


def _split_on_and(text: str) -> list[str]:
    """Split *text* on \" and \" only when the word after 'and' is an action verb."""
    parts: list[str] = []
    remaining = text

    while True:
        idx = remaining.lower().find(" and ")
        if idx == -1:
            parts.append(remaining)
            break

        after_and = remaining[idx + 5:].lstrip()
        first_word = after_and.split()[0].lower() if after_and.split() else ""

        if first_word in _ACTION_VERBS:
            parts.append(remaining[:idx])
            remaining = remaining[idx + 5:]
        else:
            # Not a split point -- advance past this " and " and keep looking.
            # We need to carry the prefix forward intact.
            next_search_start = idx + 5
            next_idx = remaining.lower().find(" and ", next_search_start)
            if next_idx == -1:
                parts.append(remaining)
                break
            # Check *that* occurrence instead.  Easiest via a small trick:
            # keep the left side and recurse on the rest.
            # But to avoid deep recursion, just continue the loop.
            # We advance by committing everything up to (and including) the
            # current " and " as non-splittable prefix.
            prefix = remaining[:idx + 5]
            tail_parts = _split_on_and(remaining[idx + 5:])
            if len(tail_parts) > 1:
                # The first tail element should be glued back to our prefix
                parts.append(prefix + tail_parts[0])
                parts.extend(tail_parts[1:])
            else:
                parts.append(remaining)
            break

    return parts


# =========================================================================
# 2. Keyword-based fallback parser
# =========================================================================

def keyword_parse(text: str) -> dict | None:
    """Fast keyword-based command parser -- used as fallback when LLM fails.

    Returns ``{"category": ..., "action": ..., "args": {...}}`` or ``None``
    if the text doesn't match any known pattern.
    """
    if not text or not text.strip():
        return None

    t = text.strip()
    low = t.lower()

    # ------------------------------------------------------------------
    # Routines / greetings
    # ------------------------------------------------------------------
    if low in ("good morning", "good night", "goodmorning", "goodnight"):
        return _r("routine", "run", routine=low.replace(" ", "_"))

    # ------------------------------------------------------------------
    # Desktop: open / close / screenshot
    # ------------------------------------------------------------------
    m = re.match(r"^open\s+(.+)", low)
    if m:
        target = m.group(1).strip()
        # If it looks like a URL, route to web_auto
        if re.match(r"^(https?://|www\.|\S+\.\w{2,6}(/|$))", target):
            url = target if target.startswith("http") else f"https://{target}"
            return _r("web_auto", "open_url", url=url)
        return _r("desktop", "open_app", app_name=_titlecase(target))

    m = re.match(r"^(close|quit|exit)\s+(.+)", low)
    if m:
        return _r("desktop", "close_app", app_name=_titlecase(m.group(2).strip()))

    if low in ("screenshot", "take a screenshot", "take screenshot"):
        return _r("desktop", "screenshot")

    # ------------------------------------------------------------------
    # Spotify
    # ------------------------------------------------------------------
    if re.match(r"^play\s+(music|spotify|some music)$", low):
        return _r("spotify", "play")

    m = re.match(r"^play\s+(.+)", low)
    if m:
        return _r("spotify", "play_search", query=m.group(1).strip())

    if low in ("pause", "pause music", "pause spotify", "stop music"):
        return _r("spotify", "pause")

    if low in ("resume", "resume music", "resume spotify", "unpause"):
        return _r("spotify", "play")

    if low in ("next song", "skip", "next track", "skip song", "next"):
        return _r("spotify", "next")

    if low in ("previous song", "previous track", "previous", "go back"):
        return _r("spotify", "previous")

    if low in ("what's playing", "current song", "what song is this",
               "what is playing", "now playing"):
        return _r("spotify", "current")

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------
    if low in ("volume up", "louder", "increase volume", "turn up volume",
               "turn volume up", "raise volume"):
        return _r("system", "volume_up")

    if low in ("volume down", "quieter", "decrease volume", "turn down volume",
               "turn volume down", "lower volume"):
        return _r("system", "volume_down")

    if low in ("mute", "mute volume", "silence", "volume mute"):
        return _r("system", "volume_mute")

    if low in ("unmute", "unmute volume", "volume unmute"):
        return _r("system", "volume_unmute")

    m = re.match(r"^set\s+volume\s+(?:to\s+)?(\d+)", low)
    if m:
        return _r("system", "volume_set", level=int(m.group(1)))

    m = re.match(r"^volume\s+(\d+)", low)
    if m:
        return _r("system", "volume_set", level=int(m.group(1)))

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------
    if low in ("brightness up", "increase brightness", "brighter",
               "turn up brightness", "turn brightness up"):
        return _r("system", "brightness_up")

    if low in ("brightness down", "decrease brightness", "dimmer",
               "turn down brightness", "turn brightness down"):
        return _r("system", "brightness_down")

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------
    if re.match(r"^(what('s| is) the )?time$", low) or low == "what time is it":
        return _r("system", "time")

    if re.match(r"^(what('s| is) the )?date$", low) or low == "what's today's date":
        return _r("system", "date")

    if low in ("battery", "battery level", "how much battery",
               "battery status", "check battery"):
        return _r("system", "battery")

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------
    m = re.match(r"^(?:what's the )?weather\s+(?:in|for|at)\s+(.+)", low)
    if m:
        return _r("scrape", "weather", city=_titlecase(m.group(1).strip()))

    if low in ("weather", "what's the weather", "how's the weather"):
        return _r("scrape", "weather", city="")

    # ------------------------------------------------------------------
    # Web search
    # ------------------------------------------------------------------
    m = re.match(r"^(?:search\s+(?:for\s+)?|google\s+)(.+)", low)
    if m:
        return _r("web_auto", "google_search", query=m.group(1).strip())

    # ------------------------------------------------------------------
    # Phone: call / message
    # ------------------------------------------------------------------
    m = re.match(r"^(?:call|phone|ring)\s+(.+)", low)
    if m:
        target = m.group(1).strip()
        return _r("phone", "call", number=target)

    if low in ("call", "make a call", "call someone"):
        return _r("phone", "call", number="")

    m = re.match(
        r"^(?:send\s+(?:a\s+)?(?:message|text|sms)\s+to|text)\s+(.+?)(?:\s+(?:saying|that|message)\s+(.+))?$",
        low,
    )
    if m:
        return _r("phone", "send_message",
                   to=m.group(1).strip(),
                   message=(m.group(2) or "").strip())

    if low in ("send a message", "send a text", "text someone",
               "send message", "send text"):
        return _r("phone", "send_message", to="", message="")

    # ------------------------------------------------------------------
    # Reading: emails, messages
    # ------------------------------------------------------------------
    if low in ("read my emails", "check my emails", "read emails",
               "check emails", "check my email", "read my email"):
        return _r("system", "read_emails", count=5)

    if low in ("read my messages", "check my messages", "read messages",
               "check messages"):
        return _r("phone", "read_messages", contact="")

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------
    m = re.match(
        r"^set\s+(?:a\s+)?timer\s+(?:for\s+)?(.+)", low
    )
    if m:
        seconds = _parse_duration(m.group(1))
        return _r("system", "set_timer", seconds=seconds,
                   label=m.group(1).strip())

    # ------------------------------------------------------------------
    # Knowledge: define, translate, wikipedia
    # ------------------------------------------------------------------
    m = re.match(r"^define\s+(.+)", low)
    if m:
        return _r("knowledge", "define", word=m.group(1).strip())

    m = re.match(r"^translate\s+(.+?)\s+(?:to|into)\s+(.+)", low)
    if m:
        return _r("knowledge", "translate",
                   text=m.group(1).strip(),
                   to_language=m.group(2).strip())

    m = re.match(r"^(?:wikipedia|wiki|look\s+up)\s+(.+)", low)
    if m:
        return _r("knowledge", "wikipedia", topic=m.group(1).strip())

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------
    m = re.match(r"^remind\s+me\s+(?:to\s+)?(.+)", low)
    if m:
        return _r("system", "add_reminder", text=m.group(1).strip())

    # ------------------------------------------------------------------
    # Calculator
    # ------------------------------------------------------------------
    m = re.match(r"^(?:calculate|calc)\s+(.+)", low)
    if m:
        return _r("system", "calculate", expression=m.group(1).strip())

    # "what's N times/plus/minus/divided by N"
    m = re.match(
        r"^what(?:'s| is)\s+(\d+[\d.]*)\s+(times|plus|minus|divided\s+by|over|x)\s+(\d+[\d.]*)",
        low,
    )
    if m:
        ops = {"times": "*", "x": "*", "plus": "+", "minus": "-",
               "divided by": "/", "over": "/"}
        op = ops.get(m.group(2), m.group(2))
        return _r("system", "calculate",
                   expression=f"{m.group(1)} {op} {m.group(3)}")

    # ------------------------------------------------------------------
    # System controls
    # ------------------------------------------------------------------
    if low in ("lock", "lock screen", "lock my computer", "lock the screen",
               "lock my mac"):
        return _r("system", "lock_screen")

    if low in ("sleep", "go to sleep", "put the computer to sleep"):
        return _r("system", "sleep")

    if low in ("dark mode on", "enable dark mode", "turn on dark mode"):
        return _r("system", "dark_mode_on")

    if low in ("dark mode off", "disable dark mode", "turn off dark mode"):
        return _r("system", "dark_mode_off")

    # ------------------------------------------------------------------
    # Smart home
    # ------------------------------------------------------------------
    m = re.match(r"^turn\s+(on|off)\s+(?:the\s+)?lights?$", low)
    if m:
        action = "lights_on" if m.group(1) == "on" else "lights_off"
        return _r("smart_home", action)

    if re.match(r"^lights?\s+(on|off)$", low):
        action = "lights_on" if "on" in low else "lights_off"
        return _r("smart_home", action)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    m = re.match(r"^remember\s+(?:that\s+)?(.+)", low)
    if m:
        return _r("memory", "remember", text=m.group(1).strip())

    # ------------------------------------------------------------------
    # Catch-all: questions or general chat
    # ------------------------------------------------------------------
    if "?" in t or _looks_like_question(low):
        return _r("chat", "chat", message=t)

    return None


# --- helpers for keyword_parse -------------------------------------------

def _r(category: str, action: str, **kwargs) -> dict:
    """Build a standard result dict."""
    return {"category": category, "action": action, "args": kwargs}


def _titlecase(s: str) -> str:
    """Title-case a string while preserving acronyms that are all-caps."""
    return " ".join(
        w if w.isupper() and len(w) > 1 else w.capitalize()
        for w in s.split()
    )


def _looks_like_question(text: str) -> bool:
    """Return True if the text starts with a typical question word."""
    question_starters = (
        "who ", "what ", "where ", "when ", "why ", "how ",
        "is ", "are ", "can ", "could ", "would ", "should ",
        "do ", "does ", "did ", "will ", "has ", "have ",
        "tell me", "explain",
    )
    return any(text.startswith(q) for q in question_starters)


def _parse_duration(text: str) -> int:
    """Convert a spoken duration like '5 minutes' or '1 hour 30 minutes' to seconds."""
    text = text.lower().strip()
    total = 0

    hours = re.search(r"(\d+)\s*(?:hour|hr)s?", text)
    if hours:
        total += int(hours.group(1)) * 3600

    minutes = re.search(r"(\d+)\s*(?:minute|min)s?", text)
    if minutes:
        total += int(minutes.group(1)) * 60

    seconds = re.search(r"(\d+)\s*(?:second|sec)s?", text)
    if seconds:
        total += int(seconds.group(1))

    # Plain number with no unit -- assume minutes
    if total == 0:
        m = re.search(r"(\d+)", text)
        if m:
            total = int(m.group(1)) * 60

    return total if total > 0 else 60  # default 60 seconds


# =========================================================================
# 3. Entity extraction
# =========================================================================

def extract_entities(text: str) -> dict:
    """Extract entities from text: phone numbers, emails, URLs, numbers, times.

    Returns a dict with keys: ``phones``, ``emails``, ``urls``, ``numbers``,
    ``times``.  Each value is a list of matched strings.
    """
    entities: dict[str, list[str]] = {
        "phones": [],
        "emails": [],
        "urls": [],
        "numbers": [],
        "times": [],
    }

    if not text:
        return entities

    # --- Phone numbers ---------------------------------------------------
    # International: +1-234-567-8901  |  Local: (012) 345-6789  |  Plain: 0712345678
    phone_patterns = [
        r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
        r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        r"\b0\d{9,10}\b",
    ]
    for pat in phone_patterns:
        for match in re.finditer(pat, text):
            value = match.group().strip()
            if value not in entities["phones"] and len(value) >= 7:
                entities["phones"].append(value)

    # --- Email addresses -------------------------------------------------
    for match in re.finditer(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text
    ):
        entities["emails"].append(match.group())

    # --- URLs ------------------------------------------------------------
    for match in re.finditer(
        r"https?://[^\s,;\"'<>]+|www\.[^\s,;\"'<>]+", text
    ):
        entities["urls"].append(match.group())

    # --- Numbers (standalone digits / decimals) --------------------------
    # Exclude numbers that are part of phone numbers or emails.
    for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        num = match.group()
        start, end = match.span()
        # Skip if this number is embedded inside a phone or email already captured
        context = text[max(0, start - 3):min(len(text), end + 3)]
        if "@" in context or "+" in context:
            continue
        # Avoid very long digit sequences that are likely phone numbers
        if len(num) >= 7:
            continue
        if num not in entities["numbers"]:
            entities["numbers"].append(num)

    # --- Time expressions ------------------------------------------------
    time_patterns = [
        # Relative durations: "5 minutes", "1 hour", "30 seconds"
        r"\b\d+\s*(?:second|sec|minute|min|hour|hr)s?\b",
        # Clock times: "3pm", "3:30 PM", "15:00"
        r"\b\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?\b",
        r"\b\d{1,2}\s*(?:am|pm|AM|PM)\b",
        # Relative day references
        r"\b(?:today|tomorrow|tonight|yesterday|this morning|this afternoon|"
        r"this evening|next week|next month)\b",
    ]
    for pat in time_patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            value = match.group().strip()
            if value not in entities["times"]:
                entities["times"].append(value)

    return entities


# =========================================================================
# 4. Confidence scoring
# =========================================================================

def estimate_confidence(text: str, parsed_result: dict) -> float:
    """Estimate how confident we are in the parsed result (0.0 to 1.0).

    Higher confidence when keywords match the parsed category/action.
    If ``keyword_parse`` and the LLM-parsed result agree on category and
    action, confidence is high (0.9+).  If they disagree, confidence is
    lower (0.5-0.7).

    Args:
        text: The original user input.
        parsed_result: A dict with at least ``category`` and ``action`` keys
                       (as returned by the LLM parser or keyword_parse).

    Returns:
        A float between 0.0 and 1.0.
    """
    if not parsed_result or not text:
        return 0.0

    target_category = parsed_result.get("category", "")
    target_action = parsed_result.get("action", "")

    # Run the keyword parser for comparison
    keyword_result = keyword_parse(text)

    # --- Case 1: keyword parser also matched ----------------------------
    if keyword_result is not None:
        kw_cat = keyword_result["category"]
        kw_act = keyword_result["action"]

        if kw_cat == target_category and kw_act == target_action:
            # Full agreement -- very confident
            return 0.95

        if kw_cat == target_category:
            # Same category, different action -- moderately confident
            return 0.75

        # Category mismatch -- the LLM and keyword parser disagree
        return 0.50

    # --- Case 2: keyword parser returned None ---------------------------
    # The keyword parser didn't recognise the command.  The LLM parse is
    # our only signal.

    # If the LLM chose "chat", that's a reasonable default
    if target_category == "chat":
        return 0.70

    # Otherwise, moderate confidence since keyword parser couldn't confirm
    # but the LLM did produce something.
    confidence = 0.60

    # Boost slightly if the text contains words related to the category
    _category_keywords: dict[str, list[str]] = {
        "spotify": ["play", "music", "song", "track", "spotify", "pause",
                     "skip", "next", "previous", "album", "artist"],
        "system": ["volume", "brightness", "battery", "time", "date", "timer",
                    "lock", "sleep", "dark mode", "wifi", "bluetooth",
                    "clipboard", "trash", "restart", "shutdown", "calculate",
                    "email", "calendar", "reminder", "note"],
        "desktop": ["open", "close", "quit", "screenshot", "type", "click"],
        "web_auto": ["search", "google", "url", "website", "browse"],
        "scrape": ["weather", "news", "stock", "scrape"],
        "phone": ["call", "text", "message", "facetime", "ring", "phone"],
        "knowledge": ["define", "translate", "wikipedia", "synonym", "look up"],
        "smart_home": ["lights", "light", "turn on", "turn off"],
        "memory": ["remember"],
        "routine": ["morning", "night", "routine"],
    }

    low = text.lower()
    related = _category_keywords.get(target_category, [])
    if any(kw in low for kw in related):
        confidence += 0.15

    return min(confidence, 1.0)
