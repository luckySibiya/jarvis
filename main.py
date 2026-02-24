"""Jarvis Personal Assistant — Entry point."""

import argparse

from core.voice_input import listen, wait_for_wake_word
from core.voice_output import speak
from core.command_parser import parse_command
from core.command_router import route_command, consume_pending
from config import EXIT_COMMANDS
from utils.logger import setup_logger


def handle_command(user_input: str, logger) -> bool:
    """Parse and execute a command. Returns False if Jarvis should shut down."""
    if user_input.lower().strip() in EXIT_COMMANDS:
        speak("Goodbye, sir.")
        return False

    try:
        # Check if there's a pending follow-up (e.g. "who to call?")
        result = consume_pending(user_input)

        if result is None:
            # No pending action — parse as a new command
            command = parse_command(user_input)
            result = route_command(command)

        speak(result)

        # Feed results into chat memory so Jarvis has full context
        from modules.chat import _save_exchange
        _save_exchange(user_input, result)

    except Exception as e:
        logger.error(f"Error: {e}")
        speak(f"Sorry, something went wrong: {e}")

    return True


def run_always_on(logger):
    """Always-on mode: continuously listens for 'Jarvis' wake word."""
    speak("Jarvis online. Just say my name when you need me, sir.")
    print("\n--- Always listening. Say 'Jarvis' to activate. ---\n")

    while True:
        # Phase 1: Wait for wake word (blocks until "Jarvis" is heard)
        command = wait_for_wake_word()

        if command:
            # User said "Jarvis <command>" in one sentence
            print(f"You: {command}")
            if not handle_command(command, logger):
                break
        else:
            # User just said "Jarvis" — prompt for command
            speak("Yes, sir?")
            print("\n🎤 Listening for command...")
            command = listen(timeout=8, phrase_limit=15)
            if command:
                print(f"You: {command}")
                if not handle_command(command, logger):
                    break
            else:
                speak("I didn't catch that.")


def run_voice(logger):
    """Voice-only mode: listen → process → repeat."""
    speak("Jarvis online. How can I help you, sir?")

    while True:
        print("\n🎤 Listening...")
        user_input = listen()
        if user_input is None:
            continue
        print(f"You: {user_input}")
        if not handle_command(user_input, logger):
            break


def run_text(logger):
    """Text-only mode."""
    speak("Jarvis online. How can I help you?")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        if not handle_command(user_input, logger):
            break


def main():
    parser = argparse.ArgumentParser(description="Jarvis Personal Assistant")
    parser.add_argument(
        "--mode",
        choices=["always", "voice", "text"],
        default="always",
        help=(
            "always: wake word 'Jarvis' activates (default), "
            "voice: always listening for commands, "
            "text: type commands"
        ),
    )
    args = parser.parse_args()
    logger = setup_logger()

    if args.mode == "always":
        run_always_on(logger)
    elif args.mode == "voice":
        run_voice(logger)
    else:
        run_text(logger)


if __name__ == "__main__":
    main()
