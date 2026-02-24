# Jarvis - AI Personal Assistant

A voice-activated personal assistant inspired by Iron Man's Jarvis. Built with Python, powered by LLMs, with **72 commands** covering full system control, phone calls, iMessages, email, calendar, notes, reminders, Spotify, desktop automation, web automation, and natural conversation.

## Features

- **Voice Activation** — Say "Jarvis" to wake, then speak your command
- **Conversational AI** — Ask anything, multi-turn conversations with session memory
- **Full System Control** — Volume, brightness, dark mode, Wi-Fi, Bluetooth, lock, sleep, restart, shutdown
- **Spotify Control** — Play, pause, skip, search songs, see what's playing
- **Desktop Automation** — Open/close apps, type text, take screenshots, click coordinates
- **Web Automation** — Google searches, open URLs via Selenium-controlled Chrome
- **Web Scraping** — Weather, news headlines, stock prices, scrape any webpage
- **Phone Calls & Messages** — Make calls via iPhone Continuity, FaceTime, send/read iMessages
- **Calendar, Reminders & Notes** — Read/create calendar events, reminders, and notes
- **Email** — Send and read emails via Gmail
- **Timers & Math** — Set voice-alert timers, calculate expressions
- **Reading** — Read emails, files, selected text, notes aloud
- **Clipboard & Notifications** — Read/write clipboard, send macOS notifications
- **Shell Commands** — Run any terminal command by voice
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

Edit `.env` and add your keys (at least one LLM key required):

