"""PyAutoGUI-based desktop automation: open apps, click, type, screenshot."""

import os
import subprocess
import time
from datetime import datetime

import pyautogui

from core.command_router import register
from config import PYAUTOGUI_PAUSE, PYAUTOGUI_FAILSAFE
from utils.logger import get_logger

logger = get_logger(__name__)

pyautogui.PAUSE = PYAUTOGUI_PAUSE
pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE


@register("desktop", "open_app")
def open_app(app_name: str) -> str:
    """Open a macOS application by name."""
    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            time.sleep(1)
            return f"Opened {app_name}."

        # App not found — try common aliases
        alias = APP_ALIASES.get(app_name.lower())
        if alias:
            retry = subprocess.run(
                ["open", "-a", alias],
                capture_output=True, text=True, timeout=5,
            )
            if retry.returncode == 0:
                time.sleep(1)
                return f"Opened {alias}."

        return f"Could not find application '{app_name}'. Make sure it's installed."
    except Exception as e:
        return f"Could not open {app_name}: {e}"


# Same aliases used by both open and close
APP_ALIASES = {
    "teams": "Microsoft Teams",
    "vscode": "Visual Studio Code",
    "code": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "photoshop": "Adobe Photoshop",
    "terminal": "Terminal",
    "finder": "Finder",
    "music": "Music",
    "messages": "Messages",
}


def _resolve_app_name(app_name: str) -> str:
    """Resolve a short app name to its full macOS name."""
    return APP_ALIASES.get(app_name.lower(), app_name)


@register("desktop", "close_app")
def close_app(app_name: str) -> str:
    """Close/quit a macOS application by name."""
    full_name = _resolve_app_name(app_name)
    try:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "{full_name}" to quit'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f"Closed {full_name}."
        return f"Could not close {full_name}. It may not be running."
    except Exception as e:
        return f"Could not close {full_name}: {e}"


@register("desktop", "type_text")
def type_text(text: str) -> str:
    """Type text at the current cursor position."""
    pyautogui.typewrite(text, interval=0.03)
    return f"Typed: {text}"


@register("desktop", "screenshot")
def screenshot() -> str:
    """Take a screenshot and save it."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
    img = pyautogui.screenshot()
    img.save(path)
    return f"Screenshot saved to {path}"


@register("desktop", "click_image")
def click_image(target: str) -> str:
    """Click at screen coordinates. Use 'click x, y' format."""
    if "," in target:
        parts = target.split(",")
        try:
            x, y = int(parts[0].strip()), int(parts[1].strip())
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})."
        except ValueError:
            return "Invalid coordinates. Use format: click 500, 300"
    return (
        f"I can't locate '{target}' on screen yet. "
        f"Try: 'click 500, 300' with coordinates."
    )
