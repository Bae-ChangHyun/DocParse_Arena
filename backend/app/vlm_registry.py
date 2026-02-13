"""VLM Model Registry - known model patterns with recommended settings.

This registry provides advisory recommendations for known self-hosted VLM/OCR models.
When a user adds a model whose model_id matches a registry entry, the system
suggests the recommended prompt and optional post-processing.

All recommendations are opt-in: the user is asked whether to apply them,
and can toggle them on/off later via model config.
"""

from __future__ import annotations

VLM_REGISTRY: dict[str, dict] = {
    # ── DeepSeek-OCR ──────────────────────────────────────
    "deepseek-ocr": {
        "display_name": "DeepSeek-OCR",
        "recommended_prompt": "<image>\n<|grounding|>Convert the document to markdown.",
        "postprocessor": "deepseek_clean",
        "notes": (
            "Uses special grounding token in prompt. "
            "Post-processing removes <｜end▁of▁sentence｜> tokens and normalizes newlines."
        ),
        "recommended_config": {"temperature": 0.0},
        "match_patterns": [
            "deepseek-ocr",
            "deepseek-ai/deepseek-ocr",
            "deepseek-ai/DeepSeek-OCR",
            "DeepSeek-OCR",
        ],
    },

    # ── DeepSeek-OCR-2 ────────────────────────────────────
    "deepseek-ocr-2": {
        "display_name": "DeepSeek-OCR-2",
        "recommended_prompt": "<image>\n<|grounding|>Convert the document to markdown.",
        "postprocessor": "deepseek_clean",
        "notes": (
            "Same prompt and post-processing as DeepSeek-OCR. "
            "Visual Causal Flow architecture."
        ),
        "recommended_config": {"temperature": 0.0},
        "match_patterns": [
            "deepseek-ocr-2",
            "deepseek-ai/deepseek-ocr-2",
            "deepseek-ai/DeepSeek-OCR-2",
            "DeepSeek-OCR-2",
        ],
    },

    # ── dots.ocr ──────────────────────────────────────────
    "dots-ocr": {
        "display_name": "dots.ocr",
        "recommended_prompt": (
            "Please output the layout information from the PDF image, "
            "including each layout element's bbox, its category, and the "
            "corresponding text content within the bbox.\n\n"
            "1. Bbox format: [x1, y1, x2, y2]\n\n"
            "2. Layout Categories: The possible categories are "
            "['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', "
            "'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].\n\n"
            "3. Text Extraction & Formatting Rules:\n"
            "    - Picture: For the 'Picture' category, the text field should be omitted.\n"
            "    - Formula: Format its text as LaTeX.\n"
            "    - Table: Format its text as HTML.\n"
            "    - All Others (Text, Title, etc.): Format their text as Markdown.\n\n"
            "4. Constraints:\n"
            "    - The output text must be the original text from the image, with no translation.\n"
            "    - All layout elements must be sorted according to human reading order.\n\n"
            "5. Final Output: The entire output must be a single JSON object."
        ),
        "postprocessor": "dots_json_to_md",
        "notes": (
            "3B model by rednote-hilab. Outputs structured JSON with layout info. "
            "Post-processing converts JSON layout to Markdown. "
            "Alternative simple prompt: 'Extract the text content from this image.' (no post-processing needed)."
        ),
        "recommended_config": {"temperature": 0.0, "max_tokens": 24000},
        "match_patterns": [
            "dots.ocr",
            "dots-ocr",
            "rednote-hilab/dots.ocr",
        ],
    },

    # ── PaddleOCR-VL ──────────────────────────────────────
    "paddleocr-vl": {
        "display_name": "PaddleOCR-VL",
        "recommended_prompt": "OCR:",
        "postprocessor": None,
        "notes": (
            "Supports multiple task prompts: 'OCR:', 'Table Recognition:', "
            "'Formula Recognition:', 'Chart Recognition:', 'Seal Recognition:', "
            "'Spotting:'. Default task is OCR."
        ),
        "recommended_config": {"temperature": 0.0, "max_tokens": 512},
        "match_patterns": [
            "paddleocr-vl",
            "paddlepaddle/paddleocr-vl",
            "paddle-ocr-vl",
        ],
    },

    # ── LightOnOCR ────────────────────────────────────────
    "lightonocr": {
        "display_name": "LightOnOCR-2-1B",
        "recommended_prompt": "Convert the document to markdown.",
        "postprocessor": "lighton_clean",
        "notes": (
            "1B model by lightonai. Very fast (~5.71 pages/sec on H100). "
            "Post-processing removes residual special tokens."
        ),
        "recommended_config": {"temperature": 0.0, "max_tokens": 2048},
        "match_patterns": [
            "lightonocr",
            "lightonai/lightonocr",
            "lightonai/lightonocr-2-1b",
        ],
    },

    # ── Nanonets ──────────────────────────────────────────
    "nanonets": {
        "display_name": "Nanonets-OCR",
        "recommended_prompt": (
            "Extract the text from the above document as if you were reading it naturally. "
            "Return the tables in html format. Return the equations in LaTeX representation. "
            "If there is an image in the document and image caption is not present, "
            "add a small description of the image inside the <img></img> tag; otherwise, "
            "add the image caption inside <img></img>. "
            "Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. "
            "Page numbers should be wrapped in brackets. Ex: <page_number>14</page_number> "
            "or <page_number>9/22</page_number>. "
            "Prefer using \u2610 and \u2611 for check boxes."
        ),
        "postprocessor": None,
        "notes": "Nanonets OCR model. Rich structured output with HTML tables, LaTeX equations, and semantic tags.",
        "recommended_config": {"temperature": 0.0},
        "match_patterns": [
            "nanonets",
            "nanonets-ocr",
            "nanonets/Nanonets-OCR-s",
        ],
    },

}


def match_registry(model_id: str) -> dict | None:
    """Match a model_id against the registry.

    Tries exact key match first, then match_patterns, then substring.
    Returns a cleaned entry or None.
    """
    if not model_id:
        return None

    normalized = model_id.strip().lower()

    # Exact key match
    if normalized in VLM_REGISTRY:
        return _clean_entry(normalized, VLM_REGISTRY[normalized])

    # Pattern matching (case-insensitive)
    for key, entry in VLM_REGISTRY.items():
        for pattern in entry.get("match_patterns", []):
            if pattern.lower() == normalized:
                return _clean_entry(key, entry)

    # Substring matching (looser)
    for key, entry in VLM_REGISTRY.items():
        for pattern in entry.get("match_patterns", []):
            if pattern.lower() in normalized or normalized in pattern.lower():
                return _clean_entry(key, entry)

    return None


def list_registry() -> list[dict]:
    """Return all registry entries."""
    return [_clean_entry(key, entry) for key, entry in VLM_REGISTRY.items()]


def _clean_entry(key: str, entry: dict) -> dict:
    """Return a copy without internal fields (match_patterns)."""
    return {
        "key": key,
        "display_name": entry["display_name"],
        "recommended_prompt": entry["recommended_prompt"],
        "postprocessor": entry.get("postprocessor"),
        "notes": entry["notes"],
        "recommended_config": entry.get("recommended_config", {}),
    }
