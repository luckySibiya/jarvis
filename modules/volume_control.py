"""macOS volume control using osascript."""

import subprocess

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)


def _run_osascript(script: str) -> str:
    """Run an AppleScript command and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip()


def _get_volume() -> int:
    """Get current volume level (0-100)."""
    return int(_run_osascript("output volume of (get volume settings)"))


@register("system", "volume_up")
def volume_up() -> str:
    """Increase volume by 15%."""
    current = _get_volume()
    new_vol = min(100, current + 15)
    _run_osascript(f"set volume output volume {new_vol}")
    return f"Volume up to {new_vol}%."


@register("system", "volume_down")
def volume_down() -> str:
    """Decrease volume by 15%."""
    current = _get_volume()
    new_vol = max(0, current - 15)
    _run_osascript(f"set volume output volume {new_vol}")
    return f"Volume down to {new_vol}%."


@register("system", "volume_set")
def volume_set(level: int) -> str:
    """Set volume to a specific level (0-100)."""
    level = max(0, min(100, int(level)))
    _run_osascript(f"set volume output volume {level}")
    return f"Volume set to {level}%."


@register("system", "volume_mute")
def volume_mute() -> str:
    """Mute the system volume."""
    _run_osascript("set volume output muted true")
    return "Volume muted."


@register("system", "volume_unmute")
def volume_unmute() -> str:
    """Unmute the system volume."""
    _run_osascript("set volume output muted false")
    return "Volume unmuted."


@register("system", "volume_get")
def volume_get() -> str:
    """Get the current volume level."""
    vol = _get_volume()
    muted = _run_osascript("output muted of (get volume settings)")
    if muted == "true":
        return f"Volume is at {vol}%, currently muted."
    return f"Volume is at {vol}%."
