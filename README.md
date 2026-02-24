# Jarvis - AI Personal Assistant

A voice-activated personal assistant inspired by Iron Man's Jarvis. Built with Python, powered by LLMs (Groq/Gemini/Anthropic), with desktop automation, web automation, web scraping, and natural conversation abilities.

## Features

- **Voice Activation** — Say "Jarvis" to wake, then speak your command
- **Conversational AI** — Ask anything, get intelligent responses with session memory
- **Desktop Automation** — Open/close apps, type text, take screenshots, click coordinates
- **Web Automation** — Google searches, open URLs via Selenium-controlled Chrome
- **Web Scraping** — Weather, news headlines, stock prices, scrape any webpage
- **British Male Voice** — Daniel (UK English) text-to-speech for the authentic Jarvis feel
- **Multi-LLM Fallback** — Gemini (free) → Groq (free) → Anthropic (paid), auto-switches on failure

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/luckySibiya/jarvis.git
cd jarvis

# Install system dependency (macOS — needed for microphone)
brew install portaudio

# Create virtual environment & install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Add API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys (at least one required):

```
GOOGLE_API_KEY=your-gemini-key      # Free: https://aistudio.google.com/apikey
GROQ_API_KEY=your-groq-key          # Free: https://console.groq.com/keys
ANTHROPIC_API_KEY=your-claude-key    # Paid: https://console.anthropic.com/settings/keys
```

### 3. Run Jarvis

```bash
# Wake word mode (default) — say "Jarvis" to activate
python main.py

# Text mode — type commands
python main.py --mode text

# Voice mode — always listening, no wake word needed
python main.py --mode voice
```

## Commands

### Desktop Control
| Command | What it does |
|---|---|
| "open Safari" | Launch an app |
| "open Chrome" / "open Teams" | Smart aliases for full app names |
| "close Teams" | Quit an app |
| "type 'hello world'" | Type text at cursor |
| "take a screenshot" | Save to `screenshots/` folder |
| "click 500, 300" | Click at screen coordinates |

### Web Automation
| Command | What it does |
|---|---|
| "search for Python tutorials" | Google search, returns top 5 results |
| "open github.com" | Open URL in Chrome |

### Information
| Command | What it does |
|---|---|
| "weather in London" | Current weather from wttr.in |
| "news about technology" | Top 5 Google News headlines |
| "price of AAPL" | Stock price from Yahoo Finance |
| "scrape https://example.com" | Extract text from any webpage |
| "what time is it" | Current time |
| "what's the date" | Current date |

### Conversation
| Command | What it does |
|---|---|
| "how intelligent are you?" | Chat with Jarvis about anything |
| "tell me a joke" | Jarvis responds in character |
| "create a business plan" | Multi-turn conversations with memory |
| "goodbye" | Shut down |

## Project Structure

```
jarvis/
├── main.py                    # Entry point — wake word, voice, text modes
├── config.py                  # All settings & environment variables
├── jarvis.sh                  # Shell launcher script
├── requirements.txt
├── .env.example
├── core/
│   ├── command_parser.py      # LLM-powered natural language → structured commands
│   ├── command_router.py      # @register decorator pattern, dispatches to modules
│   ├── voice_input.py         # Speech-to-text (SpeechRecognition + Google API)
│   └── voice_output.py        # Text-to-speech (pyttsx3, Daniel voice)
├── modules/
│   ├── chat.py                # Conversational AI with session memory
│   ├── desktop_automation.py  # PyAutoGUI — open/close apps, type, screenshot
│   ├── web_automation.py      # Selenium — Google search, URL navigation
│   ├── web_scraper.py         # BeautifulSoup — weather, news, stocks
│   └── system_commands.py     # Time, date
└── utils/
    ├── logger.py              # Centralized logging
    └── helpers.py             # Shared utilities
```

## Architecture

```
User speaks/types
    ↓
command_parser.py  →  LLM classifies intent → Command(category, action, args)
    ↓
command_router.py  →  Looks up handler by (category, action)
    ↓
Module handler     →  Executes action, returns result string
    ↓
voice_output.py    →  Speaks result aloud (Daniel voice) + prints to console
```

## macOS Permissions

On first run, macOS will ask for:
- **Microphone** — System Settings → Privacy & Security → Microphone → allow Terminal/VS Code
- **Accessibility** — System Settings → Privacy & Security → Accessibility → allow Terminal/VS Code (needed for PyAutoGUI)

## Shell Alias (Optional)

Add to `~/.zshrc` to run Jarvis from anywhere:

```bash
alias jarvis="/path/to/jarvis/jarvis.sh"
```

Then just type `jarvis` in any terminal.

## Tech Stack

- **Python 3.13+**
- **SpeechRecognition + PyAudio** — microphone input
- **pyttsx3** — offline text-to-speech
- **PyAutoGUI** — desktop automation
- **Selenium + webdriver-manager** — browser automation
- **BeautifulSoup4 + requests** — web scraping
- **Groq / Google Gemini / Anthropic** — LLM APIs for command parsing & chat

## License

MIT
