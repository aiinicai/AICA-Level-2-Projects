"""ELA10 AI pedagogy engine: Gemini via google-genai plus gTTS speech synthesis."""
from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

try:  # Streamlit >= 1.27
    from streamlit.errors import StreamlitSecretNotFoundError
except Exception:  # pragma: no cover
    class StreamlitSecretNotFoundError(Exception):  # type: ignore[no-redef]
        """Fallback so the except clause below always has a valid class."""

from config.prompt_templates import LANGUAGES, SYSTEM_INSTRUCTION, build_user_prompt

MODEL_ID = "gemini-3.8-flash"
_ENV_LOADED = False


def _load_env_files() -> None:
    """Probe .env in cwd, project root and parent directories (once)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve()
    for p in (Path.cwd() / ".env", here.parents[1] / ".env", here.parents[2] / ".env"):
        if p.is_file():
            load_dotenv(p, override=False)


def get_api_key() -> str | None:
    """Resolve key: session override -> st.secrets -> environment/.env."""
    key = st.session_state.get("CUSTOM_GEMINI_KEY")
    if key:
        return str(key).strip()
    try:
        secret = st.secrets["GEMINI_API_KEY"]
        if secret:
            return str(secret).strip()
    except (StreamlitSecretNotFoundError, FileNotFoundError, KeyError):
        pass
    _load_env_files()
    env = os.getenv("GEMINI_API_KEY")
    return env.strip() if env else None


def render_key_drawer() -> bool:
    """Show the credential drawer when no key exists. Returns True if a key is available."""
    if get_api_key():
        return True
    with st.expander("API key required: add a Gemini key to test live AI", expanded=True):
        st.caption("Stored only in this browser session. Never written to disk or Git.")
        entered = st.text_input("Gemini API key", type="password", key="_key_input")
        if st.button("Use this key") and entered.strip():
            st.session_state["CUSTOM_GEMINI_KEY"] = entered.strip()
            st.rerun()
    return False


@dataclass(frozen=True)
class TutorResult:
    ok: bool
    text: str
    chapter: str = ""
    module: str = ""
    error: str = ""


_MAP_RE = re.compile(r"^\s*MAPPED\|([^|\n]+)\|([^\n]+)\s*$", re.MULTILINE)


def parse_response(raw: str) -> tuple[str, str, str]:
    """Return (chapter, module, body) from the model output."""
    m = _MAP_RE.search(raw)
    if not m:
        return "Not classified", "N/A", raw.strip()
    body = (raw[:m.start()] + raw[m.end():]).strip()
    return m.group(1).strip(), m.group(2).strip(), body


def ask_gemini(question: str, language_label: str, name: str) -> TutorResult:
    key = get_api_key()
    if not key:
        return TutorResult(False, "", error="No API key configured.")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=MODEL_ID,
            contents=build_user_prompt(name, question, language_label),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.6),
        )
        raw = (resp.text or "").strip()
        if not raw:
            return TutorResult(False, "", error="The model returned an empty response.")
        chapter, module, body = parse_response(raw)
        return TutorResult(True, body, chapter, module)
    except Exception as exc:  # network, auth, model-not-found, quota
        return TutorResult(False, "", error=f"{type(exc).__name__}: {exc}")


def _clean_for_speech(text: str) -> str:
    text = re.sub(r"[*_#`>|]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:4500]


def synthesize_speech(text: str, language_label: str) -> bytes | None:
    """Return MP3 bytes, or None on failure. Only call with successful AI text."""
    try:
        from gtts import gTTS

        code, _ = LANGUAGES[language_label]
        buf = io.BytesIO()
        gTTS(text=_clean_for_speech(text), lang=code).write_to_fp(buf)
        return buf.getvalue() or None
    except Exception:
        return None


def render_tutor() -> None:
    st.subheader("ELA10 AI Tutor: ask any FM or SM doubt")
    name = st.session_state.get("candidate_name", "Candidate")
    has_key = render_key_drawer()

    language = st.selectbox("Explain in", list(LANGUAGES))
    question = st.text_area("Your doubt", height=120,
                            placeholder="e.g. Why does D-Mart survive with negative working capital?")
    if st.button("Explain it to me", type="primary", disabled=not has_key or not question.strip()):
        with st.spinner("Your senior partner is thinking..."):
            result = ask_gemini(question, language, name)
            audio = synthesize_speech(result.text, language) if result.ok else None
        st.session_state["tutor_result"] = (result, audio, language)

    saved = st.session_state.get("tutor_result")
    if saved:
        result, audio, lang = saved
        if not result.ok:
            st.error(f"Could not get an answer. {result.error}")
            return
        st.markdown(f"<div class='mapped'>Mapped ICAI Syllabus Chapter: <b>{result.chapter}</b> &bull; {result.module}</div>",
                    unsafe_allow_html=True)
        st.markdown(result.text)
        if audio:
            st.audio(audio, format="audio/mp3")
        else:
            st.caption("Audio unavailable right now (speech service needs internet access).")
        st.caption("AI-generated faculty-style explanation. Verify against ICAI Study Material.")
