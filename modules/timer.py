"""Timer and alarm functionality."""

import threading

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)

_active_timers: dict[str, threading.Timer] = {}


def _timer_done(label: str, speak_func):
    """Called when a timer completes."""
    _active_timers.pop(label, None)
    speak_func(f"Timer complete: {label}. Time's up, sir!")


@register("system", "set_timer")
def set_timer(seconds: int, label: str = "timer") -> str:
    """Set a timer that speaks when done."""
    seconds = int(seconds)

    # Import speak here to avoid circular imports
    from core.voice_output import speak

    timer = threading.Timer(seconds, _timer_done, args=[label, speak])
    timer.daemon = True
    timer.start()
    _active_timers[label] = timer

    if seconds >= 3600:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        time_str = f"{hours} hour{'s' if hours > 1 else ''}"
        if mins:
            time_str += f" and {mins} minute{'s' if mins > 1 else ''}"
    elif seconds >= 60:
        mins = seconds // 60
        secs = seconds % 60
        time_str = f"{mins} minute{'s' if mins > 1 else ''}"
        if secs:
            time_str += f" and {secs} second{'s' if secs > 1 else ''}"
    else:
        time_str = f"{seconds} second{'s' if seconds > 1 else ''}"

    return f"Timer set for {time_str}, sir."


@register("system", "cancel_timer")
def cancel_timer(label: str = "timer") -> str:
    """Cancel an active timer."""
    timer = _active_timers.pop(label, None)
    if timer:
        timer.cancel()
        return f"Timer '{label}' cancelled."
    return "No active timer found with that name."
