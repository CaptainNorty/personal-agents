"""
LLM call surfaces.

Two stacks live here side-by-side:

  1. The existing LangChain `ask_claude()` helper, used by the Telegram bot
     agent loops (podcast, nutrition, etc.). Don't change the model or
     behavior here without coordinating with those features.

  2. Direct Anthropic SDK helpers (`ask_claude_text`, `ask_claude_structured`),
     for static one-shot calls that need structured outputs, prompt caching,
     adaptive thinking, or tighter cost control. Used by Unknown Unknowns for
     end-of-session content generation, post-cold-record briefing generation,
     and end-of-day scoring.
"""

import json
from typing import Any, TypeVar

from anthropic import AsyncAnthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import settings

# === Existing LangChain helper (Telegram bots) =========================

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    anthropic_api_key=settings.anthropic_api_key,
)


async def ask_claude(prompt: str, system: str | None = None) -> str:
    """Send a prompt to Claude and return the response text."""
    messages: list = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))
    response = await llm.ainvoke(messages)
    return str(response.content)


# === Direct Anthropic SDK helpers (UU and future static structured calls) ===

DEFAULT_MODEL = "claude-opus-4-7"

T = TypeVar("T", bound=BaseModel)

_async_client: AsyncAnthropic | None = None


def _client() -> AsyncAnthropic:
    """Singleton AsyncAnthropic client, lazily initialized."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _async_client


def _enforce_strict_object_schemas(schema: Any) -> Any:
    """Recursively ensure every JSON-schema `object` carries
    `additionalProperties: false`. Anthropic's structured-outputs feature
    rejects schemas that omit it, but Pydantic's model_json_schema() does
    not emit it by default. We add it here so callers don't need to
    annotate every model with `model_config = {"extra": "forbid"}`.

    Mutates and returns the schema for convenience.
    """
    if isinstance(schema, dict):
        if schema.get("type") == "object" and "additionalProperties" not in schema:
            schema["additionalProperties"] = False
        for v in schema.values():
            _enforce_strict_object_schemas(v)
    elif isinstance(schema, list):
        for item in schema:
            _enforce_strict_object_schemas(item)
    return schema


def _build_system_param(
    system: str | None, cache_system: bool
) -> str | list[dict[str, Any]] | None:
    """Wrap the system prompt in a cache-control block when caching is enabled,
    otherwise pass through as a string.

    Note: on Opus 4.7, prompt caching only kicks in for prefixes ≥4096 tokens.
    Setting cache_system=True on a short prompt is a no-op (no cache write,
    no cache read) — verify via response.usage.cache_read_input_tokens.
    """
    if system is None:
        return None
    if cache_system:
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    return system


async def ask_claude_text(
    prompt: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16_000,
    effort: str = "high",
    cache_system: bool = False,
) -> str:
    """One-shot unstructured text completion via the Anthropic SDK.

    Defaults to Opus 4.7 with adaptive thinking and `high` effort. For
    typed/validated outputs, use ask_claude_structured() instead — passing a
    Pydantic schema constrains the response and returns a parsed instance.

    Parameters
    ----------
    prompt : str
        The user message.
    system : str, optional
        System prompt. If set, becomes a cache-control prefix when
        cache_system=True.
    model : str
        Model ID. Defaults to claude-opus-4-7. Pass claude-sonnet-4-6 or
        claude-haiku-4-5 for cheaper/faster calls.
    max_tokens : int
        Hard ceiling on response size (thinking + text). 16k is generous for
        most one-shot tasks; raise for long-form generation.
    effort : str
        Thinking depth / overall token spend: low | medium | high | max.
        High is the default sweet spot. `max` is Opus-tier only.
    cache_system : bool
        Mark the system prompt as a cached prefix. Saves ~90% on repeated
        calls with the same system prompt (≥4096 tokens on Opus 4.7).
    """
    client = _client()
    system_param = _build_system_param(system, cache_system)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
    }
    if system_param is not None:
        kwargs["system"] = system_param

    response = await client.messages.create(**kwargs)

    if response.stop_reason == "max_tokens":
        # Don't silently truncate — the caller wanted a complete response.
        raise RuntimeError(
            f"Hit max_tokens={max_tokens} before completion. "
            "Raise max_tokens or shorten the prompt."
        )
    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Claude declined to respond to this prompt (stop_reason=refusal)."
        )

    return "".join(b.text for b in response.content if b.type == "text")


async def ask_claude_structured(
    prompt: str,
    schema: type[T],
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16_000,
    effort: str = "high",
    cache_system: bool = False,
) -> T:
    """One-shot structured completion: model returns JSON matching `schema`,
    validated and returned as a Pydantic instance.

    Uses Anthropic's structured-outputs feature (output_config.format =
    json_schema) which guarantees the response is valid JSON conforming to
    the schema. The first request with a new schema incurs a one-time
    compilation cost; subsequent calls with the same schema hit a 24-hour
    cache.

    Parameters mirror ask_claude_text(). The additional `schema` argument
    must be a Pydantic BaseModel subclass.

    Example
    -------
        class Score(BaseModel):
            coverage: int
            accuracy: int
            notes: str

        result = await ask_claude_structured(
            prompt=f"Rate this answer against the bullets:\\n{transcript}",
            schema=Score,
            system="You score on a 1-10 scale.",
            cache_system=True,
        )
        result.coverage  # int
    """
    client = _client()
    system_param = _build_system_param(system, cache_system)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": effort,
            "format": {
                "type": "json_schema",
                "schema": _enforce_strict_object_schemas(schema.model_json_schema()),
            },
        },
    }
    if system_param is not None:
        kwargs["system"] = system_param

    response = await client.messages.create(**kwargs)

    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Hit max_tokens={max_tokens} before completion — JSON likely truncated. "
            "Raise max_tokens."
        )
    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Claude declined to respond to this prompt (stop_reason=refusal)."
        )

    text = "".join(b.text for b in response.content if b.type == "text")
    if not text.strip():
        raise RuntimeError(
            f"Model returned no text content (stop_reason={response.stop_reason}). "
            f"Expected JSON matching {schema.__name__}."
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned non-JSON content despite structured-output schema: "
            f"{text[:200]!r}"
        ) from exc

    return schema.model_validate(data)
