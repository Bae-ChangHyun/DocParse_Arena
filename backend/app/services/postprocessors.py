"""Post-processors for specific VLM model outputs.

Each function takes raw OCR text and returns cleaned/converted text.
Registry entries reference these by name via the 'postprocessor' field.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

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


# ── dots.ocr official layoutjson2md port ─────────────────────
# Verbatim port of dots_ocr/utils/format_transformer.py (layoutjson2md +
# get_formula_in_markdown + clean_text + helpers) so benchmark scores match the
# official dots.ocr leaderboard runner. The one deviation: 'Picture' cells embed
# a base64 image crop in the original, which we can't do here (no image at the
# postprocessor layer) — pictures are dropped, which doesn't affect the
# text/formula/table/reading-order metrics.
_DOTS_LATEX_PATTERNS = [
    r"\$\$.*?\$\$",
    r"\$[^$\n]+?\$",
    r"\\begin\{.*?\}.*?\\end\{.*?\}",
    r"\\[a-zA-Z]+\{.*?\}",
    r"\\[a-zA-Z]+",
    r"\\\[.*?\\\]",
    r"\\\(.*?\\\)",
]
_DOTS_PREAMBLE_PATTERNS = [
    r"\\documentclass\{[^}]+\}",
    r"\\usepackage\{[^}]+\}",
    r"\\usepackage\[[^\]]*\]\{[^}]+\}",
    r"\\begin\{document\}",
    r"\\end\{document\}",
]


def _dots_has_latex(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return any(re.search(p, text, re.DOTALL) for p in _DOTS_LATEX_PATTERNS)


def _dots_clean_latex_preamble(text: str) -> str:
    for pattern in _DOTS_PREAMBLE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _dots_formula_md(text: str) -> str:
    text = text.strip()
    if text.startswith("$$") and text.endswith("$$"):
        inner = text[2:-2].strip()
        return f"$$\n{inner}\n$$" if "$" not in inner else text
    if text.startswith("\\[") and text.endswith("\\]"):
        return f"$$\n{text[2:-2].strip()}\n$$"
    if len(re.findall(r".*\\\[.*\\\].*", text)) > 0:
        return text
    if len(re.findall(r"\$([^$]+)\$", text)) > 0:  # inline formula, keep as-is
        return text
    if not _dots_has_latex(text):
        return text
    if "usepackage" in text:
        text = _dots_clean_latex_preamble(text)
    if text and text[0] == "`" and text[-1] == "`":
        text = text[1:-1]
    return f"$$\n{text}\n$$"


def _dots_clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if text[:2] == "`$" and text[-2:] == "$`":
        text = text[1:-1]
    return text


def dots_json_to_md(text: str, no_page_hf: bool = False) -> str:
    """Convert dots.ocr layout JSON to Markdown (official layoutjson2md logic).

    ``prompt_layout_all_en`` returns a JSON **array** of cells (bbox/category/text,
    reading-order sorted); some variants wrap it as ``{"layout": [...]}``. Non-JSON
    (e.g. plain ``prompt_ocr`` output) passes through unchanged.
    """
    text = strip_code_fences(text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(data, dict):
        cells = data.get("layout")
        if not isinstance(cells, list):
            return text
    elif isinstance(data, list):
        cells = data
    else:
        return text

    items: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        category = cell.get("category", "Text")
        content = cell.get("text", "")
        if no_page_hf and category in ("Page-header", "Page-footer"):
            continue
        if category == "Picture":
            # Official layoutjson2md emits ![](base64_crop) to hold the picture's
            # place in reading order. We have no image, so emit an empty image
            # placeholder — keeps the reading-order position without adding text.
            items.append("![]()")
            continue
        if category == "Formula":
            items.append(_dots_formula_md(content))
        else:
            items.append(_dots_clean_text(content))

    return "\n\n".join(items) if items else text


def dots_json_to_md_nohf(text: str) -> str:
    """dots.ocr JSON → Markdown, dropping Page-header/Page-footer cells.

    Used for olmOCR-Bench, whose tests require running headers/footers to be
    removed. OmniDocBench keeps them (its ground truth includes them), so the
    plain ``dots_json_to_md`` is used there.
    """
    return dots_json_to_md(text, no_page_hf=True)


# ── Registry of available postprocessors ──────────────────

POSTPROCESSORS: dict[str, Callable[[str], str]] = {
    "deepseek_clean": deepseek_clean,
    "lighton_clean": lighton_clean,
    "dots_json_to_md": dots_json_to_md,
    "dots_json_to_md_nohf": dots_json_to_md_nohf,
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
