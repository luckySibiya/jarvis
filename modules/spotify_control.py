"""Spotify playback control using macOS osascript."""

import subprocess

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)


def _spotify_command(action: str) -> str:
    """Send a command to Spotify via AppleScript."""
    result = subprocess.run(
        ["osascript", "-e", f'tell application "Spotify" to {action}'],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip()


def _is_spotify_running() -> bool:
    """Check if Spotify is currently running."""
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to '
         '(name of processes) contains "Spotify"'],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip() == "true"


@register("spotify", "play")
def spotify_play() -> str:
    """Play or resume Spotify."""
    if not _is_spotify_running():
        subprocess.Popen(["open", "-a", "Spotify"])
        import time
        time.sleep(2)
    _spotify_command("play")
    return "Playing Spotify."


@register("spotify", "pause")
def spotify_pause() -> str:
    """Pause Spotify."""
    _spotify_command("pause")
    return "Spotify paused."


@register("spotify", "next")
def spotify_next() -> str:
    """Skip to next track."""
    _spotify_command("next track")
    import time
    time.sleep(0.5)
    name = _spotify_command("name of current track")
    artist = _spotify_command("artist of current track")
    return f"Next track: {name} by {artist}."


@register("spotify", "previous")
def spotify_previous() -> str:
    """Go to previous track."""
    _spotify_command("previous track")
    import time
    time.sleep(0.5)
    name = _spotify_command("name of current track")
    artist = _spotify_command("artist of current track")
    return f"Previous track: {name} by {artist}."


@register("spotify", "current")
def spotify_current() -> str:
    """Get currently playing track info."""
    if not _is_spotify_running():
        return "Spotify is not running."
    try:
        name = _spotify_command("name of current track")
        artist = _spotify_command("artist of current track")
        album = _spotify_command("album of current track")
        if not name:
            return "Nothing is currently playing on Spotify."
        return f"Now playing: {name} by {artist}, from the album {album}."
    except Exception:
        return "Nothing is currently playing on Spotify."


@register("spotify", "play_search")
def spotify_play_search(query: str) -> str:
    """Search and play a song/artist/playlist on Spotify.

    Uses Spotify URI search to play directly.
    """
    # Spotify supports spotify:search: URI for quick play
    search_uri = f"spotify:search:{query}"
    subprocess.run(
        ["open", search_uri],
        capture_output=True, text=True, timeout=5,
    )
    return f"Searching Spotify for '{query}'."
