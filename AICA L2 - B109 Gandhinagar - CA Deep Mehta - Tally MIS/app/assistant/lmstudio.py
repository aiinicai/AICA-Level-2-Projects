"""Talks to LM Studio's local OpenAI-style server. Only this computer can be contacted."""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

DEFAULT_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "google/gemma-4-e2b"


class AssistantError(Exception):
    pass


def check_local(url: str) -> str:
    """Refuse anything that is not this computer, so company figures can never be sent elsewhere."""
    u = urlsplit(url.strip())
    host = (u.hostname or "").lower()
    ok = u.scheme in ("http", "https") and (host == "localhost" or _is_loopback(host))
    if not ok:
        raise AssistantError("The assistant address must be on this PC (localhost or 127.0.0.1).")
    return url.strip().rstrip("/")


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass
class Status:
    online: bool
    model_loaded: bool
    models: list[str]
    message: str


def status(base_url: str, model: str, client: httpx.Client | None = None) -> Status:
    try:
        base = check_local(base_url)
        c = client or httpx.Client(timeout=3.0, trust_env=False)
        r = c.get(f"{base}/models")
        r.raise_for_status()
        ids = [m.get("id", "") for m in r.json().get("data", [])]
    except AssistantError as e:
        return Status(False, False, [], str(e))
    except Exception:
        return Status(False, False, [], "LM Studio is not running. Start LM Studio, load the model and turn on its local server (Developer tab).")
    if model not in ids:
        shown = ", ".join(ids[:5]) or "none"
        return Status(True, False, ids, f'LM Studio is running, but the model "{model}" is not loaded. Loaded models: {shown}.')
    return Status(True, True, ids, "Ready")


def _strip_thinking(text: str) -> str:
    """Remove <think>…</think> blocks that some reasoning models put inside the reply."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def chat(base_url: str, model: str, messages: list[dict], *, max_tokens: int = 300, client: httpx.Client | None = None) -> str:
    base = check_local(base_url)
    c = client or httpx.Client(timeout=httpx.Timeout(180.0, connect=5.0), trust_env=False)
    try:
        r = c.post(f"{base}/chat/completions", json={"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens, "stream": False,
                                  # Reasoning models (Gemma 4, Qwen 3 …) otherwise "think" for minutes and use up the answer space.
                                  "reasoning_effort": "none"})
    except httpx.ConnectError:
        raise AssistantError("LM Studio is not running. Start LM Studio, load the model and turn on its local server.")
    except httpx.TimeoutException:
        raise AssistantError("LM Studio took too long to answer. The model may still be loading; try again in a minute.")
    except httpx.HTTPError as e:
        raise AssistantError(f"Could not reach LM Studio: {e}")
    if r.status_code != 200:
        raise AssistantError(f"LM Studio returned an error ({r.status_code}): {r.text[:200]}")
    try:
        choice = r.json()["choices"][0]
        text = _strip_thinking(choice["message"].get("content") or "")
    except (KeyError, IndexError, ValueError, AttributeError):
        raise AssistantError("LM Studio sent a reply the app could not read.")
    if not text:
        raise AssistantError("The model used all its allowed words thinking and gave no answer. In LM Studio, pick a model without "
                             "“thinking” mode, or turn thinking off for this model, then ask again.")
    return text
