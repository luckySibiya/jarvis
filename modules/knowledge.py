"""Knowledge module — Wikipedia, dictionary, translations, and instant web answers.

Gives Jarvis access to real-world knowledge beyond what the LLM knows.
"""

import requests
from bs4 import BeautifulSoup

from core.command_router import register
from config import USER_AGENT, REQUEST_TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)

_HEADERS = {"User-Agent": USER_AGENT}


@register("knowledge", "wikipedia")
def wikipedia_summary(topic: str) -> str:
    """Get a Wikipedia summary for a topic."""
    try:
        resp = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + topic.replace(" ", "_"),
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            return f"I couldn't find a Wikipedia article about '{topic}', sir."
        data = resp.json()
        extract = data.get("extract", "")
        if not extract:
            return f"No summary available for '{topic}'."
        # Truncate for speech
        if len(extract) > 400:
            # Cut at sentence boundary
            cut = extract[:400].rsplit(".", 1)[0] + "."
            extract = cut
        return f"According to Wikipedia: {extract}"
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return f"Could not look up '{topic}': {e}"


@register("knowledge", "define")
def define_word(word: str) -> str:
    """Get the dictionary definition of a word."""
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.strip()}",
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            return f"I couldn't find a definition for '{word}', sir."
        data = resp.json()
        if not data or not isinstance(data, list):
            return f"No definition found for '{word}'."

        entry = data[0]
        results = []
        for meaning in entry.get("meanings", [])[:3]:
            part = meaning.get("partOfSpeech", "")
            definitions = meaning.get("definitions", [])
            if definitions:
                defn = definitions[0].get("definition", "")
                results.append(f"{part}: {defn}")

        if not results:
            return f"No definitions found for '{word}'."

        formatted = "; ".join(results)
        return f"'{word}' — {formatted}"
    except Exception as e:
        logger.error(f"Definition error: {e}")
        return f"Could not look up the definition: {e}"


@register("knowledge", "translate")
def translate_text(text: str, to_language: str = "en") -> str:
    """Translate text using MyMemory translation API (free, no key needed)."""
    # Map common language names to codes
    lang_map = {
        "spanish": "es", "french": "fr", "german": "de", "italian": "it",
        "portuguese": "pt", "dutch": "nl", "russian": "ru", "japanese": "ja",
        "chinese": "zh", "korean": "ko", "arabic": "ar", "hindi": "hi",
        "turkish": "tr", "swedish": "sv", "polish": "pl", "zulu": "zu",
        "afrikaans": "af", "sotho": "st", "xhosa": "xh", "tswana": "tn",
        "english": "en",
    }
    lang_code = lang_map.get(to_language.lower(), to_language.lower())

    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"en|{lang_code}"},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if not translated:
            return f"Could not translate to {to_language}."
        return f"Translation to {to_language}: {translated}"
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return f"Could not translate: {e}"


@register("knowledge", "instant_answer")
def instant_answer(query: str) -> str:
    """Get an instant answer from DuckDuckGo (facts, quick answers)."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()

        # Try AbstractText first (main answer)
        answer = data.get("AbstractText", "")
        if answer:
            if len(answer) > 400:
                answer = answer[:400].rsplit(".", 1)[0] + "."
            source = data.get("AbstractSource", "")
            return f"{answer}" + (f" (Source: {source})" if source else "")

        # Try Answer (computation, facts)
        answer = data.get("Answer", "")
        if answer:
            return str(answer)

        # Try Related Topics
        related = data.get("RelatedTopics", [])
        if related and isinstance(related[0], dict):
            text = related[0].get("Text", "")
            if text:
                if len(text) > 300:
                    text = text[:300].rsplit(".", 1)[0] + "."
                return text

        return ""  # No instant answer available
    except Exception as e:
        logger.error(f"Instant answer error: {e}")
        return ""


@register("knowledge", "synonym")
def get_synonyms(word: str) -> str:
    """Get synonyms for a word."""
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.strip()}",
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return f"Could not find synonyms for '{word}'."
        data = resp.json()
        synonyms = set()
        for entry in data:
            for meaning in entry.get("meanings", []):
                for defn in meaning.get("definitions", []):
                    for syn in defn.get("synonyms", []):
                        synonyms.add(syn)
                for syn in meaning.get("synonyms", []):
                    synonyms.add(syn)

        if not synonyms:
            return f"No synonyms found for '{word}', sir."

        syn_list = list(synonyms)[:8]
        return f"Synonyms for '{word}': {', '.join(syn_list)}"
    except Exception as e:
        logger.error(f"Synonym error: {e}")
        return f"Could not find synonyms: {e}"
