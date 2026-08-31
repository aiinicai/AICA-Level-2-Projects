"""
services/gemini_service.py — R K Muley & Co | Tax Notice Litigation Assistant v8.1

Gemini API wrapper using the current google-genai SDK (v1.x).
Uses the current google-genai SDK (v1.x) only. Install: pip install google-genai

Install: pip install google-genai tenacity

API pattern (google.genai v1.x):
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="prompt text",
        config=types.GenerateContentConfig(
            system_instruction="...",
            temperature=0.15,
            max_output_tokens=8192,
            top_p=0.85,
            top_k=40,
        )
    )
    text = response.text
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("RKMuley.Gemini.v8")

# ── SDK import ────────────────────────────────────────────────────────────────
try:
    import google.genai as genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None          # type: ignore[assignment]
    genai_types = None    # type: ignore[assignment]

# ── Retry ─────────────────────────────────────────────────────────────────────
try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False


# ── Custom exception ──────────────────────────────────────────────────────────
class APICallError(Exception):
    """Raised when the Gemini API call fails after all retries."""


# ── HallucinationGuard system instruction ─────────────────────────────────────
# Injected as systemInstruction (separate field) — more reliable than
# prepending to the contents string, and correctly scoped in the v1.x SDK.
_GUARD_SYSTEM_INSTRUCTION = """\
You are generating a legal document for professional use in Indian income tax proceedings.

ABSOLUTE RULES:
1. SECTIONS: Only cite sections that exist in the Income Tax Act, 1961.
   Valid: Section 148A(b), Section 271(1)(c). Invalid: Section 199A, Section 45(3A).
2. CASE LAWS: Use verified-library and user-provided citations in the main filing draft.
   You may suggest additional authorities only if the prompt requests it and only under:
   "SUGGESTED AUTHORITIES - VERIFY BEFORE USE".
   Each outside-library suggestion must say it requires independent verification before filing.
3. FACTS: Use only facts from the extracted notice data and user inputs provided.
   Do not invent amounts, dates, or procedural steps.
4. FORMAT: Plain text only. No markdown, asterisks, hash headers, or bullet symbols.
5. VOICE: First person only. Never write "the assessee" or "the taxpayer".
"""


# ── API key resolution ────────────────────────────────────────────────────────
def get_api_key() -> str:
    """
    Retrieve Gemini API key in priority order:
      1. Streamlit secrets  (st.secrets["GEMINI_API_KEY"])
      2. Environment var    (GEMINI_API_KEY)
      3. Streamlit session  (legacy local-dev fallback)
    Returns empty string if not found.
    """
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key

    try:
        import streamlit as st
        return st.session_state.get("_api_key_", "")
    except Exception:
        return ""


# ── Retry-wrapped raw caller ──────────────────────────────────────────────────
def _build_caller():
    """Return a generate_content caller with or without tenacity retry."""

    if TENACITY_AVAILABLE:
        @retry(
            wait=wait_exponential(multiplier=1, min=2, max=30),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _call(client, model_name, contents, system_instruction, temperature, max_tokens):
            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=0.85,
                top_k=40,
                system_instruction=system_instruction,
            )
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            ).text
        return _call

    else:
        def _call_plain(client, model_name, contents, system_instruction, temperature, max_tokens):
            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=0.85,
                top_k=40,
                system_instruction=system_instruction,
            )
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            ).text
        return _call_plain


_raw_caller = _build_caller()


# ── Public API ────────────────────────────────────────────────────────────────
def call_gemini(
    model_name: str,
    prompt: str,
    temperature: float = 0.15,
    max_tokens: int = 8192,
    step: str = "unknown",
    username: str = "system",
    inject_guard: bool = True,
) -> str:
    """
    Call the Gemini API via google.genai v1.x SDK.

    Args:
        model_name:   Gemini model ID, e.g. "gemini-2.5-flash"
        prompt:       Full prompt (sent as contents)
        temperature:  0.05-0.20 for legal drafting; up to 0.4 for creative steps
        max_tokens:   Maximum output tokens
        step:         Label for generation_log audit trail
        username:     Username for audit log
        inject_guard: If True, set HallucinationGuard as systemInstruction

    Returns:
        Response text string

    Raises:
        APICallError on exhausted retries, missing package, or missing key
    """
    from database import log_generation

    if not GENAI_AVAILABLE:
        raise APICallError(
            "google-genai package not installed. Run: pip install google-genai"
        )

    api_key = get_api_key()
    if not api_key:
        raise APICallError(
            "Gemini API key not found. "
            "Set GEMINI_API_KEY in .streamlit/secrets.toml or as an environment variable."
        )

    if len(prompt) > 200_000:
        logger.warning("Prompt truncated from %d to 200,000 chars.", len(prompt))
        prompt = prompt[:200_000]

    system_instr = _GUARD_SYSTEM_INSTRUCTION if inject_guard else None

    try:
        client = genai.Client(api_key=api_key)
        text = _raw_caller(client, model_name, prompt, system_instr, temperature, max_tokens)

        log_generation(
            model=model_name,
            step=step,
            prompt=prompt,
            output=text,
            username=username,
            notes=f"temp={temperature},tokens={max_tokens}",
        )
        logger.info("Gemini OK: model=%s step=%s chars=%d", model_name, step, len(text))
        return text

    except APICallError:
        raise
    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        raise APICallError(
            f"Gemini API call failed after retries: {exc}\n\n"
            "Check: API key, model name, internet connection, API quota."
        ) from exc
