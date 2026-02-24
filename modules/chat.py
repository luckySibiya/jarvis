"""Conversational chat — Jarvis answers general questions using LLM.

Maintains conversation history so Jarvis remembers context within a session.
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
since they will be spoken aloud. Be helpful, knowledgeable, and confident.\
"""

# Conversation history — keeps last 20 messages for context
_history: deque[dict] = deque(maxlen=20)


def _get_messages(new_message: str) -> list[dict]:
    """Build the full message list with system prompt + history + new message."""
    messages = [{"role": "system", "content": JARVIS_PERSONA}]
    messages.extend(_history)
    messages.append({"role": "user", "content": new_message})
    return messages


def _save_exchange(user_msg: str, assistant_msg: str):
    """Save the user/assistant exchange to history."""
    _history.append({"role": "user", "content": user_msg})
    _history.append({"role": "assistant", "content": assistant_msg})


_gemini_chat_disabled = False


def _chat_gemini(messages: list[dict]) -> str | None:
    global _gemini_chat_disabled
    if not GOOGLE_API_KEY or _gemini_chat_disabled:
        return None
    try:
        # Gemini uses a flat string, so we join the conversation
        convo = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Jarvis'}: {m['content']}"
            for m in messages if m["role"] != "system"
        )
        prompt = f"{JARVIS_PERSONA}\n\n{convo}\nJarvis:"

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
            max_tokens=256,
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
        user_messages = [m for m in messages if m["role"] != "system"]
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            system=JARVIS_PERSONA,
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
    """Have a conversation with Jarvis. Maintains session memory."""
    messages = _get_messages(message)

    for name, provider in _CHAT_PROVIDERS:
        result = provider(messages)
        if result:
            logger.info(f"Chat response from {name}")
            _save_exchange(message, result)
            return result

    return "I'm having trouble connecting to my brain right now. Try again in a moment, sir."
