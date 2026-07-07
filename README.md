# Jarvis Voice Assistant

A lightweight offline-first voice assistant written in Python.

Unlike many assistants that constantly consume system resources, Jarvis uses a tiny background listener that waits for a wake word and only launches the full assistant when needed.

## Features

* Wake word detection (`Jarvis`)
* Lightweight background listener
* Automatically launches the main assistant
* Prevents multiple assistant instances
* Easy to extend with custom commands
* CPU friendly
* Simple project structure

## Project Structure

main
.
├── listener.py          # Always-running wake word listener
├── jarvis.py            # Main assistant
├── run_listener.bat     # Starts listener
├── README.md
├── CHANGELOG.md
└── .gitignore

## Requirements

* Python 3.10+
* Microphone
* Internet connection (Google Speech Recognition)

## Installation

Clone the repository:

```
git clone https://github.com/yourusername/jarvis.git
cd jarvis
```

Install dependencies:

```
pip install SpeechRecognition
pip install pyaudio
```

or

```
pip install -r requirements.txt
```

## Running

Start the background listener:

```
python listener.py
```

or simply double-click:

```
run_listener.bat
```

The listener will remain idle until it hears the wake word.

## Wake Word

Default wake word:

```
Jarvis
```

This can be changed inside `listener.py`:

```
WAKE_WORD = "jarvis"
```

## Automatic Startup

To launch Jarvis whenever Windows starts:

1. Press `Win + R`
2. Type:

```
shell:startup
```

3. Press Enter.
4. Create a shortcut to `run_listener.bat`.
5. The listener will now start automatically after logging in.

## How It Works

```
Microphone
      │
      ▼
listener.py
      │
Wake word detected?
      │
      ▼
Launch jarvis.py
      │
Conversation
      │
Exit
      │
listener.py continues waiting
```

## Dependencies

* SpeechRecognition
* PyAudio

## Future Plans

* Offline speech recognition
* Text-to-speech improvements
* Plugin system
* AI conversation engine
* Local memory
* Smart home integration
* Wake word customization
* Better NLP

## License

This project is released under the MIT License.
