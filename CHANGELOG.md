# Changelog

## v0.5.0
- Moved vision logic into a standalone `vision.py` module
- `jarvis.py` now imports `describe_screen` and `describe_webcam` from `vision.py`

## v0.4.0
- Added vision support: describe screen or webcam using a vision-language
  model via Hugging Face's inference router
- Added live news via Google News RSS, with category support (sports,
  technology, business, science, health, entertainment, world, india)
  and arbitrary topic queries ("news about X")

## v0.3.0
- Split the assistant into two processes: `listener.py` (always-on wake
  word listener) and `jarvis.py` (full assistant, launched on demand)
- `jarvis.py` now exits automatically after a period of silence, handing
  control back to the listener
- Added Google Calendar integration for reading today's events
- Added persistent memory backed by SQLite (`jarvis_memory.db`)
- Added interruptible speech support
- Upgraded text-to-speech from `pyttsx3` to `edge-tts` with `pygame`
  playback for more natural-sounding voices
- Fixed a `PermissionError` caused by overwriting an in-use audio file by
  using unique temporary filenames and unloading the file after playback
- Added weather (Open-Meteo, no API key) and time/date commands
- Added app close command using `taskkill`

## v0.2.0
- Switched the LLM backend from local Ollama / Anthropic to Groq
- Reduced model size to `llama-3.1-8b-instant` to lower token cost and
  latency
- Added markdown stripping so spoken responses don't include literal
  asterisks from bold/italic/bullet formatting

## v0.1.0
- Initial voice assistant: voice input/output, opening apps, web search,
  and basic PC control (shutdown, restart, lock, volume)
- General conversation handled via LLM fallback