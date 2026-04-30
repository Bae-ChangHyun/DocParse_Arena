from __future__ import annotations

from typing import Any


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def extract_message_text(message: Any) -> str:
    return _first_text(
        getattr(message, "content", None),
        getattr(message, "reasoning_content", None),
        getattr(message, "reasoning", None),
    )


def extract_delta_text(delta: Any) -> str:
    return _first_text(
        getattr(delta, "content", None),
        getattr(delta, "reasoning_content", None),
        getattr(delta, "reasoning", None),
    )
