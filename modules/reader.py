"""Read things aloud — emails, files, notes, reminders, calendar events, selected text.

Jarvis reads content and the voice engine speaks it. This module returns text
that gets spoken automatically by the main loop.
"""

import subprocess
import imaplib
import email
from email.header import decode_header
from pathlib import Path

from core.command_router import register
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
from utils.logger import get_logger

logger = get_logger(__name__)


def _osascript(script: str) -> str:
    """Run an AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip()


# --- Email Reading (IMAP) ---

@register("system", "read_emails")
def read_emails(count: int = 5) -> str:
    """Read the latest emails from Gmail inbox via IMAP."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return (
            "Email is not configured. Add GMAIL_ADDRESS and "
            "GMAIL_APP_PASSWORD to your .env file."
        )

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        _, data = mail.search(None, "ALL")
        mail_ids = data[0].split()

        if not mail_ids:
            mail.logout()
            return "Your inbox is empty, sir."

        # Get the latest N emails
        latest = mail_ids[-count:]
        latest.reverse()

        results = []
        for i, mail_id in enumerate(latest, 1):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            # Decode subject
            subject_raw = msg["Subject"] or "(No subject)"
            decoded_parts = decode_header(subject_raw)
            subject = ""
            for part, enc in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part

            sender = msg["From"] or "Unknown"
            # Clean sender: "Name <email>" -> "Name"
            if "<" in sender:
                sender = sender.split("<")[0].strip().strip('"')

            results.append(f"{i}. From {sender} — {subject}")

        mail.logout()
        summary = "\n".join(results)
        return f"Here are your latest {len(results)} emails, sir:\n{summary}"

    except Exception as e:
        logger.error(f"Email read error: {e}")
        return f"Could not read emails: {e}"


