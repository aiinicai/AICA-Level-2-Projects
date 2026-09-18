"""
Provider-agnostic LLM completion seam.

The generic engine (criteria derivation + validation) and the panel are
provider-neutral: a "model" is just a string, and which SDK we call is decided
from that string. This is what makes the panel's *cross-provider* diversity
real — listing e.g. `gpt-4o-mini,claude-haiku-4-5-20251001` in AI_JURY_MODELS
convenes jurors that are genuinely independent (different vendors, weights, and
training), not just the same model sampled at different temperatures.

Model naming:
  - `gpt-*`, `o1-*`, `o3-*`, or an explicit `openai:<model>`  -> OpenAI
  - `claude-*` or an explicit `anthropic:<model>`             -> Anthropic
  - `openrouter:<vendor/model>`, or any bare `vendor/model`
    (contains a `/`, the OpenRouter convention)               -> OpenRouter
A bare unknown name defaults to OpenAI (backwards compatible).

OpenRouter is an OpenAI-compatible gateway to many vendors' models through one
key (`anthropic/claude-*`, `openai/gpt-*`, `google/gemini-*`, `meta-llama/*`, …),
which is the cheapest way to get cross-provider panel diversity from a single
account — no separate Anthropic SDK/key needed.

`anthropic` is an OPTIONAL dependency: it is imported lazily, so OpenAI-only
deployments never need it installed. We only raise if a Claude *native* model is
actually requested without the SDK present (OpenRouter uses the OpenAI SDK).
"""

import json
import os
import re
from typing import Optional

from services import cost as _cost

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _max_output_tokens() -> int:
    """Cap on completion tokens per call. Our outputs are compact JSON verdicts, so a
    small cap is plenty — and it stops OpenRouter from RESERVING credit for a model's
    full (e.g. 65k) max output, which otherwise causes spurious 402 'need more credits'.
    """
    try:
        return int(os.getenv("AI_MAX_OUTPUT_TOKENS", "4096"))
    except ValueError:
        return 4096


def _extract_json(text: str) -> str:
    """Pull a JSON value out of an LLM reply.

    Models (notably Claude/Gemini via OpenRouter) ignore response_format and wrap
    JSON in a ```json ... ``` fence or add prose around it. We strip the fence and,
    failing that, take the outermost {...}/[...] span so json.loads() succeeds. If
    nothing JSON-looking is found, the original text is returned unchanged.
    """
    if not text:
        return text
    s = text.strip()
    m = _FENCE_RE.search(s)
    if m:
        s = m.group(1).strip()
    if s and s[0] not in "{[":
        starts = [i for i in (s.find("{"), s.find("[")) if i != -1]
        ends = [i for i in (s.rfind("}"), s.rfind("]")) if i != -1]
        if starts and ends:
            i, j = min(starts), max(ends)
            if i < j:
                s = s[i:j + 1]
    return s

OPENAI = "openai"
ANTHROPIC = "anthropic"
OPENROUTER = "openrouter"

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def provider_for_model(model: str) -> str:
    """Infer the provider from a model string (explicit `provider:` prefix wins)."""
    m = (model or "").strip().lower()
    if m.startswith("openrouter:"):
        return OPENROUTER
    if m.startswith("anthropic:") or m.startswith("claude"):
        return ANTHROPIC
    if m.startswith("openai:") or m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return OPENAI
    if "/" in m:  # vendor/model -> OpenRouter convention
        return OPENROUTER
    return OPENAI  # safe default — historical behaviour


def _strip_prefix(model: str) -> str:
    for p in ("openai:", "anthropic:", "openrouter:"):
        if model.lower().startswith(p):
            return model[len(p):]
    return model


def complete(model: str, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, api_key: Optional[str] = None,
             json_mode: bool = True) -> str:
    """Run one chat completion against whichever provider `model` names.

    Returns the raw assistant text (expected to be JSON when json_mode=True).
    """
    provider = provider_for_model(model)
    real_model = _strip_prefix(model)
    if provider == ANTHROPIC:
        out = _complete_anthropic(real_model, system_prompt, user_prompt, temperature, api_key, json_mode)
    elif provider == OPENROUTER:
        out = _complete_openrouter(real_model, system_prompt, user_prompt, temperature, json_mode)
    else:
        out = _complete_openai(real_model, system_prompt, user_prompt, temperature, api_key, json_mode)
    # Models often ignore response_format and fence/wrap JSON — normalize it so
    # every caller's json.loads() succeeds regardless of provider quirks.
    return _extract_json(out) if json_mode else out


def supports_tool_loop(model: str) -> bool:
    """Tool-calling loop is supported on the OpenAI-compatible providers.

    OpenAI models natively, and ANY model via OpenRouter (including claude-*/gemini-*
    through the `vendor/model` form) which speaks the OpenAI tool-call format. Native
    `anthropic:`/`claude-*` (direct SDK) is not wired for tools yet — use the
    OpenRouter form `anthropic/claude-...` instead.
    """
    return provider_for_model(model) in (OPENAI, OPENROUTER)