```
GOOGLE_API_KEY=your-gemini-key      # Free: https://aistudio.google.com/apikey
GROQ_API_KEY=your-groq-key          # Free: https://console.groq.com/keys
ANTHROPIC_API_KEY=your-claude-key    # Paid: https://console.anthropic.com/settings/keys

# Optional — for email
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password  # https://myaccount.google.com/apppasswords
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

## All 72 Commands

### Spotify
| Command | What it does |
|---|---|
| "play music" / "play Spotify" | Play/resume |
| "pause" / "pause music" | Pause playback |
| "next song" / "skip" | Next track |
| "previous song" | Previous track |
| "what's playing" / "current song" | Show current track info |
| "play Drake" / "play Bohemian Rhapsody" | Search and play a song/artist |

### Volume & Brightness
| Command | What it does |
|---|---|
| "volume up" | Increase by 15% |
| "volume down" | Decrease by 15% |
| "set volume to 50" | Set specific level (0-100) |
| "mute" / "unmute" | Mute/unmute audio |
| "what's the volume" | Current volume level |
| "brightness up" / "brightness down" | Adjust screen brightness |

### System Control
| Command | What it does |
|---|---|
| "lock my computer" | Lock screen |
| "go to sleep" | Sleep the Mac |
| "restart" / "shut down" | Restart or power off |
| "turn on dark mode" / "turn off dark mode" | Dark mode control |
| "toggle dark mode" | Switch dark/light |
| "turn on wifi" / "turn off wifi" | Wi-Fi toggle |
| "turn on bluetooth" / "turn off bluetooth" | Bluetooth toggle |
| "do not disturb on" / "off" | Focus mode toggle |
| "empty the trash" | Empty Trash |
| "show desktop" | Minimize all windows |
| "open Downloads folder" | Open folder in Finder |

### System Info
| Command | What it does |
|---|---|
| "what's my battery" | Battery level & charging status |
| "what wifi am I on" | Current Wi-Fi network |
| "what's my IP address" | Local and public IP |
| "how much disk space" | Free/total disk space |
| "what time is it" | Current time |
| "what's the date" | Current date |

### Desktop Automation
| Command | What it does |
|---|---|
| "open Safari" / "open Chrome" | Launch an app |
| "open Teams" / "open VS Code" | Smart aliases for full app names |
| "close Teams" | Quit an app |
| "type 'hello world'" | Type text at cursor |
| "take a screenshot" | Save to `screenshots/` folder |
| "click 500, 300" | Click at screen coordinates |

### Web Automation & Scraping
| Command | What it does |
|---|---|
| "search for Python tutorials" | Google search, top 5 results |
| "open github.com" | Open URL in Chrome |
| "weather in London" | Current weather |
| "news about technology" | Top 5 headlines |
| "price of AAPL" | Stock price |
| "scrape https://example.com" | Extract page text |

### Timers & Math
| Command | What it does |
|---|---|
| "set a timer for 5 minutes" | Voice alert when done |
| "set a timer for 1 hour" | Longer timers work too |
| "cancel timer" | Cancel active timer |
| "what's 25 times 48" | Math calculations |
| "calculate 100 divided by 3" | Supports +, -, *, /, ^, sqrt |

### Clipboard & Notifications
| Command | What it does |
|---|---|
| "what's on my clipboard" | Read clipboard contents |
| "copy hello world to clipboard" | Write to clipboard |
| "send a notification saying meeting in 5 minutes" | macOS notification |

### Phone Calls & Messages
| Command | What it does |
|---|---|
| "call 0712345678" | Make a phone call (via iPhone Continuity) |
| "FaceTime John" | FaceTime video call |
| "FaceTime audio mom" | FaceTime audio call |
| "send a message to John saying I'm on my way" | Send iMessage/SMS |
| "read my messages" | Read recent iMessages |
| "read messages from John" | Read messages from a specific contact |

### Email
| Command | What it does |
|---|---|
| "send email to john@gmail.com about meeting" | Send via Gmail SMTP |
| "check my emails" / "read my emails" | Read latest 5 inbox emails |
| "read the first email" | Read full content of most recent email |

### Calendar, Reminders & Notes
| Command | What it does |
|---|---|
| "what's on my calendar" | Today's calendar events |
| "what's on my calendar this week" | Next 7 days of events |
| "add a meeting on March 1st at 2pm" | Create a calendar event |
| "read my reminders" | List pending reminders |
| "remind me to buy groceries" | Add a new reminder |
| "read my notes" | List recent notes |
| "create a note called Ideas" | Create a new note |

### Reading
| Command | What it does |
|---|---|
| "read what's selected" | Read highlighted text on screen aloud |
| "read the file /path/to/file.txt" | Read a text file aloud |

### Conversation
| Command | What it does |
|---|---|
| "how intelligent are you?" | Chat about anything |
| "tell me a joke" | Jarvis responds in character |
| "create a business plan" | Multi-turn with memory |
| "goodbye" | Shut down Jarvis |

### Shell (Power User)
| Command | What it does |
|---|---|
| "run command ls" | Execute any terminal command |

## Project Structure

```
jarvis/
├── main.py                    # Entry point — wake word, voice, text modes
├── config.py                  # All settings & environment variables
├── jarvis.sh                  # Shell launcher script
├── requirements.txt
├── .env.example
├── core/
│   ├── command_parser.py      # LLM-powered NL → structured commands (72 actions)
│   ├── command_router.py      # @register decorator, dispatches to modules
│   ├── voice_input.py         # Speech-to-text with wake word detection
│   └── voice_output.py        # Text-to-speech (Daniel British male voice)
├── modules/
│   ├── chat.py                # Conversational AI with session memory
│   ├── desktop_automation.py  # Open/close apps, type, screenshot, click
│   ├── web_automation.py      # Selenium — Google search, URL navigation
│   ├── web_scraper.py         # BeautifulSoup — weather, news, stocks
│   ├── system_commands.py     # Time, date, battery, wifi, IP, disk, brightness
│   ├── system_control.py      # Lock, sleep, restart, dark mode, wifi/BT toggle,
│   │                          # trash, clipboard, notifications, DND, shell commands
│   ├── volume_control.py      # Volume up/down/mute/set
│   ├── spotify_control.py     # Play/pause/next/previous/current/search
│   ├── timer.py               # Set/cancel voice-alert timers
│   ├── calculator.py          # Safe math expression evaluation
│   ├── email_sender.py        # Send emails via Gmail SMTP
│   ├── phone.py               # Phone calls, FaceTime, iMessages
│   └── reader.py              # Read emails, files, calendar, reminders, notes
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
command_router.py  →  Looks up handler by (category, action) from 72 registered handlers
    ↓
Module handler     →  Executes action, returns result string
    ↓
voice_output.py    →  Speaks result aloud (Daniel voice) + prints to console
```

## macOS Permissions

On first run, macOS will ask for:
- **Microphone** — System Settings → Privacy & Security → Microphone → allow Terminal/VS Code
- **Accessibility** — System Settings → Privacy & Security → Accessibility → allow Terminal/VS Code (needed for PyAutoGUI)
- **Contacts, Calendar, Reminders, Notes** — Allow access when prompted (needed for PIM features)
- **Phone Calls** — Requires iPhone on same iCloud account with "Calls on Other Devices" enabled in iPhone Settings → Phone

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
