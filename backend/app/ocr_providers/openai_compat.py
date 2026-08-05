from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def _reasoning_text(obj: Any) -> str:
    return _first_text(
        getattr(obj, "reasoning_content", None),
        getattr(obj, "reasoning", None),
    )


def extract_message_text(message: Any) -> str:
    """Return the message text, wrapping any separate reasoning in <think>.

    When the server splits thinking into ``reasoning_content`` (vLLM reasoning
    parser), we keep the answer as the main content and wrap the thinking in
    ``<think>...</think>`` so the UI can show it in Raw but hide it in Rendered.
    Models that emit thinking inline already carry ``<think>`` in content and
    pass through unchanged.
    """
    content = getattr(message, "content", None)
    content = content if isinstance(content, str) else ""
    reasoning = _reasoning_text(message)
    if reasoning and content:
        return f"<think>{reasoning}</think>\n\n{content}"
    if reasoning:
        return f"<think>{reasoning}</think>"
    return content


def extract_delta_text(delta: Any) -> str:
    return _first_text(
        getattr(delta, "content", None),
        getattr(delta, "reasoning_content", None),
        getattr(delta, "reasoning", None),
    )


async def iter_think_wrapped(stream: Any) -> AsyncGenerator[str, None]:
    """Yield text from an OpenAI-compatible chat stream.

    Reasoning deltas (``reasoning_content``) are wrapped in a single
    ``<think>...</think>`` block; normal content follows. Streams without
    separate reasoning behave exactly like plain content streaming.
    """
    in_think = False
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = _reasoning_text(delta)
        content = getattr(delta, "content", None)
        if reasoning:
            if not in_think:
                yield "<think>"
                in_think = True
            yield reasoning
        if isinstance(content, str) and content:
            if in_think:
                yield "</think>\n\n"
                in_think = False
            yield content
    if in_think:
        yield "</think>"
