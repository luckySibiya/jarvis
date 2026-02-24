"""Phone calls and messaging via macOS Continuity (iPhone integration).

Uses FaceTime for calls and iMessage for texts — requires iPhone connected
to the same iCloud account as the Mac.
"""

import subprocess

from core.command_router import register, set_pending
from utils.logger import get_logger

logger = get_logger(__name__)


def _osascript(script: str) -> str:
    """Run an AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip()


# --- Phone Calls ---

@register("phone", "call")
def make_call(number: str = "") -> str:
    """Make a phone call via FaceTime (uses iPhone Continuity)."""
    if not number or not number.strip():
        set_pending("phone", "call", "number")
        return "Who would you like me to call, sir? Please say a name or phone number."
    # Clean the number
    clean = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    try:
        # FaceTime audio call via open command — triggers iPhone Continuity
        subprocess.Popen(["open", f"tel:{clean}"])
        return f"Calling {number}, sir."
    except Exception as e:
        logger.error(f"Call error: {e}")
        return f"Failed to initiate call: {e}"


@register("phone", "facetime")
def facetime_call(number: str = "") -> str:
    """Make a FaceTime video call."""
    if not number or not number.strip():
        set_pending("phone", "facetime", "number")
        return "Who would you like me to FaceTime, sir?"
    clean = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    try:
        subprocess.Popen(["open", f"facetime:{clean}"])
        return f"Starting FaceTime video call with {number}, sir."
    except Exception as e:
        logger.error(f"FaceTime error: {e}")
        return f"Failed to start FaceTime: {e}"


@register("phone", "facetime_audio")
def facetime_audio(number: str = "") -> str:
    """Make a FaceTime audio call."""
    if not number or not number.strip():
        set_pending("phone", "facetime_audio", "number")
        return "Who would you like me to FaceTime audio, sir?"
    clean = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    try:
        subprocess.Popen(["open", f"facetime-audio:{clean}"])
        return f"Starting FaceTime audio call with {number}, sir."
    except Exception as e:
        logger.error(f"FaceTime audio error: {e}")
        return f"Failed to start FaceTime audio: {e}"


# --- Text Messages ---

@register("phone", "send_message")
def send_imessage(to: str = "", message: str = "") -> str:
    """Send an iMessage/SMS via the Messages app."""
    if not to or not to.strip():
        set_pending("phone", "send_message", "to")
        return "Who would you like me to send a message to, sir?"
    if not message or not message.strip():
        set_pending("phone", "send_message", "message", {"to": to})
        return f"What would you like me to say to {to}, sir?"
    # Escape quotes for AppleScript
    safe_msg = message.replace('"', '\\"')
    safe_to = to.replace('"', '\\"')

    script = f'''
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to participant "{safe_to}" of targetService
        send "{safe_msg}" to targetBuddy
    end tell
    '''
    try:
        _osascript(script)
        return f"Message sent to {to}: \"{message}\""
    except Exception as e:
        logger.error(f"iMessage error: {e}")
        return f"Failed to send message: {e}"


@register("phone", "read_messages")
def read_messages(contact: str = "") -> str:
    """Read recent iMessages, optionally filtered by contact."""
    try:
        if contact:
            # Read recent messages from a specific contact via Messages app
            script = f'''
            tell application "Messages"
                set output to ""
                set targetChats to (every chat whose name contains "{contact}")
                if (count of targetChats) > 0 then
                    set targetChat to item 1 of targetChats
                    set msgs to (messages 1 thru (min of {{5, count of messages of targetChat}}) of targetChat)
                    repeat with m in msgs
                        set sender_name to sender of m
                        set msg_text to text of m
                        set output to output & sender_name & ": " & msg_text & linefeed
                    end repeat
                else
                    set output to "No conversation found with " & "{contact}"
                end if
                return output
            end tell
            '''
        else:
            # Read recent messages from the most recent chat
            script = '''
            tell application "Messages"
                set output to ""
                if (count of chats) > 0 then
                    set recentChat to item 1 of chats
                    set chatName to name of recentChat
                    set output to "Recent chat with: " & chatName & linefeed
                    set msgCount to min of {5, count of messages of recentChat}
                    set msgs to (messages 1 thru msgCount of recentChat)
                    repeat with m in msgs
                        set sender_name to sender of m
                        set msg_text to text of m
                        set output to output & sender_name & ": " & msg_text & linefeed
                    end repeat
                else
                    set output to "No recent messages found."
                end if
                return output
            end tell
            '''
        result = _osascript(script)
        if not result:
            return "No messages found."
        return f"Recent messages:\n{result}"
    except Exception as e:
        logger.error(f"Read messages error: {e}")
        return f"Could not read messages: {e}"