@register("system", "read_email_detail")
def read_email_detail(index: int = 1) -> str:
    """Read the full content of a specific email (by index, 1 = most recent)."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return "Email is not configured."

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        _, data = mail.search(None, "ALL")
        mail_ids = data[0].split()

        if not mail_ids:
            mail.logout()
            return "Your inbox is empty."

        # Index from the end (1 = most recent)
        target_id = mail_ids[-index]
        _, msg_data = mail.fetch(target_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        # Decode subject
        subject_raw = msg["Subject"] or "(No subject)"
        decoded_parts = decode_header(subject_raw)
        subject = ""
        for part, enc in decoded_parts:
            if isinstance(part, bytes):
                subject += part.decode(enc or "utf-8", errors="replace")
            else:
                subject += part

        sender = msg["From"] or "Unknown"

        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="replace")

        # Truncate long emails for speech
        if len(body) > 500:
            body = body[:500] + "... The email continues."

        mail.logout()
        return f"Email from {sender}. Subject: {subject}. Content: {body.strip()}"

    except Exception as e:
        logger.error(f"Email detail error: {e}")
        return f"Could not read email: {e}"


# --- Read Files ---

@register("system", "read_file")
def read_file(path: str) -> str:
    """Read the contents of a text file aloud."""
    try:
        file_path = Path(path).expanduser()
        if not file_path.exists():
            return f"File not found: {path}"
        if not file_path.is_file():
            return f"That's a directory, not a file: {path}"

        text = file_path.read_text(errors="replace")

        if len(text) > 1000:
            text = text[:1000] + "... The file continues."

        return f"Contents of {file_path.name}:\n{text}"
    except Exception as e:
        logger.error(f"Read file error: {e}")
        return f"Could not read file: {e}"


# --- Read Calendar Events ---

@register("system", "read_calendar")
def read_calendar(days: int = 1) -> str:
    """Read upcoming calendar events from the Calendar app."""
    try:
        script = f'''
        set today to current date
        set endDate to today + ({days} * days)
        set output to ""

        tell application "Calendar"
            set allCalendars to every calendar
            set eventList to {{}}
            repeat with cal in allCalendars
                set calEvents to (every event of cal whose start date >= today and start date <= endDate)
                repeat with evt in calEvents
                    set evtSummary to summary of evt
                    set evtStart to start date of evt
                    set output to output & evtSummary & " at " & time string of evtStart & " on " & date string of evtStart & linefeed
                end repeat
            end repeat
        end tell

        if output is "" then
            return "No upcoming events in the next {days} day(s)."
        else
            return output
        end if
        '''
        result = _osascript(script)
        if not result:
            return f"No upcoming events in the next {days} day(s), sir."
        return f"Your upcoming events:\n{result}"
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return f"Could not read calendar: {e}"


# --- Read Reminders ---

@register("system", "read_reminders")
def read_reminders() -> str:
    """Read incomplete reminders from the Reminders app."""
    try:
        script = '''
        tell application "Reminders"
            set output to ""
            set allReminders to (every reminder whose completed is false)
            if (count of allReminders) is 0 then
                return "No pending reminders."
            end if
            set counter to 0
            repeat with r in allReminders
                set counter to counter + 1
                if counter > 10 then exit repeat
                set output to output & counter & ". " & name of r & linefeed
            end repeat
            return output
        end tell
        '''
        result = _osascript(script)
        if not result:
            return "No pending reminders, sir."
        return f"Your reminders:\n{result}"
    except Exception as e:
        logger.error(f"Reminders error: {e}")
        return f"Could not read reminders: {e}"


# --- Add Reminder ---

@register("system", "add_reminder")
def add_reminder(text: str) -> str:
    """Add a new reminder to the Reminders app."""
    safe_text = text.replace('"', '\\"')
    try:
        _osascript(f'''
        tell application "Reminders"
            tell list "Reminders"
                make new reminder with properties {{name:"{safe_text}"}}
            end tell
        end tell
        ''')
        return f"Reminder added: {text}"
    except Exception as e:
        logger.error(f"Add reminder error: {e}")
        return f"Could not add reminder: {e}"


# --- Add Calendar Event ---

@register("system", "add_event")
def add_calendar_event(title: str, date: str, time: str = "09:00") -> str:
    """Add a calendar event. Date format: YYYY-MM-DD, Time: HH:MM."""
    safe_title = title.replace('"', '\\"')
    try:
        script = f'''
        set eventDate to date "{date} {time}"
        set endDate to eventDate + (1 * hours)

        tell application "Calendar"
            tell calendar "Home"
                make new event with properties {{summary:"{safe_title}", start date:eventDate, end date:endDate}}
            end tell
        end tell
        return "Event created."
        '''
        _osascript(script)
        return f"Calendar event added: {title} on {date} at {time}."
    except Exception as e:
        logger.error(f"Add event error: {e}")
        return f"Could not add event: {e}"


# --- Read Notes ---

@register("system", "read_notes")
def read_notes() -> str:
    """Read recent notes from the Notes app."""
    try:
        script = '''
        tell application "Notes"
            set output to ""
            set noteList to (every note of default account)
            set counter to 0
            repeat with n in noteList
                set counter to counter + 1
                if counter > 5 then exit repeat
                set noteTitle to name of n
                set output to output & counter & ". " & noteTitle & linefeed
            end repeat
            if output is "" then
                return "No notes found."
            end if
            return output
        end tell
        '''
        result = _osascript(script)
        if not result:
            return "No notes found, sir."
        return f"Your recent notes:\n{result}"
    except Exception as e:
        logger.error(f"Read notes error: {e}")
        return f"Could not read notes: {e}"


# --- Create Note ---

@register("system", "create_note")
def create_note(title: str, body: str = "") -> str:
    """Create a new note in the Notes app."""
    safe_title = title.replace('"', '\\"')
    safe_body = body.replace('"', '\\"')
    try:
        _osascript(f'''
        tell application "Notes"
            tell default account
                make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
            end tell
        end tell
        ''')
        return f"Note created: {title}"
    except Exception as e:
        logger.error(f"Create note error: {e}")
        return f"Could not create note: {e}"


# --- Read Selected Text (on screen) ---

@register("system", "read_selected")
def read_selected_text() -> str:
    """Read the currently selected text on screen."""
    try:
        # Copy selection to clipboard, read it
        _osascript('''
        tell application "System Events"
            keystroke "c" using command down
        end tell
        ''')
        import time
        time.sleep(0.3)
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5,
        )
        text = result.stdout.strip()
        if not text:
            return "No text is currently selected."
        if len(text) > 500:
            text = text[:500] + "... There's more text selected."
        return f"The selected text reads: {text}"
    except Exception as e:
        logger.error(f"Read selected error: {e}")
        return f"Could not read selected text: {e}"
