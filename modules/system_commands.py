"""System-level commands: time, date, battery, wifi, disk, IP, and more."""

import shutil
import socket
import subprocess
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


@register("system", "battery")
def get_battery() -> str:
    """Get battery level and charging status."""
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout
        # Parse: "... 85%; charging; ..."
        for line in output.split("\n"):
            if "%" in line:
                parts = line.strip()
                # Extract percentage
                pct_start = parts.index("\t") if "\t" in parts else 0
                info = parts[pct_start:].strip()
                return f"Battery: {info}"
        return "Could not read battery status."
    except Exception as e:
        return f"Could not get battery info: {e}"


@register("system", "wifi")
def get_wifi() -> str:
    """Get current Wi-Fi network name."""
    try:
        result = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.strip()
        if "Current Wi-Fi Network" in output:
            network = output.split(":")[1].strip()
            return f"Connected to Wi-Fi: {network}"
        return "Not connected to Wi-Fi."
    except Exception as e:
        return f"Could not get Wi-Fi info: {e}"


@register("system", "ip_address")
def get_ip() -> str:
    """Get local and public IP addresses."""
    try:
        # Local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        # Public IP
        import requests
        public_ip = requests.get("https://api.ipify.org", timeout=5).text

        return f"Local IP: {local_ip}. Public IP: {public_ip}."
    except Exception as e:
        return f"Could not get IP address: {e}"


@register("system", "disk_space")
def get_disk_space() -> str:
    """Get available disk space."""
    total, used, free = shutil.disk_usage("/")
    total_gb = total / (1024 ** 3)
    free_gb = free / (1024 ** 3)
    used_pct = (used / total) * 100
    return f"Disk: {free_gb:.1f} GB free of {total_gb:.1f} GB total ({used_pct:.0f}% used)."


@register("system", "brightness_up")
def brightness_up() -> str:
    """Increase screen brightness."""
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to key code 144'],
            capture_output=True, timeout=5,
        )
        return "Brightness increased."
    except Exception:
        return "Could not adjust brightness."


@register("system", "brightness_down")
def brightness_down() -> str:
    """Decrease screen brightness."""
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to key code 145'],
            capture_output=True, timeout=5,
        )
        return "Brightness decreased."
    except Exception:
        return "Could not adjust brightness."
