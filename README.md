# Jarvis Personal Assistant

A voice-controlled personal assistant for Windows. Always listens in the
background for the wake word "jarvis", then launches the full assistant
to handle your command.

## Features

- Wake word activation ("jarvis") via an always-on background listener
- Voice input (speech-to-text) and spoken responses (text-to-speech)
- Interruptible speech
- Open and close apps by voice
- Web search
- PC control: shutdown, restart, lock
- Live weather (Open-Meteo, no API key required)
- Live news by category or topic (Google News RSS, no API key required)
- Google Calendar integration (read today's events)
- Persistent memory stored in a local SQLite database
- Vision: describe your screen or webcam using a vision-language model
- General conversation fallback powered by Groq

## Project Structure

- `listener.py` - lightweight, always-on wake word listener. Run this.
- `jarvis.py` - the full assistant, launched automatically by the listener.
- `vision.py` - screen/webcam capture and vision-language model calls.
- `run_listener.bat` - launches the listener, for use with Windows startup.
- `jarvis_memory.db` - created automatically, stores remembered facts.

## Installation

```
pip install -r requirements.txt
```

If `pyaudio` fails to install on Windows:

```
pip install pipwin
pipwin install pyaudio
```

## Configuration

Create a `.env` file in the project folder:

```
GROQ_API_KEY=your-groq-key-here
HF_TOKEN=your-huggingface-token-here
WEATHER_LAT=12.9716
WEATHER_LON=77.5946
```

`WEATHER_LAT` and `WEATHER_LON` are optional and default to Bengaluru.

### Google Calendar setup (optional)

1. Go to https://console.cloud.google.com/
2. Create a project and enable the Google Calendar API
3. Create OAuth Client ID credentials (type: Desktop app)
4. Download the JSON and save it as `credentials.json` in the project folder
5. The first calendar request will open a browser to sign in once; after
   that, a `token.json` is cached and reused automatically

If this isn't set up, calendar commands simply say so and everything else
keeps working.

## Running

Start the always-on listener:

```
python listener.py
```

Say "jarvis" any time. The full assistant will start, listen for your
command, and go back to sleep after a short period of silence, handing
control back to the listener.

To start the listener automatically at login:

1. Edit `run_listener.bat` so its path points to your project folder
2. Press `Win+R`, type `shell:startup`, press Enter
3. Place a shortcut to `run_listener.bat` in that folder

## Example Commands

- "jarvis open notepad"
- "jarvis close chrome"
- "jarvis search for python tutorials"
- "jarvis what's the weather"
- "jarvis sports news"
- "jarvis news about elections"
- "jarvis what time is it"
- "jarvis what's on my schedule"
- "jarvis remember that my dog's name is max"
- "jarvis what do you remember"
- "jarvis what's on my screen"
- "jarvis describe the webcam"
- "jarvis lock my pc"

## Notes

- Speech recognition uses Google's free web API and requires an internet
  connection even though no API key is needed for it.
- The vision model is called through Hugging Face's inference router and
  may occasionally be slow or rate-limited depending on provider load.
- App open/close commands rely on the `APPS` and `CLOSE_NAMES` dictionaries
  at the top of `jarvis.py` - add your own installed apps there.