def _openai_compatible_client(model: str, api_key: Optional[str]):
    """Build an OpenAI() client pointed at the right provider for `model`."""
    from openai import OpenAI

    if provider_for_model(model) == OPENROUTER:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set (required for the tool loop on this model).")
        return OpenAI(api_key=key, base_url=os.getenv("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL))
    key = api_key or os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=key) if key else OpenAI()


def complete_with_tools(model: str, system_prompt: str, messages: list,
                        tools: list, temperature: float = 0.1,
                        api_key: Optional[str] = None) -> dict:
    """One tool-calling step (OpenAI function-calling format).

    `messages` is the running conversation in OpenAI format (without the system
    message — it is prepended here). `tools` is a list of bare function schemas
    ({name, description, parameters}). Returns a normalized dict:
        {"content": str|None, "tool_calls": [{"id","name","arguments"(dict)}]}
    """
    if provider_for_model(model) == ANTHROPIC:
        raise RuntimeError(
            f"The tool loop does not support the native Anthropic model '{model}'. "
            "Use the OpenRouter form instead, e.g. 'anthropic/claude-3.5-sonnet'."
        )
    client = _openai_compatible_client(model, api_key)
    oa_tools = [{"type": "function", "function": t} for t in tools]
    resp = client.chat.completions.create(
        model=_strip_prefix(model),
        messages=[{"role": "system", "content": system_prompt}] + messages,
        tools=oa_tools,
        temperature=temperature,
        max_tokens=_max_output_tokens(),
    )
    _record_openai_usage(("openrouter/" if provider_for_model(model) == OPENROUTER else "") + _strip_prefix(model), resp)
    msg = resp.choices[0].message
    calls = []
    for tc in (getattr(msg, "tool_calls", None) or []):
        try:
            args = json.loads(tc.function.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {}
        calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
    return {"content": msg.content, "tool_calls": calls}


# -- usage helper -----------------------------------------------------------

def _record_openai_usage(model, response) -> None:
    """Record token usage from an OpenAI-format response into the active cost tracker."""
    u = getattr(response, "usage", None)
    if u is not None:
        _cost.record(model, getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))


# -- OpenAI -----------------------------------------------------------------

def _complete_openai(model, system_prompt, user_prompt, temperature, api_key, json_mode) -> str:
    from openai import OpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=key) if key else OpenAI()
    kwargs = {
        "model": model,
        "max_tokens": _max_output_tokens(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    _record_openai_usage(model, response)
    return response.choices[0].message.content


# -- OpenRouter (OpenAI-compatible gateway) ---------------------------------

def _complete_openrouter(model, system_prompt, user_prompt, temperature, json_mode) -> str:
    """Call OpenRouter via the OpenAI SDK with a custom base_url.

    `model` is the OpenRouter id, e.g. `anthropic/claude-3.5-sonnet` or
    `openai/gpt-4o-mini`. The key comes from OPENROUTER_API_KEY (never from the
    OpenAI key), so OpenRouter usage is isolated from direct OpenAI usage.
    """
    from openai import OpenAI

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            f"Model '{model}' routes to OpenRouter but OPENROUTER_API_KEY is not set. "
            "Add it to your .env (get one at https://openrouter.ai/keys)."
        )
    base_url = os.getenv("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL)
    # Optional attribution headers OpenRouter uses for its dashboards/rankings.
    extra_headers = {}
    if os.getenv("OPENROUTER_SITE_URL"):
        extra_headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL")
    if os.getenv("OPENROUTER_APP_NAME"):
        extra_headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME")

    client = OpenAI(api_key=key, base_url=base_url)
    kwargs = {
        "model": model,
        "max_tokens": _max_output_tokens(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if extra_headers:
        kwargs["extra_headers"] = extra_headers
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    _record_openai_usage("openrouter/" + model, response)
    return response.choices[0].message.content


# -- Anthropic --------------------------------------------------------------

def _complete_anthropic(model, system_prompt, user_prompt, temperature, api_key, json_mode) -> str:
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover - exercised only when a Claude model is configured
        raise RuntimeError(
            f"Model '{model}' needs the Anthropic SDK. Install it with `pip install anthropic` "
            "(it is an optional dependency, only required when AI_JURY_MODELS/AI_CRITIC_MODEL "
            "reference a claude-* model)."
        ) from e

    key = api_key if (api_key and api_key.startswith("sk-ant")) else os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()

    messages = [{"role": "user", "content": user_prompt}]
    # Anthropic has no response_format=json_object; prefill an opening brace so the
    # model is forced to continue a JSON object, then re-attach it to the result.
    if json_mode:
        messages.append({"role": "assistant", "content": "{"})

    try:
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))
    except ValueError:
        max_tokens = 4096

    resp = client.messages.create(
        model=model,
        system=system_prompt,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    u = getattr(resp, "usage", None)
    if u is not None:
        _cost.record(model, getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0))
    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    if json_mode:
        text = "{" + text
        # Defensive: ensure the prefill produced parseable JSON; if the model added
        # trailing prose, keep only up to the last closing brace.
        try:
            json.loads(text)
        except json.JSONDecodeError:
            end = text.rfind("}")
            if end != -1:
                text = text[: end + 1]
    return text
