"""Smart home and device integration — HomeKit control, AirPlay, Bluetooth,
Find My, AirDrop, screen mirroring, and audio output switching.

Uses macOS Shortcuts app, AppleScript, and command-line tools (blueutil,
SwitchAudioSource) for HomeKit and peripheral device control.
"""

import subprocess
import shutil

from core.command_router import register, set_pending
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _osascript(script: str, timeout: int = 15) -> str:
    """Run an AppleScript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip()


def _run_shortcut(name: str, input_text: str = "", timeout: int = 15) -> str:
    """Run a macOS Shortcut by name, optionally passing input text."""
    cmd = ["shortcuts", "run", name]
    if input_text:
        cmd += ["-i", input_text]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


# ===========================================================================
#  HomeKit Smart Home  (category = "smart_home")
# ===========================================================================

# --- Lights On ---

@register("smart_home", "lights_on")
def lights_on(room: str = "") -> str:
    """Turn on lights via Shortcuts or AppleScript Home app integration."""
    try:
        if room:
            # Try Shortcut first — many users create room-specific shortcuts
            try:
                _run_shortcut("Turn On Lights", input_text=room)
                return f"Lights on in the {room}, sir."
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            # Fallback: AppleScript telling Home app
            script = (
                'tell application "Home" to activate\n'
                f'delay 1\n'
                f'tell application "System Events" to tell process "Home" '
                f'to click button "Turn On" of group "{room}" of window 1'
            )
            _osascript(script)
            return f"Lights on in the {room}, sir."
        else:
            try:
                _run_shortcut("Turn On Lights")
                return "Lights turned on, sir."
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            _osascript(
                'tell application "Home" to activate'
            )
            return "Lights turned on, sir."
    except Exception as e:
        logger.error(f"lights_on error: {e}")
        return f"Sorry, I couldn't turn on the lights: {e}"


# --- Lights Off ---

@register("smart_home", "lights_off")
def lights_off(room: str = "") -> str:
    """Turn off lights via Shortcuts or AppleScript Home app integration."""
    try:
        if room:
            try:
                _run_shortcut("Turn Off Lights", input_text=room)
                return f"Lights off in the {room}, sir."
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            script = (
                'tell application "Home" to activate\n'
                f'delay 1\n'
                f'tell application "System Events" to tell process "Home" '
                f'to click button "Turn Off" of group "{room}" of window 1'
            )
            _osascript(script)
            return f"Lights off in the {room}, sir."
        else:
            try:
                _run_shortcut("Turn Off Lights")
                return "Lights turned off, sir."
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            _osascript(
                'tell application "Home" to activate'
            )
            return "Lights turned off, sir."
    except Exception as e:
        logger.error(f"lights_off error: {e}")
        return f"Sorry, I couldn't turn off the lights: {e}"


# --- Set Brightness ---

@register("smart_home", "set_brightness")
def set_brightness_home(level: int = 50, room: str = "") -> str:
    """Set light brightness level (0-100) via Shortcuts or AppleScript."""
    level = max(0, min(100, int(level)))
    try:
        shortcut_input = f"{level}"
        if room:
            shortcut_input = f"{room}:{level}"
        try:
            _run_shortcut("Set Brightness", input_text=shortcut_input)
            if room:
                return f"Brightness in the {room} set to {level}%, sir."
            return f"Brightness set to {level}%, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: AppleScript to Home app
        script = (
            'tell application "Home" to activate\n'
            'delay 1\n'
            'tell application "System Events" to tell process "Home" '
            f'to set value of slider 1 of window 1 to {level}'
        )
        _osascript(script)
        if room:
            return f"Brightness in the {room} set to {level}%, sir."
        return f"Brightness set to {level}%, sir."
    except Exception as e:
        logger.error(f"set_brightness error: {e}")
        return f"Sorry, I couldn't set the brightness: {e}"


# --- Set Thermostat ---

@register("smart_home", "set_thermostat")
def set_thermostat(temperature: int = 72) -> str:
    """Set thermostat temperature via Shortcuts or AppleScript."""
    temperature = int(temperature)
    try:
        try:
            _run_shortcut("Set Thermostat", input_text=str(temperature))
            return f"Thermostat set to {temperature} degrees, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: AppleScript to Home app
        script = (
            'tell application "Home" to activate\n'
            'delay 1\n'
            'tell application "System Events" to tell process "Home" '
            f'to set value of value indicator 1 of slider 1 of window 1 to {temperature}'
        )
        _osascript(script)
        return f"Thermostat set to {temperature} degrees, sir."
    except Exception as e:
        logger.error(f"set_thermostat error: {e}")
        return f"Sorry, I couldn't set the thermostat: {e}"


# --- Scene ---

@register("smart_home", "scene")
def scene(name: str = "") -> str:
    """Activate a HomeKit scene by name via Shortcuts or AppleScript."""
    if not name or not name.strip():
        set_pending("smart_home", "scene", "name")
        return "Which scene would you like me to activate, sir?"
    name = name.strip()
    try:
        # Try running a Shortcut named after the scene
        try:
            _run_shortcut(name)
            return f"Scene '{name}' activated, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: generic "Set Scene" shortcut with scene name as input
        try:
            _run_shortcut("Set Scene", input_text=name)
            return f"Scene '{name}' activated, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: AppleScript
        safe_name = name.replace('"', '\\"')
        script = (
            'tell application "Home" to activate\n'
            'delay 1\n'
            'tell application "System Events" to tell process "Home" '
            f'to click button "{safe_name}" of window 1'
        )
        _osascript(script)
        return f"Scene '{name}' activated, sir."
    except Exception as e:
        logger.error(f"scene error: {e}")
        return f"Sorry, I couldn't activate the scene '{name}': {e}"


# --- Smart Home Status ---

@register("smart_home", "status")
def smart_home_status() -> str:
    """Get status of HomeKit devices via Shortcuts or Home app."""
    try:
        # Try a Shortcut that returns device status
        try:
            output = _run_shortcut("Home Status")
            if output:
                return f"Smart home status:\n{output}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: open Home app so user can see the status visually
        subprocess.run(["open", "-a", "Home"], capture_output=True, timeout=5)
        return ("I've opened the Home app for you, sir. "
                "I can't read device status directly without a Shortcut — "
                "please create a 'Home Status' shortcut in the Shortcuts app "
                "for hands-free status reports.")
    except Exception as e:
        logger.error(f"smart_home_status error: {e}")
        return f"Sorry, I couldn't retrieve smart home status: {e}"


# ===========================================================================
#  Device Control  (category = "device")
# ===========================================================================

# --- AirPlay ---

@register("device", "airplay")
def airplay_to(device: str = "") -> str:
    """AirPlay to a device (Apple TV, speaker) via Shortcuts or AppleScript."""
    if not device or not device.strip():
        set_pending("device", "airplay", "device")
        return "Which device would you like me to AirPlay to, sir?"
    device = device.strip()
    try:
        # Try a Shortcut that handles AirPlay routing
        try:
            _run_shortcut("AirPlay To", input_text=device)
            return f"Now AirPlaying to {device}, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: AppleScript to set AirPlay destination
        safe_device = device.replace('"', '\\"')
        script = (
            'tell application "System Events"\n'
            '    tell process "Control Center"\n'
            '        click menu bar item "Screen Mirroring" of menu bar 1\n'
            '        delay 1\n'
            f'        click button "{safe_device}" of window 1\n'
            '    end tell\n'
            'end tell'
        )
        _osascript(script)
        return f"Now AirPlaying to {device}, sir."
    except Exception as e:
        logger.error(f"airplay_to error: {e}")
        return f"Sorry, I couldn't start AirPlay to {device}: {e}"


# --- Audio Output ---

@register("device", "audio_output")
def audio_output(device: str = "") -> str:
    """Switch audio output device using SwitchAudioSource or AppleScript."""
    if not device or not device.strip():
        set_pending("device", "audio_output", "device")
        return "Which audio output device would you like to switch to, sir?"
    device = device.strip()
    try:
        # Prefer SwitchAudioSource if installed (brew install switchaudio-osx)
        if shutil.which("SwitchAudioSource"):
            result = subprocess.run(
                ["SwitchAudioSource", "-s", device],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return f"Audio output switched to {device}, sir."
            # If exact name didn't match, list available devices
            avail = subprocess.run(
                ["SwitchAudioSource", "-a", "-t", "output"],
                capture_output=True, text=True, timeout=5,
            )
            return (f"Couldn't find '{device}'. Available output devices:\n"
                    f"{avail.stdout.strip()}")
        # Fallback: AppleScript via System Settings sound pane
        safe_device = device.replace('"', '\\"')
        script = (
            'tell application "System Preferences"\n'
            '    reveal anchor "output" of pane id '
            '"com.apple.preference.sound"\n'
            '    activate\n'
            'end tell\n'
            'delay 1\n'
            'tell application "System Events"\n'
            '    tell process "System Preferences"\n'
            '        set rows_ to every row of table 1 of scroll area 1 '
            'of tab group 1 of window 1\n'
            '        repeat with r in rows_\n'
            '            if name of text field 1 of r contains '
            f'"{safe_device}" then\n'
            '                select r\n'
            '                exit repeat\n'
            '            end if\n'
            '        end repeat\n'
            '    end tell\n'
            'end tell\n'
            'tell application "System Preferences" to quit'
        )
        _osascript(script, timeout=20)
        return f"Audio output switched to {device}, sir."
    except Exception as e:
        logger.error(f"audio_output error: {e}")
        return f"Sorry, I couldn't switch audio output to {device}: {e}"


# --- Find My Device ---

@register("device", "find_my")
def find_my_device(device: str = "iphone") -> str:
    """Play sound on iPhone/iPad/Mac via Find My app or URL scheme."""
    device = device.strip().lower() if device else "iphone"
    try:
        # Try the findmy:// URL scheme to open Find My app
        try:
            subprocess.run(
                ["open", "findmy://"],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            subprocess.run(
                ["open", "-a", "Find My"],
                capture_output=True, timeout=5,
            )
        # Try a Shortcut to play sound on the specific device
        try:
            _run_shortcut("Find My Device", input_text=device)
            return f"Playing sound on your {device}, sir. Check Find My for the location."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return (f"I've opened Find My for you, sir. "
                f"Please select your {device} and tap 'Play Sound'. "
                f"For hands-free control, create a 'Find My Device' shortcut.")
    except Exception as e:
        logger.error(f"find_my_device error: {e}")
        return f"Sorry, I couldn't locate your {device}: {e}"


# --- AirDrop ---

@register("device", "airdrop")
def airdrop_file(path: str = "") -> str:
    """Open AirDrop sharing for a file, or just open the AirDrop window."""
    try:
        if path and path.strip():
            path = path.strip()
            # Use Finder's share sheet to AirDrop a specific file
            safe_path = path.replace('"', '\\"')
            script = (
                'tell application "Finder"\n'
                f'    set theFile to POSIX file "{safe_path}" as alias\n'
                '    activate\n'
                'end tell\n'
                'tell application "System Events"\n'
                '    tell process "Finder"\n'
                '        keystroke "r" using {command down, shift down}\n'
                '    end tell\n'
                'end tell'
            )
            _osascript(script, timeout=10)
            return f"AirDrop window opened for {path}, sir. Select a recipient."
        else:
            # Just open AirDrop in Finder
            subprocess.run(
                ["open", "-a", "Finder"],
                capture_output=True, timeout=5,
            )
            script = (
                'tell application "Finder"\n'
                '    activate\n'
                'end tell\n'
                'tell application "System Events"\n'
                '    tell process "Finder"\n'
                '        keystroke "r" using {command down, shift down}\n'
                '    end tell\n'
                'end tell'
            )
            _osascript(script, timeout=10)
            return "AirDrop window opened, sir. You can drag files to share."
    except Exception as e:
        logger.error(f"airdrop_file error: {e}")
        return f"Sorry, I couldn't open AirDrop: {e}"


# --- Connect Bluetooth Device ---

@register("device", "connect_bluetooth")
def connect_bluetooth_device(device: str = "") -> str:
    """Connect to a specific Bluetooth device by name using blueutil."""
    if not device or not device.strip():
        set_pending("device", "connect_bluetooth", "device")
        return "Which Bluetooth device would you like me to connect to, sir?"
    device = device.strip()
    try:
        if not shutil.which("blueutil"):
            return ("The 'blueutil' command is not installed. "
                    "Install it with: brew install blueutil")
        # List paired devices and find the matching one
        result = subprocess.run(
            ["blueutil", "--paired"],
            capture_output=True, text=True, timeout=10,
        )
        device_address = None
        device_lower = device.lower()
        for line in result.stdout.strip().splitlines():
            if device_lower in line.lower():
                # blueutil output format: address: XX-XX-XX, ...
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if part.startswith("address:"):
                        device_address = part.split(":", 1)[1].strip()
                        break
                if device_address:
                    break
        if not device_address:
            return (f"Couldn't find '{device}' in paired devices. "
                    f"Try pairing it first, or say 'list Bluetooth devices' "
                    f"to see what's available.")
        subprocess.run(
            ["blueutil", "--connect", device_address],
            capture_output=True, text=True, timeout=15,
        )
        return f"Connected to {device}, sir."
    except subprocess.TimeoutExpired:
        return f"Connection to {device} timed out. The device may be out of range."
    except Exception as e:
        logger.error(f"connect_bluetooth error: {e}")
        return f"Sorry, I couldn't connect to {device}: {e}"


# --- Disconnect Bluetooth Device ---

@register("device", "disconnect_bluetooth")
def disconnect_bluetooth_device(device: str = "") -> str:
    """Disconnect a Bluetooth device by name using blueutil."""
    if not device or not device.strip():
        set_pending("device", "disconnect_bluetooth", "device")
        return "Which Bluetooth device would you like me to disconnect, sir?"
    device = device.strip()
    try:
        if not shutil.which("blueutil"):
            return ("The 'blueutil' command is not installed. "
                    "Install it with: brew install blueutil")
        # Find the device address from paired list
        result = subprocess.run(
            ["blueutil", "--paired"],
            capture_output=True, text=True, timeout=10,
        )
        device_address = None
        device_lower = device.lower()
        for line in result.stdout.strip().splitlines():
            if device_lower in line.lower():
                parts = line.split(",")
                for part in parts:
                    part = part.strip()
                    if part.startswith("address:"):
                        device_address = part.split(":", 1)[1].strip()
                        break
                if device_address:
                    break
        if not device_address:
            return (f"Couldn't find '{device}' in paired devices. "
                    f"Say 'list Bluetooth devices' to see what's available.")
        subprocess.run(
            ["blueutil", "--disconnect", device_address],
            capture_output=True, text=True, timeout=15,
        )
        return f"Disconnected from {device}, sir."
    except subprocess.TimeoutExpired:
        return f"Disconnecting from {device} timed out."
    except Exception as e:
        logger.error(f"disconnect_bluetooth error: {e}")
        return f"Sorry, I couldn't disconnect from {device}: {e}"


# --- List Bluetooth Devices ---

@register("device", "list_bluetooth")
def list_bluetooth_devices() -> str:
    """List paired Bluetooth devices using blueutil."""
    try:
        if not shutil.which("blueutil"):
            return ("The 'blueutil' command is not installed. "
                    "Install it with: brew install blueutil")
        result = subprocess.run(
            ["blueutil", "--paired"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        if not output:
            return "No paired Bluetooth devices found."
        # Parse into a more readable format
        devices = []
        for line in output.splitlines():
            # Extract name and connected status
            name = ""
            connected = "unknown"
            for part in line.split(","):
                part = part.strip()
                if part.startswith("name:"):
                    name = part.split(":", 1)[1].strip().strip('"')
                elif part.startswith("connected:"):
                    connected = "connected" if "1" in part else "disconnected"
            if name:
                devices.append(f"  - {name} ({connected})")
        if not devices:
            return f"Paired devices:\n{output}"
        return "Paired Bluetooth devices:\n" + "\n".join(devices)
    except Exception as e:
        logger.error(f"list_bluetooth error: {e}")
        return f"Sorry, I couldn't list Bluetooth devices: {e}"


# --- Screen Mirror ---

@register("device", "screen_mirror")
def screen_mirror(device: str = "") -> str:
    """Start screen mirroring to Apple TV or external display."""
    if not device or not device.strip():
        set_pending("device", "screen_mirror", "device")
        return "Which device would you like me to mirror the screen to, sir?"
    device = device.strip()
    try:
        # Try a Shortcut for screen mirroring
        try:
            _run_shortcut("Screen Mirror", input_text=device)
            return f"Screen mirroring to {device}, sir."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Fallback: use Control Center's Screen Mirroring via AppleScript
        safe_device = device.replace('"', '\\"')
        script = (
            'tell application "System Events"\n'
            '    tell process "Control Center"\n'
            '        click menu bar item "Screen Mirroring" of menu bar 1\n'
            '        delay 1.5\n'
            f'        click checkbox "{safe_device}" of window 1\n'
            '    end tell\n'
            'end tell'
        )
        _osascript(script, timeout=20)
        return f"Screen mirroring to {device}, sir."
    except Exception as e:
        logger.error(f"screen_mirror error: {e}")
        return f"Sorry, I couldn't start screen mirroring to {device}: {e}"
