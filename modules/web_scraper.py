"""BeautifulSoup + requests: weather, news, stock prices, generic scraping."""

import requests
from bs4 import BeautifulSoup

from core.command_router import register
from config import REQUEST_TIMEOUT, USER_AGENT
from utils.logger import get_logger

logger = get_logger(__name__)

HEADERS = {"User-Agent": USER_AGENT}


@register("scrape", "weather")
def weather(city: str) -> str:
    """Get weather from wttr.in (free, no API key)."""
    try:
        url = f"https://wttr.in/{city}?format=3"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        return f"Could not get weather for {city}: {e}"


@register("scrape", "news")
def news(topic: str = "") -> str:
    """Get top news headlines from Google News RSS."""
    try:
        if topic:
            url = f"https://news.google.com/rss/search?q={topic}"
        else:
            url = "https://news.google.com/rss"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item", limit=5)
        if not items:
            return "No news found."
        lines = ["Here are the top headlines:"]
        for i, item in enumerate(items, 1):
            title = item.find("title").text
            lines.append(f"  {i}. {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch news: {e}"


@register("scrape", "stock_price")
def stock_price(symbol: str) -> str:
    """Get stock price by scraping Yahoo Finance."""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}/"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        price_el = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
        if price_el:
            return f"{symbol} is currently at ${price_el.text}"
        return f"Could not find price for {symbol}. The page structure may have changed."
    except Exception as e:
        return f"Could not fetch stock price for {symbol}: {e}"


@register("scrape", "scrape_url")
def scrape_url(url: str) -> str:
    """Fetch a URL and return a text summary of its content."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        if len(text) > 500:
            text = text[:500] + "..."
        return f"Content from {url}:\n{text}"
    except Exception as e:
        return f"Could not scrape {url}: {e}"
