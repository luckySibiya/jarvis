"""Persistent memory and learning module for Jarvis.

Stores user preferences, contacts, facts, routines, and command history
in a JSON file (~/.jarvis_memory.json) so Jarvis remembers things across sessions.
"""

import json
from pathlib import Path

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)

MEMORY_FILE = Path("~/.jarvis_memory.json").expanduser()

DEFAULT_MEMORY = {
    "user": {"name": "", "preferences": {}},
    "contacts": {},
    "facts": [],
    "routines": {},
    "command_history": [],
    "learned_corrections": {},
}


def _load_memory() -> dict:
    """Load memory from disk. Returns default structure if file missing or corrupt."""
    try:
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
            # Ensure all keys exist (in case file is from older version)
            for key, default in DEFAULT_MEMORY.items():
                if key not in data:
                    data[key] = default if not isinstance(default, (dict, list)) else type(default)(default)
            return data
    except Exception as e:
        logger.error(f"Failed to load memory file: {e}")
    # Return a fresh copy so mutations don't affect DEFAULT_MEMORY
    return json.loads(json.dumps(DEFAULT_MEMORY))


def _save_memory(data: dict) -> None:
    """Save memory to disk."""
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save memory file: {e}")


# Load memory once at module import
_memory = _load_memory()


# ---------------------------------------------------------------------------
# Memory Management (category="memory")
# ---------------------------------------------------------------------------

@register("memory", "remember")
def remember_fact(key: str, value: str = "") -> str:
    """Store a fact (e.g., 'my name is Lucky', 'my favorite song is X')."""
    key = key.strip().lower()
    value = value.strip()
    if not key:
        return "What would you like me to remember, sir?"
    if not value:
        return "What is the value you'd like me to remember for that?"

    # Update existing fact if key matches, otherwise append
    for fact in _memory["facts"]:
        if fact["key"] == key:
            fact["value"] = value
            _save_memory(_memory)
            logger.info(f"Updated fact: {key} = {value}")
            return f"Got it, sir. I've updated that {key} is {value}."

    _memory["facts"].append({"key": key, "value": value})
    _save_memory(_memory)
    logger.info(f"Stored fact: {key} = {value}")
    return f"I'll remember that, sir. {key} is {value}."


@register("memory", "recall")
def recall_fact(key: str) -> str:
    """Recall a stored fact. Searches facts by key substring match."""
    key = key.strip().lower()
    if not key:
        return "What would you like me to recall, sir?"

    matches = [f for f in _memory["facts"] if key in f["key"]]
    if not matches:
        return f"I don't have anything stored about '{key}', sir."
    if len(matches) == 1:
        return f"{matches[0]['key']} is {matches[0]['value']}, sir."

    lines = [f"  - {m['key']}: {m['value']}" for m in matches]
    return f"Here's what I know about '{key}':\n" + "\n".join(lines)


@register("memory", "forget")
def forget_fact(key: str) -> str:
    """Remove a stored fact."""
    key = key.strip().lower()
    if not key:
        return "What would you like me to forget, sir?"

    original_count = len(_memory["facts"])
    _memory["facts"] = [f for f in _memory["facts"] if key not in f["key"]]
    removed = original_count - len(_memory["facts"])

    if removed == 0:
        return f"I don't have anything stored about '{key}', sir."

    _save_memory(_memory)
    logger.info(f"Forgot {removed} fact(s) matching '{key}'")
    return f"Done, sir. I've forgotten {removed} fact{'s' if removed > 1 else ''} about '{key}'."


@register("memory", "save_contact")
def save_contact(name: str, number: str = "", email: str = "") -> str:
    """Save a contact nickname mapping."""
    name = name.strip().lower()
    if not name:
        return "What name should I save this contact under, sir?"
    if not number and not email:
        return f"Please provide a phone number or email for {name}."

    contact = {}
    if number:
        contact["number"] = number.strip()
    if email:
        contact["email"] = email.strip()

    _memory["contacts"][name] = contact
    _save_memory(_memory)

    details = []
    if number:
        details.append(number.strip())
    if email:
        details.append(email.strip())
    logger.info(f"Saved contact: {name} -> {', '.join(details)}")
    return f"Contact saved, sir. {name.title()} — {', '.join(details)}."


@register("memory", "get_contact")
def get_contact(name: str) -> str:
    """Look up a saved contact."""
    name = name.strip().lower()
    if not name:
        return "Which contact would you like me to look up, sir?"

    contact = _memory["contacts"].get(name)
    if not contact:
        # Try partial match
        matches = {k: v for k, v in _memory["contacts"].items() if name in k}
        if not matches:
            return f"I don't have a contact called '{name}', sir."
        if len(matches) == 1:
            match_name = list(matches.keys())[0]
            contact = matches[match_name]
            name = match_name
        else:
            names = ", ".join(m.title() for m in matches)
            return f"I found multiple contacts matching '{name}': {names}. Which one?"

    details = []
    if "number" in contact:
        details.append(f"phone: {contact['number']}")
    if "email" in contact:
        details.append(f"email: {contact['email']}")
    return f"{name.title()} — {', '.join(details)}."


@register("memory", "set_preference")
def set_preference(key: str, value: str = "") -> str:
    """Set a user preference."""
    key = key.strip().lower()
    value = value.strip()
    if not key:
        return "What preference would you like to set, sir?"
    if not value:
        return f"What value should I set for '{key}'?"

    _memory["user"]["preferences"][key] = value
    _save_memory(_memory)
    logger.info(f"Set preference: {key} = {value}")
    return f"Preference saved, sir. {key} is now {value}."


