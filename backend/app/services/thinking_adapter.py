from __future__ import annotations

from typing import Any

ThinkingMode = str

MODE_DEFAULT = "default"
MODE_OFF = "off"
MODE_LOW = "low"
MODE_MEDIUM = "medium"
MODE_HIGH = "high"

ALLOWED_MODES = {MODE_DEFAULT, MODE_OFF, MODE_LOW, MODE_MEDIUM, MODE_HIGH}


def detect_thinking_family(model_id: str) -> str:
    """Detect the OpenAI-compatible thinking control family from a model id."""
    normalized = (model_id or "").lower()
    if "gpt-oss" in normalized:
        return "gpt-oss"
    if "gemma-4" in normalized or "gemma4" in normalized:
        return "gemma4"
    if "qwen3" in normalized:
        return "qwen3"
    return "plain"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def build_thinking_kwargs(
    model_id: str,
    mode: ThinkingMode = MODE_DEFAULT,
    budget: int | None = None,
    extra_body_raw: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map normalized thinking controls to OpenAI-compatible request kwargs."""
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unknown thinking mode: {mode}")

    top_kwargs: dict[str, Any] = {}
    extra_body: dict[str, Any] = {}
    family = detect_thinking_family(model_id)
    is_off = mode in (MODE_DEFAULT, MODE_OFF)

    if family == "gpt-oss":
        if is_off:
            extra_body["include_reasoning"] = False
        else:
            top_kwargs["reasoning_effort"] = mode
    elif family == "gemma4":
        extra_body.setdefault("chat_template_kwargs", {})["enable_thinking"] = not is_off
    elif family == "qwen3":
        extra_body.setdefault("chat_template_kwargs", {})["enable_thinking"] = not is_off
        if not is_off and budget and budget > 0:
            extra_body["thinking_token_budget"] = int(budget)

    if extra_body_raw:
        extra_body = _deep_merge(extra_body, extra_body_raw)

    return top_kwargs, extra_body
