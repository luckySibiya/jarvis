"""Full system control — sleep, restart, lock, empty trash, toggle dark mode,
Bluetooth, Wi-Fi, Do Not Disturb, notifications, clipboard, and shell commands.
"""

import subprocess

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)


def _osascript(script: str) -> str:
    """Run an AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


# --- Power & Lock ---

@register("system", "lock_screen")
def lock_screen() -> str:
    """Lock the screen."""
    subprocess.Popen([
        "osascript", "-e",
        'tell application "System Events" to keystroke "q" '
        'using {command down, control down}'
    ])
    return "Locking screen, sir."


@register("system", "sleep")
def sleep_mac() -> str:
    """Put the Mac to sleep."""
    subprocess.Popen(["pmset", "sleepnow"])
    return "Going to sleep, sir."


@register("system", "restart")
def restart_mac() -> str:
    """Restart the Mac."""
    _osascript('tell application "System Events" to restart')
    return "Restarting now, sir."


@register("system", "shutdown")
def shutdown_mac() -> str:
    """Shut down the Mac."""
    _osascript('tell application "System Events" to shut down')
    return "Shutting down, sir."


# --- Display & Appearance ---

@register("system", "dark_mode_on")
def dark_mode_on() -> str:
    """Enable dark mode."""
    _osascript(
        'tell application "System Events" to tell appearance preferences '
        'to set dark mode to true'
    )
    return "Dark mode enabled."


@register("system", "dark_mode_off")
def dark_mode_off() -> str:
    """Disable dark mode."""
    _osascript(
        'tell application "System Events" to tell appearance preferences '
        'to set dark mode to false'
    )
    return "Dark mode disabled."


@register("system", "toggle_dark_mode")
def toggle_dark_mode() -> str:
    """Toggle dark mode."""
    _osascript(
        'tell application "System Events" to tell appearance preferences '
        'to set dark mode to not dark mode'
    )
    return "Dark mode toggled."


# --- Connectivity ---

@register("system", "wifi_on")
def wifi_on() -> str:
    """Turn Wi-Fi on."""
    subprocess.run(["networksetup", "-setairportpower", "en0", "on"],
                   capture_output=True, timeout=5)
    return "Wi-Fi turned on."


@register("system", "wifi_off")
def wifi_off() -> str:
    """Turn Wi-Fi off."""
    subprocess.run(["networksetup", "-setairportpower", "en0", "off"],
                   capture_output=True, timeout=5)
    return "Wi-Fi turned off."


@register("system", "bluetooth_on")
def bluetooth_on() -> str:
    """Turn Bluetooth on."""
    subprocess.run(["blueutil", "--power", "1"],
                   capture_output=True, timeout=5)
    return "Bluetooth turned on."


@register("system", "bluetooth_off")
def bluetooth_off() -> str:
    """Turn Bluetooth off."""
    subprocess.run(["blueutil", "--power", "0"],
                   capture_output=True, timeout=5)
    return "Bluetooth turned off."


# --- Finder & Files ---

@register("system", "empty_trash")
def empty_trash() -> str:
    """Empty the Trash."""
    _osascript(
        'tell application "Finder" to empty trash'
    )
    return "Trash emptied, sir."


@register("system", "show_desktop")
def show_desktop() -> str:
    """Show the desktop (minimize all windows)."""
    _osascript(
        'tell application "System Events" to key code 103 '
        'using {command down, fn down}'
    )
    return "Showing desktop."


@register("system", "open_folder")
def open_folder(path: str) -> str:
    """Open a folder in Finder."""
    result = subprocess.run(
        ["open", path],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0:
        return f"Opened {path}."
    return f"Could not open folder: {path}"


# --- Clipboard ---

@register("system", "clipboard_read")
def clipboard_read() -> str:
    """Read the current clipboard contents."""
    result = subprocess.run(
        ["pbpaste"],
        capture_output=True, text=True, timeout=5,
    )
    text = result.stdout.strip()
    if not text:
        return "Clipboard is empty."
    if len(text) > 200:
        text = text[:200] + "..."
    return f"Clipboard contains: {text}"


@register("system", "clipboard_write")
def clipboard_write(text: str) -> str:
    """Copy text to the clipboard."""
    process = subprocess.Popen(
        ["pbcopy"],
        stdin=subprocess.PIPE,
    )
    process.communicate(text.encode())
    return f"Copied to clipboard: {text}"


# --- Notifications ---

@register("system", "notify")
def send_notification(message: str, title: str = "Jarvis") -> str:
    """Send a macOS notification."""
    _osascript(
        f'display notification "{message}" with title "{title}"'
    )
    return f"Notification sent: {message}"


@register("system", "do_not_disturb_on")
def dnd_on() -> str:
    """Enable Do Not Disturb / Focus mode."""
    subprocess.run(
        ["shortcuts", "run", "Turn On Do Not Disturb"],
        capture_output=True, timeout=5,
    )
    return "Do Not Disturb enabled."


@register("system", "do_not_disturb_off")
def dnd_off() -> str:
    """Disable Do Not Disturb / Focus mode."""
    subprocess.run(
        ["shortcuts", "run", "Turn Off Do Not Disturb"],
        capture_output=True, timeout=5,
    )
    return "Do Not Disturb disabled."


# --- General Shell Command ---

@register("system", "run_command")
def run_shell_command(command: str) -> str:
    """Run a shell command and return the output.

    This is the ultimate fallback — Jarvis can execute anything.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0 and error:
            return f"Command failed: {error[:200]}"
        if not output:
            return "Command executed successfully."
        if len(output) > 300:
            output = output[:300] + "..."
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Could not run command: {e}"
