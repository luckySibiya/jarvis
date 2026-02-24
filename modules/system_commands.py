"""System-level commands: time, date, and other OS interactions."""

from datetime import datetime

from core.command_router import register


@register("system", "time")
def get_time() -> str:
    now = datetime.now().strftime("%I:%M %p")
    return f"The current time is {now}."


@register("system", "date")
def get_date() -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    return f"Today is {today}."
