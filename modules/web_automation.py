"""Selenium-based web automation: search Google, open URLs."""

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


def _is_alive(driver) -> bool:
    try:
        _ = driver.title
        return True
    except Exception:
        return False


def get_driver():
    """Lazy-initialize the Selenium Chrome driver."""
    global _driver
    if _driver is None or not _is_alive(_driver):
        options = Options()
        if HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=options)
        _driver.implicitly_wait(IMPLICIT_WAIT)
    return _driver


@register("web_auto", "google_search")
def google_search(query: str) -> str:
    """Search Google and return top results."""
    try:
        driver = get_driver()
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
        logger.error(f"Google search error: {e}")
        return f"Search failed: {e}"


@register("web_auto", "open_url")
def open_url(url: str) -> str:
    """Open a URL in the Selenium browser."""
    try:
        driver = get_driver()
        driver.get(url)
        return f"Opened {url}. Page title: {driver.title}"
    except Exception as e:
        logger.error(f"Open URL error: {e}")
        return f"Could not open {url}: {e}"