@register("memory", "get_preference")
def get_preference(key: str) -> str:
    """Get a user preference."""
    key = key.strip().lower()
    if not key:
        return "Which preference would you like me to look up, sir?"

    value = _memory["user"]["preferences"].get(key)
    if value is None:
        return f"I don't have a preference set for '{key}', sir."
    return f"Your {key} preference is set to {value}, sir."


@register("memory", "list_memory")
def list_memory() -> str:
    """List all stored facts and contacts."""
    sections = []

    # User name
    if _memory["user"]["name"]:
        sections.append(f"Your name: {_memory['user']['name']}")

    # Preferences
    prefs = _memory["user"]["preferences"]
    if prefs:
        pref_lines = [f"  - {k}: {v}" for k, v in prefs.items()]
        sections.append("Preferences:\n" + "\n".join(pref_lines))

    # Facts
    facts = _memory["facts"]
    if facts:
        fact_lines = [f"  - {f['key']}: {f['value']}" for f in facts]
        sections.append(f"Facts ({len(facts)}):\n" + "\n".join(fact_lines))

    # Contacts
    contacts = _memory["contacts"]
    if contacts:
        contact_lines = []
        for name, info in contacts.items():
            details = []
            if "number" in info:
                details.append(info["number"])
            if "email" in info:
                details.append(info["email"])
            contact_lines.append(f"  - {name.title()}: {', '.join(details)}")
        sections.append(f"Contacts ({len(contacts)}):\n" + "\n".join(contact_lines))

    if not sections:
        return "My memory is empty, sir. I haven't stored anything yet."

    return "Here's everything I remember, sir:\n\n" + "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Routines (category="routine")
# ---------------------------------------------------------------------------

@register("routine", "create")
def create_routine(name: str, commands: str = "") -> str:
    """Create a named routine (list of commands). Commands are comma-separated."""
    name = name.strip().lower()
    if not name:
        return "What should I call this routine, sir?"
    if not commands:
        return f"What commands should the '{name}' routine include? Please list them separated by commas."

    command_list = [cmd.strip() for cmd in commands.split(",") if cmd.strip()]
    if not command_list:
        return "I didn't get any valid commands. Please try again."

    _memory["routines"][name] = command_list
    _save_memory(_memory)
    logger.info(f"Created routine '{name}' with {len(command_list)} commands")
    return (
        f"Routine '{name}' created with {len(command_list)} commands, sir:\n"
        + "\n".join(f"  {i+1}. {cmd}" for i, cmd in enumerate(command_list))
    )


@register("routine", "run")
def run_routine(name: str) -> str:
    """Run a stored routine — execute each command in sequence."""
    name = name.strip().lower()
    if not name:
        return "Which routine would you like me to run, sir?"

    command_list = _memory["routines"].get(name)
    if not command_list:
        available = ", ".join(_memory["routines"].keys()) if _memory["routines"] else "none"
        return f"I don't have a routine called '{name}', sir. Available routines: {available}."

    # Import here to avoid circular imports
    from core.command_parser import parse_command
    from core.command_router import route_command

    results = []
    logger.info(f"Running routine '{name}' with {len(command_list)} commands")
    for i, cmd in enumerate(command_list, 1):
        try:
            parsed = parse_command(cmd)
            result = route_command(parsed)
            results.append(f"{i}. {cmd}: {result}")
            logger.info(f"Routine '{name}' step {i} done: {cmd}")
        except Exception as e:
            results.append(f"{i}. {cmd}: Error — {e}")
            logger.error(f"Routine '{name}' step {i} failed: {e}")

    return f"Routine '{name}' complete, sir.\n" + "\n".join(results)


@register("routine", "list")
def list_routines() -> str:
    """List all saved routines."""
    routines = _memory["routines"]
    if not routines:
        return "You don't have any routines saved yet, sir."

    lines = []
    for name, commands in routines.items():
        cmd_summary = ", ".join(commands)
        lines.append(f"  - {name}: {cmd_summary}")
    return f"Your routines ({len(routines)}):\n" + "\n".join(lines)


@register("routine", "delete")
def delete_routine(name: str) -> str:
    """Delete a routine."""
    name = name.strip().lower()
    if not name:
        return "Which routine should I delete, sir?"

    if name not in _memory["routines"]:
        return f"I don't have a routine called '{name}', sir."

    del _memory["routines"][name]
    _save_memory(_memory)
    logger.info(f"Deleted routine '{name}'")
    return f"Routine '{name}' has been deleted, sir."


# ---------------------------------------------------------------------------
# Learning helpers (NOT registered as command handlers)
# ---------------------------------------------------------------------------

def log_command(user_input: str, parsed_category: str, parsed_action: str) -> None:
    """Log a command to history. Keeps the last 100 entries. Called by main.py."""
    entry = {
        "input": user_input,
        "category": parsed_category,
        "action": parsed_action,
    }
    _memory["command_history"].append(entry)
    # Keep only the last 100
    _memory["command_history"] = _memory["command_history"][-100:]
    _save_memory(_memory)


def get_contact_number(name: str) -> str | None:
    """Look up a contact by nickname and return the number or email.

    Used by phone.py to resolve names like 'mom' to actual phone numbers.
    Returns the number if available, otherwise the email, or None.
    """
    name = name.strip().lower()
    contact = _memory["contacts"].get(name)
    if not contact:
        # Try partial match
        for stored_name, info in _memory["contacts"].items():
            if name in stored_name:
                contact = info
                break
    if not contact:
        return None
    return contact.get("number") or contact.get("email")
