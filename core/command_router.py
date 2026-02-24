"""Route parsed commands to the appropriate module handler."""

from core.command_parser import Command
from utils.logger import get_logger

logger = get_logger(__name__)

# Registry: maps (category, action) -> handler function
HANDLERS: dict[tuple[str, str], callable] = {}


def register(category: str, action: str):
    """Decorator to register a command handler."""
    def decorator(func):
        HANDLERS[(category, action)] = func
        return func
    return decorator


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
