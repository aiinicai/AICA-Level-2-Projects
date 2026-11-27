"""
Any-model AI layer (no extra libraries - plain HTTPS with urllib).

Supported providers (chosen in Settings, with a backup provider):
  gemini      Google Gemini            key from aistudio.google.com
  anthropic   Anthropic Claude         key from console.anthropic.com
  openai      OpenAI (ChatGPT)         key from platform.openai.com
  compatible  Any OpenAI-compatible service - OpenRouter, Groq, DeepSeek, Together,
              a company gateway ... (enter its base URL)
  ollama      A local model on this PC through Ollama (fully offline, no key)

The AI is used only to READ statements and to SUGGEST CMA heads.  All
calculations are done by the app itself.
"""
import base64
import json
import ssl
import urllib.error
import urllib.request

PROVIDERS = {
    "gemini": {"label": "Google Gemini", "models": ["gemini-2.5-flash", "gemini-2.5-pro"], "base": ""},
    "anthropic": {"label": "Anthropic Claude", "models": ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"],
                  "base": ""},
    "openai": {"label": "OpenAI", "models": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
               "base": "https://api.openai.com/v1"},
    "compatible": {"label": "OpenAI-compatible (OpenRouter, Groq, DeepSeek ...)", "models": [],
                   "base": "https://openrouter.ai/api/v1"},
    "ollama": {"label": "Local model (Ollama, offline)", "models": ["llama3.2-vision", "qwen2.5vl", "llama3.1"],
               "base": "http://localhost:11434/v1"},
}


class AIError(Exception):
    pass


def _post(url, payload, headers, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=dict({"Content-Type": "application/json"}, **headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:400]
        raise AIError("HTTP %s: %s" % (e.code, body))
    except urllib.error.URLError as e:
        raise AIError("Cannot reach the AI service (%s). Check the internet connection or use a local model."
                      % e.reason)


def call(cfg, prompt, image_png=None, system=None, max_tokens=8000):
    """cfg: {provider, api_key, model, base_url}. Returns the reply text."""
    prov = cfg.get("provider", "gemini")
    key = cfg.get("api_key", "")
    model = cfg.get("model") or (PROVIDERS.get(prov, {}).get("models") or [""])[0]
    b64 = base64.b64encode(image_png).decode("ascii") if image_png else None
    if prov == "gemini":
        if not key:
            raise AIError("No Gemini API key in Settings.")
        parts = [{"text": (system + "\n\n" if system else "") + prompt}]
        if b64:
            parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key)
        out = _post(url, {"contents": [{"parts": parts}],
                          "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens}}, {})
        try:
            return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            raise AIError("Unexpected reply from Gemini: %s" % str(out)[:300])
    if prov == "anthropic":
        if not key:
            raise AIError("No Anthropic API key in Settings.")
        content = []
        if b64:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}})
        content.append({"type": "text", "text": prompt})
        payload = {"model": model, "max_tokens": max_tokens, "temperature": 0,
                   "messages": [{"role": "user", "content": content}]}
        if system:
            payload["system"] = system
        out = _post("https://api.anthropic.com/v1/messages", payload,
                    {"x-api-key": key, "anthropic-version": "2023-06-01"})
        try:
            return "".join(b.get("text", "") for b in out["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise AIError("Unexpected reply from Claude: %s" % str(out)[:300])
    # OpenAI and every OpenAI-compatible endpoint (incl. Ollama)
    base = (cfg.get("base_url") or PROVIDERS.get(prov, {}).get("base") or "").rstrip("/")
    if not base:
        raise AIError("Enter the base URL of the AI service in Settings.")
    content = [{"type": "text", "text": prompt}]
    if b64:
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}})
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    headers = {"Authorization": "Bearer " + key} if key else {}
    out = _post(base + "/chat/completions", {"model": model, "messages": msgs, "temperature": 0,
                                             "max_tokens": max_tokens}, headers)
    try:
        return out["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise AIError("Unexpected reply: %s" % str(out)[:300])


def call_with_backup(settings, prompt, image_png=None, system=None):
    """Try the main provider, then the backup provider."""
    errs = []
    for key in ("ai_main", "ai_backup"):
        cfg = settings.get(key) or {}
        if not cfg.get("provider") or cfg.get("provider") == "none":
            continue
        try:
            return call(cfg, prompt, image_png, system)
        except AIError as e:
            errs.append("%s: %s" % (PROVIDERS.get(cfg["provider"], {}).get("label", cfg["provider"]), e))
    raise AIError(" | ".join(errs) if errs else "No AI provider set in Settings.")


def test_connection(cfg):
    txt = call(cfg, "Reply with the single word OK.", max_tokens=20)
    return txt.strip()[:40]


def ai_enabled(settings):
    return any((settings.get(k) or {}).get("provider") not in (None, "", "none") for k in ("ai_main", "ai_backup"))


def parse_json(text):
    """Pull the first JSON array / object out of a model reply."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    for opener, closer in (("[", "]"), ("{", "}")):
        a, b = t.find(opener), t.rfind(closer)
        if a != -1 and b > a:
            try:
                return json.loads(t[a:b + 1])
            except ValueError:
                continue
    raise AIError("The AI reply was not valid JSON.")
