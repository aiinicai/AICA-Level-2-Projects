"""
audio_helper.py
Adds voice input (speech-to-text) and voice output (text-to-speech) to the
AI panels, without adding any paid API dependency.

VOICE INPUT: uses the free, unofficial Google Web Speech recognition
endpoint via the `SpeechRecognition` library. No API key needed. This is
best-effort — it's rate-limited and not officially supported for heavy
production use, but is well suited to demo and moderate real usage.

VOICE OUTPUT: uses the browser's own built-in speechSynthesis API via a
small embedded HTML/JS snippet. Runs entirely client-side in the employee's
browser — no server calls, no cost, no extra API.
"""

import io
import streamlit as st
import streamlit.components.v1 as components

try:
    import speech_recognition as sr
except ImportError:
    sr = None


def transcribe_audio(audio_bytes: bytes) -> str:
    """Converts recorded audio (WAV bytes) to text. Returns an empty string
    and a friendly message on failure rather than raising, so a flaky
    transcription never crashes the app."""
    if sr is None:
        return ""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return ""
    except Exception:
        return ""


def speak_text_button(text: str, key: str):
    """Renders a small 'Listen' button that reads the given text aloud using
    the browser's built-in text-to-speech. No audio is generated server-side
    or sent anywhere — this runs entirely in the employee's browser."""
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    components.html(
        f"""
        <button id="speak-btn-{key}" style="
            background:#12b76a;color:white;border:none;border-radius:8px;
            padding:8px 16px;font-size:14px;cursor:pointer;">
            🔊 Listen to this answer
        </button>
        <script>
        document.getElementById("speak-btn-{key}").onclick = function() {{
            const utterance = new SpeechSynthesisUtterance("{safe_text}");
            utterance.rate = 0.95;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        }};
        </script>
        """,
        height=50,
    )
