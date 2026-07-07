"""
jarvis.py  (v2)

Personal voice assistant with:
- Wake word ("jarvis") - always listening, only acts when it hears its name
- Voice commands: open/close apps, web search, PC control
- Weather (Open-Meteo, free, no key)
- Time / date
- Google Calendar integration (read today's events)
- Persistent memory (SQLite) - remembers facts across runs
- Interruptible speech (say anything while it's talking to cut it off)
- Better TTS voice via edge-tts + pygame playback

============================================================
INSTALL
============================================================
pip install groq python-dotenv SpeechRecognition pyaudio edge-tts pygame requests google-auth-oauthlib google-api-python-client

If pyaudio fails on Windows:
    pip install pipwin
    pipwin install pyaudio

============================================================
.env file (same folder) needs:
============================================================
GROQ_API_KEY=your-key-here

Optional, for weather - set your city's lat/long (defaults to Bengaluru):
WEATHER_LAT=12.9716
WEATHER_LON=77.5946

============================================================
GOOGLE CALENDAR SETUP (one-time, optional - skip if you don't need it)
============================================================
1. Go to https://console.cloud.google.com/
2. Create a project -> Enable "Google Calendar API"
3. Create OAuth Client ID credentials (type: Desktop app)
4. Download the JSON, save it as credentials.json in this folder
5. First run will open a browser to log in once; after that it's cached
   in token.json and works automatically.

If you skip this, calendar commands will just tell you it's not set up.

============================================================
RUN
============================================================
python jarvis.py
"""

import os
import re
import sqlite3
import subprocess
import threading
import webbrowser
from datetime import datetime, date

from dotenv import load_dotenv
load_dotenv()

import requests
import speech_recognition as sr
import asyncio
import edge_tts
import pygame
from groq import Groq

# ---------- Config ----------

GROQ_MODEL = "llama-3.1-8b-instant"
VOICE = "en-US-GuyNeural"          # try "en-GB-RyanNeural" or "en-US-JennyNeural" too
WAKE_WORD = "jarvis"
WEATHER_LAT = os.getenv("WEATHER_LAT", "12.9716")
WEATHER_LON = os.getenv("WEATHER_LON", "77.5946")

client = Groq()
recognizer = sr.Recognizer()
mic = sr.Microphone()

pygame.mixer.init()

# interrupt flag shared between speaking thread and listener thread
stop_speaking = threading.Event()


# ---------- Memory (SQLite) ----------

