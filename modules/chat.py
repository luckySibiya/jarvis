"""Conversational chat — Jarvis answers general questions using LLM.

Maintains conversation history so Jarvis remembers context within a session.
Enhanced with knowledge enrichment: for factual questions, Jarvis fetches
real data (Wikipedia, definitions, instant answers) and weaves it into responses.
"""

from collections import deque

from google import genai
from groq import Groq
import anthropic

from core.command_router import register
from config import (
    GOOGLE_API_KEY, GEMINI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
)
from utils.logger import get_logger

logger = get_logger(__name__)

JARVIS_PERSONA = """\
You are Jarvis, a highly intelligent personal AI assistant inspired by the Jarvis \
from Iron Man. You speak with a British accent and are polite, witty, and concise. \
You address the user as "sir" occasionally. Keep responses brief (2-3 sentences max) \
since they will be spoken aloud. Be helpful, knowledgeable, and confident.

You have extensive capabilities. When relevant, you can suggest actions you can perform:
- Phone: make calls, FaceTime, send/read iMessages
- Email: send and read emails
- Calendar: read/add events
- Reminders: read/add reminders
- Notes: read/create notes
- Spotify: play/pause/skip/search music
- System: volume, brightness, dark mode, Wi-Fi, Bluetooth, lock, sleep, restart, shutdown
- Desktop: open/close apps, type text, screenshots, click coordinates
- Web: Google search, open URLs, weather, news, stocks, scrape pages
- Knowledge: Wikipedia, definitions, translations, synonyms
- Timers, math calculations, clipboard, notifications, shell commands
- Read files and selected text aloud

When given factual context below, use it to give an informed answer. \
If the context is empty or irrelevant, answer from your own knowledge.

IMPORTANT: Never make up actions you didn't perform. If the user asks you to do \
something (call, send message, etc.), tell them to give you the command directly \
rather than pretending you did it. For example, don't say "I'm dialing now" if \
no call was actually made — instead say "I can make that call for you. Just say \
'call' followed by the name or number."\
"""

# Conversation history — keeps last 20 messages for context
_history: deque[dict] = deque(maxlen=20)


def _get_messages(new_message: str, context: str = "") -> list[dict]:
    """Build the full message list with system prompt + history + new message."""
    system = JARVIS_PERSONA
    if context:
        system += f"\n\nRelevant factual context for this query:\n{context}"

    messages = [{"role": "system", "content": system}]
    messages.extend(_history)
    messages.append({"role": "user", "content": new_message})
    return messages


def _save_exchange(user_msg: str, assistant_msg: str):
    """Save the user/assistant exchange to history."""
    _history.append({"role": "user", "content": user_msg})
    _history.append({"role": "assistant", "content": assistant_msg})


def get_history() -> list[dict]:
    """Return conversation history for use by other modules (e.g. parser)."""
    return list(_history)


def _enrich_with_knowledge(message: str) -> str:
    """Try to fetch relevant factual data to give Jarvis real knowledge."""
    msg_lower = message.lower()

    # Skip enrichment for simple greetings, opinions, jokes
    skip_patterns = [
        "hello", "hi ", "hey", "how are you", "tell me a joke",
        "thank", "goodbye", "good morning", "good night",
        "what can you do", "who are you", "your name",
    ]
    if any(p in msg_lower for p in skip_patterns):
        return ""

    context_parts = []

    try:
        # Try instant answer for factual questions
        from modules.knowledge import instant_answer
        answer = instant_answer(message)
        if answer:
            context_parts.append(answer)
    except Exception:
        pass

    # For "what is X" / "who is X" / "tell me about X" — try Wikipedia
    knowledge_triggers = [
        "what is", "what are", "who is", "who was", "who were",
        "tell me about", "explain", "describe", "history of",
        "how does", "how do", "where is", "when was", "when did",
    ]
    if any(trigger in msg_lower for trigger in knowledge_triggers):
        try:
            from modules.knowledge import wikipedia_summary
            # Extract the topic — rough heuristic
            topic = message
            for trigger in knowledge_triggers:
                if trigger in msg_lower:
                    idx = msg_lower.index(trigger) + len(trigger)
                    topic = message[idx:].strip().rstrip("?.,!")
                    break
            if topic and len(topic) > 2:
                wiki = wikipedia_summary(topic)
                if "couldn't find" not in wiki and "No summary" not in wiki:
                    context_parts.append(wiki)
        except Exception:
            pass

    # For "define X" / "meaning of X"
    if any(w in msg_lower for w in ["define ", "meaning of ", "definition of "]):
        try:
            from modules.knowledge import define_word
            word = message
            for w in ["define ", "meaning of ", "definition of "]:
                if w in msg_lower:
                    word = message[msg_lower.index(w) + len(w):].strip().rstrip("?.,!")
                    break
            if word:
                defn = define_word(word)
                if "couldn't find" not in defn:
                    context_parts.append(defn)
        except Exception:
            pass

    return "\n".join(context_parts)


_gemini_chat_disabled = False


def _chat_gemini(messages: list[dict]) -> str | None:
    global _gemini_chat_disabled
    if not GOOGLE_API_KEY or _gemini_chat_disabled:
        return None
    try:
        # Gemini uses a flat string, so we join the conversation
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        convo = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Jarvis'}: {m['content']}"
            for m in messages if m["role"] != "system"
        )
        prompt = f"{system}\n\n{convo}\nJarvis:"

        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        err = str(e)
        if "RESOURCE_EXHAUSTED" in err or "429" in err:
            _gemini_chat_disabled = True
        else:
            logger.warning(f"Gemini chat failed: {err[:100]}")
        return None


def _chat_groq(messages: list[dict]) -> str | None:
    if not GROQ_API_KEY:
        return None
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq chat failed: {e}")
        return None


def _chat_anthropic(messages: list[dict]) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        # Anthropic uses system separately from messages
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user_messages = [m for m in messages if m["role"] != "system"]
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=system,
            messages=user_messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Anthropic chat failed: {e}")
        return None


_CHAT_PROVIDERS = [
    ("Gemini", _chat_gemini),
    ("Groq", _chat_groq),
    ("Anthropic", _chat_anthropic),
]


@register("chat", "chat")
def chat(message: str) -> str:
    """Have a conversation with Jarvis. Maintains session memory.

    Enriches responses with real-world knowledge from Wikipedia, dictionaries,
    and instant answers when the question is factual.
    """
    # Fetch real knowledge to ground the response
    context = _enrich_with_knowledge(message)

    messages = _get_messages(message, context)

    for name, provider in _CHAT_PROVIDERS:
        result = provider(messages)
        if result:
            logger.info(f"Chat response from {name}")
            _save_exchange(message, result)
            return result

    return "I'm having trouble connecting to my brain right now. Try again in a moment, sir."
