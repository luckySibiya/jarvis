"""Web automation: search Google, open URLs.

Uses Selenium (Chrome) when available. Falls back to native browser + requests
for search if ChromeDriver fails.
"""

import subprocess
import webbrowser

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from core.command_router import register
from config import HEADLESS, IMPLICIT_WAIT
from utils.logger import get_logger

logger = get_logger(__name__)

_driver = None
_selenium_failed = False


def _is_alive(driver) -> bool:
    try:
        _ = driver.title
        return True
    except Exception:
        return False


def get_driver():
    """Lazy-initialize the Selenium Chrome driver."""
    global _driver, _selenium_failed
    if _selenium_failed:
        return None
    if _driver is not None and _is_alive(_driver):
        return _driver
    try:
        options = Options()
        if HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--remote-debugging-port=0")
        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=options)
        _driver.implicitly_wait(IMPLICIT_WAIT)
        return _driver
    except Exception as e:
        logger.warning(f"Selenium init failed: {e}. Falling back to native browser.")
        _selenium_failed = True
        return None


def _search_with_scraping(query: str) -> str:
    """Fallback: scrape DuckDuckGo lite for results (no JavaScript needed)."""
    import requests
    from bs4 import BeautifulSoup
    from config import USER_AGENT, REQUEST_TIMEOUT

    try:
        url = "https://lite.duckduckgo.com/lite/"
        resp = requests.post(
            url,
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        # DuckDuckGo lite results are in <a class="result-link"> or in table rows
        links = soup.select("a.result-link")
        if not links:
            # Try alternative selectors
            links = soup.select("td a[href^='http']")

        results = []
        seen = set()
        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if title and href and title not in seen and "duckduckgo" not in href:
                seen.add(title)
                results.append(title)
                if len(results) >= 5:
                    break

        if results:
            lines = [f"Top results for '{query}':"]
            for i, r in enumerate(results, 1):
                lines.append(f"  {i}. {r}")
            return "\n".join(lines)

        # If scraping didn't get results, just open the search in browser
        return None
    except Exception as e:
        logger.warning(f"Scrape search failed: {e}")
        return None


@register("web_auto", "google_search")
def google_search(query: str) -> str:
    """Search the web and return top results."""
    # Try Selenium first
    driver = get_driver()
    if driver:
        try:
            driver.get("https://www.google.com")
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            results = driver.find_elements(By.CSS_SELECTOR, "div.g h3")[:5]
            if not results:
                return f"Searched for '{query}' but found no results."
            lines = [f"Top results for '{query}':"]
            for i, r in enumerate(results, 1):
                lines.append(f"  {i}. {r.text}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Selenium search failed: {e}")

    # Fallback: try scraping DuckDuckGo
    result = _search_with_scraping(query)
    if result:
        return result

    # Last resort: open in the default browser
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    return f"Opened a Google search for '{query}' in your browser, sir."


@register("web_auto", "open_url")
def open_url(url: str) -> str:
    """Open a URL in the browser."""
    # Try Selenium first
    driver = get_driver()
    if driver:
        try:
            driver.get(url)
            return f"Opened {url}. Page title: {driver.title}"
        except Exception as e:
            logger.warning(f"Selenium open failed: {e}")

    # Fallback: open in default browser
    webbrowser.open(url)
    return f"Opened {url} in your browser, sir."
