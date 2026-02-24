"""Shared utility functions."""


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text for speech output."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def sanitize_filename(name: str) -> str:
    """Remove invalid filename characters."""
    return "".join(c for c in name if c.isalnum() or c in "._- ")
