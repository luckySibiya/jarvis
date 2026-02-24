"""Route parsed commands to the appropriate module handler."""

from core.command_parser import Command
from utils.logger import get_logger

logger = get_logger(__name__)

# Registry: maps (category, action) -> handler function
HANDLERS: dict[tuple[str, str], callable] = {}

# Pending follow-up: when a handler needs more info from the user
_pending: dict | None = None


def register(category: str, action: str):
    """Decorator to register a command handler."""
    def decorator(func):
        HANDLERS[(category, action)] = func
        return func
    return decorator


def set_pending(category: str, action: str, needs: str, args: dict | None = None):
    """Store a pending action that needs one more piece of info from the user.

    Args:
        category: Handler category (e.g. "phone")
        action: Handler action (e.g. "call")
        needs: The arg name to fill with the user's next input (e.g. "number")
        args: Any args already collected
    """
    global _pending
    _pending = {
        "category": category,
        "action": action,
        "needs": needs,
        "args": args or {},
    }
    logger.info(f"Pending action set: {category}.{action} needs '{needs}'")


def consume_pending(user_input: str) -> str | None:
    """Check for a pending follow-up action. If one exists, fill in the missing
    arg with user_input, execute the handler, and return the result.
    Returns None if no pending action.
    """
    global _pending
    if _pending is None:
        return None

    pending = _pending
    _pending = None

    handler = HANDLERS.get((pending["category"], pending["action"]))
    if not handler:
        return None

    # Fill in the missing argument
    pending["args"][pending["needs"]] = user_input.strip()
    logger.info(
        f"Resuming {pending['category']}.{pending['action']} "
        f"with {pending['needs']}='{user_input.strip()}'"
    )
    return handler(**pending["args"])


_loaded = False


def _load_handlers():
    """Import all modules to trigger @register decorators."""
    global _loaded
    if _loaded:
        return
    import modules.web_automation       # noqa: F401
    import modules.desktop_automation   # noqa: F401
    import modules.web_scraper          # noqa: F401
    import modules.system_commands      # noqa: F401
    import modules.system_control       # noqa: F401
    import modules.volume_control       # noqa: F401
    import modules.spotify_control      # noqa: F401
    import modules.timer                # noqa: F401
    import modules.calculator           # noqa: F401
    import modules.email_sender         # noqa: F401
    import modules.phone                # noqa: F401
    import modules.reader               # noqa: F401
    import modules.chat                 # noqa: F401
    _loaded = True


def route_command(command: Command) -> str:
    """Route a command to its handler. Returns a response string."""
    _load_handlers()

    handler = HANDLERS.get((command.category, command.action))
    if handler:
        logger.info(f"Routing to {handler.__name__}")
        return handler(**command.args)

    # Unknown commands go to chat — Jarvis can talk about anything
    chat_handler = HANDLERS.get(("chat", "chat"))
    if chat_handler:
        logger.info("Unknown command, routing to chat")
        return chat_handler(message=command.raw_input)

    return f"I don't know how to do that yet. You said: '{command.raw_input}'"