class Memory:
    def __init__(self, db="jarvis_memory.db"):
        self.conn = sqlite3.connect(db, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def remember(self, key, value):
        self.cur.execute(
            "INSERT INTO facts (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        self.conn.commit()

    def recall(self, key):
        self.cur.execute("SELECT value FROM facts WHERE key = ?", (key,))
        row = self.cur.fetchone()
        return row[0] if row else None

    def all_facts(self):
        self.cur.execute("SELECT key, value FROM facts")
        return self.cur.fetchall()


memory = Memory()


# ---------- TTS (edge-tts + pygame, interruptible) ----------

async def _generate_speech(text, path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


def speak(text):
    print("Jarvis:", text)
    stop_speaking.clear()

    path = f"reply_{threading.get_ident()}.mp3"
    asyncio.run(_generate_speech(text, path))

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        if stop_speaking.is_set():
            pygame.mixer.music.stop()
            break
        pygame.time.wait(100)

    pygame.mixer.music.unload()  # release the file lock
    try:
        os.remove(path)
    except OSError:
        pass


def speak_async(text):
    """Speak in a background thread so we can interrupt it."""
    t = threading.Thread(target=speak, args=(text,))
    t.start()
    return t


# ---------- Speech recognition ----------

def listen(timeout=5, phrase_time_limit=8):
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        except sr.WaitTimeoutError:
            return ""

    try:
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""


# ---------- App shortcuts ----------

APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": "chrome.exe",
    "vscode": "code",
    "vs code": "code",
    "explorer": "explorer.exe",
    "spotify": "spotify.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
}

# process names used for closing (task image names, not launch commands)
CLOSE_NAMES = {
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "chrome": "chrome.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "spotify": "Spotify.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
}


def open_app(command):
    for key, cmd in APPS.items():
        if key in command:
            try:
                subprocess.Popen(cmd, shell=True)
                return f"Opening {key}."
            except Exception:
                return f"I couldn't open {key}."
    return "I don't know that app. Add it to the APPS dict in jarvis.py."


def close_app(command):
    for key, proc in CLOSE_NAMES.items():
        if key in command:
            result = subprocess.run(
                ["taskkill", "/IM", proc, "/F"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return f"Closed {key}."
            return f"{key} doesn't seem to be running."
    return "I don't know that app. Add it to the CLOSE_NAMES dict in jarvis.py."


# ---------- PC control ----------

def control_pc(command):
    if "shutdown" in command:
        speak("Shutting down in 10 seconds. Say cancel shutdown to stop.")
        os.system("shutdown /s /t 10")
        return True
    if "cancel shutdown" in command:
        os.system("shutdown /a")
        speak("Shutdown cancelled.")
        return True
    if "restart" in command:
        speak("Restarting in 10 seconds.")
        os.system("shutdown /r /t 10")
        return True
    if "lock" in command:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        speak("Locking your PC.")
        return True
    return False


# ---------- Web search ----------

def web_search(command):
    query = re.sub(r"(search for|search|google|look up)", "", command).strip()
    if not query:
        return "What do you want me to search for?"
    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
    return f"Searching the web for {query}."


# ---------- Weather (Open-Meteo, free, no key) ----------

def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
            f"&current=temperature_2m,weather_code,wind_speed_10m"
        )
        data = requests.get(url, timeout=8).json()
        current = data["current"]
        temp = current["temperature_2m"]
        wind = current["wind_speed_10m"]

        code = current["weather_code"]
        conditions = {
            0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 48: "foggy", 51: "light drizzle", 61: "light rain",
            63: "rain", 65: "heavy rain", 71: "light snow", 80: "rain showers",
            95: "thunderstorms",
        }
        desc = conditions.get(code, "some weather")

        return f"It's currently {temp} degrees celsius with {desc}, wind at {wind} km/h."
    except Exception:
        return "I couldn't fetch the weather right now."


# ---------- News (Google News RSS, free, no key needed) ----------

NEWS_CATEGORIES = {
    "sports": "sports",
    "sport": "sports",
    "technology": "technology",
    "tech": "technology",
    "business": "business",
    "finance": "business",
    "science": "science",
    "health": "health",
    "entertainment": "entertainment",
    "world": "world",
    "politics": "world",
    "india": "india",
}


def get_news(command):
    import feedparser
    from urllib.parse import quote

    # figure out what kind of news they want
    topic = None
    for word, category in NEWS_CATEGORIES.items():
        if word in command:
            topic = category
            break

    # also support "news about X" / "news on X" for arbitrary topics
    match = re.search(r"news (?:about|on|for) (.+)", command)
    custom_topic = match.group(1).strip() if match else None

    if custom_topic:
        query = custom_topic
        spoken_topic = custom_topic
    elif topic:
        query = topic
        spoken_topic = topic
    else:
        query = "top stories"
        spoken_topic = "today"

    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"

    try:
        feed = feedparser.parse(url)

        if not feed.entries:
            return f"I couldn't find any news on {spoken_topic} right now."

        headlines = [entry.title for entry in feed.entries[:5]]

        response = f"Here's the latest on {spoken_topic}: "
        for i, headline in enumerate(headlines, 1):
            # Google News titles often end with " - SourceName", trim that for speech
            clean = re.sub(r"\s*-\s*[^-]+$", "", headline)
            response += f"{clean}. "

        return response

    except Exception:
        return f"I had trouble reaching the news for {spoken_topic}. Check your internet connection."


# ---------- Time / date ----------

def get_time():
    return datetime.now().strftime("It's %I:%M %p right now.")


def get_date():
    return datetime.now().strftime("Today is %A, %B %d, %Y.")


# ---------- Google Calendar ----------

def get_calendar_events():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return "Calendar libraries aren't installed. Run: pip install google-auth-oauthlib google-api-python-client"

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                return (
                    "Calendar isn't set up yet. Follow the setup steps in the "
                    "jarvis.py file header to connect Google Calendar."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as f:
            f.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        end_of_day = datetime.combine(date.today(), datetime.max.time()).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary", timeMin=now, timeMax=end_of_day,
            singleEvents=True, orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            return "You have no events scheduled for the rest of today."

        summary = "Here's what's on your schedule: "
        for event in events[:5]:
            start = event["start"].get("dateTime", event["start"].get("date"))
            try:
                time_str = datetime.fromisoformat(start).strftime("%I:%M %p")
            except Exception:
                time_str = "all day"
            summary += f"{event.get('summary', 'Untitled event')} at {time_str}. "

        return summary
    except Exception as e:
        return f"I couldn't reach your calendar: {e}"


# ---------- Persistent memory commands ----------

def handle_memory(command):
    # "remember that my dog's name is max"
    match = re.search(r"remember that (.+)", command)
    if match:
        fact = match.group(1).strip()
        key = fact[:40]
        memory.remember(key, fact)
        return "Got it, I'll remember that."

    if "what do you remember" in command or "what do you know about me" in command:
        facts = memory.all_facts()
        if not facts:
            return "I don't have anything stored yet."
        return "Here's what I remember: " + "; ".join(v for _, v in facts)

    return None


# ---------- LLM fallback ----------

history = [
    {
        "role": "system",
        "content": (
            "You are Jarvis, a concise personal voice assistant. "
            "Keep answers short and conversational since they will be "
            "read aloud. Never use markdown formatting like asterisks."
        ),
    }
]


def ask_llm(text):
    history.append({"role": "user", "content": text})
    response = client.chat.completions.create(model=GROQ_MODEL, messages=history)
    reply = response.choices[0].message.content
    reply = re.sub(r"\*\*(.*?)\*\*", r"\1", reply)
    reply = re.sub(r"\*(.*?)\*", r"\1", reply)
    history.append({"role": "assistant", "content": reply})
    return reply


# ---------- Command router ----------

def handle_command(command):
    if not command:
        return

    if command in ["quit", "exit", "stop", "goodbye", "shut down jarvis"]:
        speak("Goodbye.")
        raise SystemExit

    if "open" in command:
        speak(open_app(command)); return

    if "close" in command:
        speak(close_app(command)); return

    if any(w in command for w in ["search", "google", "look up"]):
        speak(web_search(command)); return

    if control_pc(command):
        return

    if "weather" in command:
        speak(get_weather()); return

    if "time" in command:
        speak(get_time()); return

    if "date" in command or "day is it" in command:
        speak(get_date()); return

    if "schedule" in command or "calendar" in command or "events" in command:
        speak(get_calendar_events()); return

    memory_reply = handle_memory(command)
    if memory_reply:
        speak(memory_reply); return

    speak(ask_llm(command))


# ---------- Main loop with wake word + interrupt ----------

def strip_wake_word(text):
    return text.replace(WAKE_WORD, "").strip()


if __name__ == "__main__":
    speak("Yes? How can I help?")

    IDLE_TIMEOUT_CYCLES = 3  # how many silent listens before Jarvis goes back to sleep

    silent_count = 0

    while True:
        try:
            command = listen(timeout=8, phrase_time_limit=8)

            if not command:
                silent_count += 1
                if silent_count >= IDLE_TIMEOUT_CYCLES:
                    print("[jarvis] No activity, going back to sleep.")
                    break
                continue

            silent_count = 0
            command = strip_wake_word(command)
            handle_command(command)

        except SystemExit:
            break
        except KeyboardInterrupt:
            speak("Shutting down.")
            break