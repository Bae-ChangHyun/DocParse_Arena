"""Post-processors for specific VLM model outputs.

Each function takes raw OCR text and returns cleaned/converted text.
Registry entries reference these by name via the 'postprocessor' field.
"""

from __future__ import annotations

import json


def deepseek_clean(text: str) -> str:
    """Remove DeepSeek-OCR special tokens and normalize newlines."""
    text = text.replace("<｜end▁of▁sentence｜>", "")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def lighton_clean(text: str) -> str:
    """Remove LightOnOCR residual special tokens."""
    text = text.replace("<｜end▁of▁sentence｜>", "")
    text = text.replace("<eos>", "")
    return text.strip()


def dots_json_to_md(text: str) -> str:
    """Convert dots.ocr JSON layout output to Markdown.

    The model outputs a JSON object with a 'layout' array of elements,
    each having 'category', 'text', and 'bbox' fields.
    """
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Not valid JSON - return as-is (might be simple markdown mode)
        return text

    if not isinstance(data, dict) or "layout" not in data:
        return text

    parts = []
    for element in data.get("layout", []):
        category = element.get("category", "Text")
        content = element.get("text", "")

        if not content:
            continue

        if category == "Title":
            parts.append(f"# {content}")
        elif category == "Section-header":
            parts.append(f"## {content}")
        elif category == "List-item":
            parts.append(f"- {content}")
        elif category == "Formula":
            parts.append(f"$${content}$$")
        elif category == "Table":
            parts.append(content)  # Already HTML formatted
        elif category == "Caption":
            parts.append(f"*{content}*")
        elif category == "Footnote":
            parts.append(f"> {content}")
        elif category in ("Page-header", "Page-footer", "Picture"):
            continue
        else:
            parts.append(content)

    return "\n\n".join(parts) if parts else text


# ── Registry of available postprocessors ──────────────────

POSTPROCESSORS: dict[str, callable] = {
    "deepseek_clean": deepseek_clean,
    "lighton_clean": lighton_clean,
    "dots_json_to_md": dots_json_to_md,
}


def apply_postprocessor(name: str, text: str) -> str:
    """Apply a named postprocessor. Returns text unchanged if name is unknown."""
    fn = POSTPROCESSORS.get(name)
    if fn:
        return fn(text)
    return text


def list_postprocessors() -> list[str]:
    """Return available postprocessor names."""
    return list(POSTPROCESSORS.keys())
