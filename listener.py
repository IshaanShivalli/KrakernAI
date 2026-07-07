"""
listener.py

A tiny, lightweight program meant to run in the background ALL the time
(even when jarvis.py itself isn't running). It just listens for the
word "jarvis" using minimal resources, and when it hears it, launches
the full jarvis.py assistant as a separate process.

Think of this as the "always on" ear, and jarvis.py as the "brain"
that only wakes up when needed.

Install (if not already):
    pip install SpeechRecognition pyaudio

Run this instead of jarvis.py directly:
    python listener.py

To make it start automatically when your PC boots:
    1. Press Win+R, type: shell:startup , press Enter
    2. Create a shortcut to a .bat file (see run_listener.bat below)
       in that folder, so it launches automatically at login.
"""

import subprocess
import sys
import time
import speech_recognition as sr

WAKE_WORD = "jarvis"
JARVIS_SCRIPT = "jarvis.py"

recognizer = sr.Recognizer()
mic = sr.Microphone()

jarvis_process = None


def is_jarvis_running():
    global jarvis_process
    return jarvis_process is not None and jarvis_process.poll() is None


def launch_jarvis():
    global jarvis_process
    print("[listener] Wake word heard - starting Jarvis...")
    jarvis_process = subprocess.Popen([sys.executable, JARVIS_SCRIPT])


def listen_for_wake_word():
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=None, phrase_time_limit=4)
        except sr.WaitTimeoutError:
            return ""

    try:
        text = recognizer.recognize_google(audio)
        return text.lower()
    except (sr.UnknownValueError, sr.RequestError):
        return ""


if __name__ == "__main__":
    print(f"[listener] Waiting for wake word: '{WAKE_WORD}'")
    print("[listener] (This runs quietly in the background. Ctrl+C to stop.)")

    while True:
        try:
            if is_jarvis_running():
                # Jarvis is already active and handling its own conversation -
                # don't compete with it for the microphone.
                time.sleep(1)
                continue

            heard = listen_for_wake_word()

            if WAKE_WORD in heard:
                launch_jarvis()

        except KeyboardInterrupt:
            print("\n[listener] Stopped.")
            break