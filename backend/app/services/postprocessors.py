"""Post-processors for specific VLM model outputs.

Each function takes raw OCR text and returns cleaned/converted text.
Registry entries reference these by name via the 'postprocessor' field.
"""

from __future__ import annotations

import json
import re

# Matches opening code fence: ```markdown, ```md, ```html, ```json, ``` etc.
_CODE_FENCE_OPEN_RE = re.compile(r"^```\w*\s*$", re.MULTILINE)


def strip_code_fences(text: str) -> str:
    """Remove wrapping markdown code fences from OCR output.

    Many LLMs wrap their entire response in ```markdown ... ```.
    This strips the outermost fence if present.
    Applied globally to all OCR results before model-specific post-processing.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text

    first_newline = stripped.find("\n")
    if first_newline == -1:
        return text

    opening_line = stripped[:first_newline].strip()
    if not re.match(r"^```\w*$", opening_line):
        return text

    if not stripped.endswith("```"):
        return text

    # Strip opening fence line and closing ```
    inner = stripped[first_newline + 1:]
    inner = inner[: -len("```")].rstrip("\n")
    return inner

# Matches DeepSeek grounding labels: sub_title[[x, y, w, h]]
_GROUNDING_LABEL_RE = re.compile(
    r"^(sub_title|text|image|table|title|header|footer|formula|caption)\[\[[\d,\s]+\]\]\s*$",
    re.MULTILINE,
)


def deepseek_clean(text: str) -> str:
    """Convert DeepSeek-OCR grounding output to clean Markdown.

    DeepSeek-OCR with <|grounding|> prompt outputs labels like:
        sub_title[[49, 31, 520, 60]]
        ## Heading text
        text[[209, 85, 400, 106]]
        Some paragraph content
        table[[49, 217, 949, 287]]
        <table>...</table>

    This function strips the label lines and special tokens,
    keeping only the content as clean markdown.
    """
    text = text.replace("<｜end▁of▁sentence｜>", "")
    text = strip_code_fences(text)

    # Check if text contains grounding labels
    if not _GROUNDING_LABEL_RE.search(text):
        # No grounding format — just normalize whitespace
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

    # Parse grounding format: strip label lines, keep content
    lines = text.split("\n")
    result_lines = []
    skip_empty_after_label = False

    for line in lines:
        if _GROUNDING_LABEL_RE.match(line.strip()):
            # This is a label line — skip it
            skip_empty_after_label = True
            continue

        if skip_empty_after_label and line.strip() == "":
            # Skip empty line right after label
            skip_empty_after_label = False
            continue

        skip_empty_after_label = False
        result_lines.append(line)

    result = "\n".join(result_lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.strip()


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
