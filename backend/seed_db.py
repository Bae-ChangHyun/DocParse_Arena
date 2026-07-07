"""Seed the database with initial OCR models and provider settings."""
import asyncio

from loguru import logger
from sqlalchemy import select

from app.config import get_settings
from app.models.database import OcrModel, PromptSetting, ProviderSetting, async_session, init_db

SEED_PROVIDERS = [
    {"id": "claude", "display_name": "Anthropic Claude", "provider_type": "claude"},
    {"id": "openai", "display_name": "OpenAI", "provider_type": "openai"},
    {"id": "gemini", "display_name": "Google Gemini", "provider_type": "gemini"},
    {"id": "mistral", "display_name": "Mistral AI", "provider_type": "mistral"},
]

SEED_MODELS = [
    {
        "id": "claude-sonnet",
        "name": "claude-sonnet",
        "display_name": "Claude Sonnet 4",
        "provider": "claude",
        "model_id": "claude-sonnet-4-20250514",
        "icon": "CS",
        "is_active": False,
    },
    {
        "id": "claude-haiku",
        "name": "claude-haiku",
        "display_name": "Claude Haiku 3.5",
        "provider": "claude",
        "model_id": "claude-haiku-4-5-20251001",
        "icon": "CH",
        "is_active": False,
    },
    {
        "id": "gpt-4o",
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
        "icon": "O4",
        "is_active": False,
    },
    {
        "id": "gpt-4o-mini",
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "icon": "O4m",
        "is_active": False,
    },
    {
        "id": "gemini-2-flash",
        "name": "gemini-2-flash",
        "display_name": "Gemini 2.0 Flash",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash",
        "icon": "G2",
        "is_active": False,
    },
    {
        "id": "gemini-2-flash-lite",
        "name": "gemini-2-flash-lite",
        "display_name": "Gemini 2.0 Flash Lite",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash-lite",
        "icon": "G2L",
        "is_active": False,
    },
    {
        "id": "mistral-small",
        "name": "mistral-small",
        "display_name": "Mistral Small",
        "provider": "mistral",
        "model_id": "mistral-small-latest",
        "icon": "MS",
        "is_active": False,
    },
    # Local PaddleOCR-VL-1.6 served via vLLM (OpenAI-compatible) through llmux.
    # Uses the "custom" provider; base_url reaches the host's vLLM server.
    {
        "id": "paddleocr-vl-1-6",
        "name": "paddleocr-vl-1-6",
        "display_name": "PaddleOCR-VL 1.6",
        "provider": "custom",
        "model_id": "PaddlePaddle/PaddleOCR-VL-1.6",
        "base_url": "http://host.docker.internal:8000/v1",
        "config": {"temperature": 0},  # official recipe uses temperature 0.0
        "icon": "PV",
        "is_active": True,
    },
    # Local dots.ocr served via llmux (llmux profile `dots-ocr`, port 8011 —
    # off the default 8000 which a separate kong container occupies). Outputs
    # layout JSON, converted to markdown by the dots_json_to_md postprocessor.
    {
        "id": "dots-ocr",
        "name": "dots-ocr",
        "display_name": "DotsOCR (dots.ocr)",
        "provider": "custom",
        "model_id": "rednote-hilab/dots.ocr",
        "base_url": "http://host.docker.internal:8011/v1",
        "config": {"temperature": 0, "postprocessor": "dots_json_to_md"},
        "icon": "DO",
        "is_active": True,
    },
]

# dots.ocr official full-document prompt (dots_ocr/utils/prompts.py ::
# prompt_layout_all_en). USER turn, no system message. Output is layout JSON.
DOTS_LAYOUT_PROMPT = """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object.
"""

# Model-specific prompts seeded alongside their model. PaddleOCR-VL expects the
# official task tag ("OCR:") in the user turn and NO system prompt.
SEED_MODEL_PROMPTS = [
    {
        "name": "PaddleOCR-VL Official (OCR:)",
        "model_id": "paddleocr-vl-1-6",
        "prompt_text": "",
        "user_prompt_text": "OCR:",
    },
    {
        "name": "DotsOCR Official (layout_all_en)",
        "model_id": "dots-ocr",
        "prompt_text": "",
        "user_prompt_text": DOTS_LAYOUT_PROMPT,
    },
]

# ── Official benchmark prompts (verbatim from each benchmark's own repo) ──────
#
# OmniDocBench general-VLM prompt: identical across tools/model_infer/
# gpt_4o_inf.py, gpt_5.2_img2md.py, gemini25_img2md.py, internvl2_test_img2md.py,
# Qwen2VL_img2md.py. Sent in the USER turn with NO system message.
OMNI_VLM_PROMPT = r"""You are an AI assistant specialized in converting PDF images to Markdown format. Please follow these instructions for the conversion:

1. Text Processing:
- Accurately recognize all text content in the PDF image without guessing or inferring.
- Convert the recognized text into Markdown format.
- Maintain the original document structure, including headings, paragraphs, lists, etc.

2. Mathematical Formula Processing:
- Convert all mathematical formulas to LaTeX format.
- Enclose inline formulas with \( \). For example: This is an inline formula \( E = mc^2 \)
- Enclose block formulas with \[ \]. For example: \[ \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \]

3. Table Processing:
- Convert tables to HTML format.
- Wrap the entire table with <table> and </table>.

4. Figure Handling:
- Ignore figures content in the PDF image. Do not attempt to describe or convert images.

5. Output Format:
- Ensure the output Markdown document has a clear structure with appropriate line breaks between elements.
- For complex layouts, try to maintain the original document's structure and format as closely as possible.

Please strictly follow these guidelines to ensure accuracy and consistency in the conversion. Your task is to accurately convert the content of the PDF image into Markdown format without adding any extra explanations or comments."""

# olmOCR-Bench prompt: verbatim build_openai_silver_data_prompt_no_document_anchoring
# (olmocr/bench/prompts.py) — the image-only variant shared by run_chatgpt.py,
# run_claude.py, run_gemini.py, run_mistral.py. USER turn, NO system message.
OLMOCR_PROMPT = (
    "Below is the image of one page of a PDF document. "
    "Just return the plain text representation of this document as if you were reading it naturally.\n"
    "Turn equations into a LaTeX representation, and tables into markdown format. Remove the headers and footers, but keep references and footnotes.\n"
    "Read any natural handwriting.\n"
    "This is likely one page out of several in the document, so be sure to preserve any sentences that come from the previous page, or continue onto the next page, exactly as they are.\n"
    "If there is no text at all that you think you should read, you can output null.\n"
    "Do not hallucinate."
)

# General multimodal LLMs use the shared official prompt for each benchmark.
# PaddleOCR-VL is a task-tag model: its official recipe is "OCR:" with no system
# prompt, so it MUST override the general benchmark prompt in both benchmarks.
_GENERAL_VLM_MODEL_IDS = [
    "claude-sonnet", "claude-haiku",
    "gpt-4o", "gpt-4o-mini",
    "gemini-2-flash", "gemini-2-flash-lite",
    "mistral-small",
]
_BENCH_PROMPTS = {
    "omnidocbench": ("OmniDocBench", "", OMNI_VLM_PROMPT),   # (label, system, user)
    "olmocr_bench": ("olmOCR-Bench", "", OLMOCR_PROMPT),
}


def _build_benchmark_prompts() -> list[dict]:
    prompts: list[dict] = []
    for bench, (label, system, user) in _BENCH_PROMPTS.items():
        # Benchmark-wide default (model_id=None) — official general-VLM prompt.
        prompts.append({
            "name": f"{label} Default (official)",
            "benchmark": bench, "model_id": None,
            "prompt_text": system, "user_prompt_text": user,
        })
        # Explicit per-model rows so each model carries its official prompt.
        for mid in _GENERAL_VLM_MODEL_IDS:
            prompts.append({
                "name": f"{label} · {mid}",
                "benchmark": bench, "model_id": mid,
                "prompt_text": system, "user_prompt_text": user,
            })
        # PaddleOCR-VL override: its own official task tag, not the VLM prompt.
        prompts.append({
            "name": f"{label} · PaddleOCR-VL (OCR:)",
            "benchmark": bench, "model_id": "paddleocr-vl-1-6",
            "prompt_text": "", "user_prompt_text": "OCR:",
        })
        # dots.ocr override: its official layout_all_en prompt (outputs layout
        # JSON → converted to markdown by the dots_json_to_md postprocessor).
        prompts.append({
            "name": f"{label} · DotsOCR (layout_all_en)",
            "benchmark": bench, "model_id": "dots-ocr",
            "prompt_text": "", "user_prompt_text": DOTS_LAYOUT_PROMPT,
        })
    return prompts


SEED_BENCHMARK_PROMPTS = _build_benchmark_prompts()


async def seed():
    await init_db()
    settings = get_settings()
    async with async_session() as db:
        # Seed providers
        for pdata in SEED_PROVIDERS:
            existing = await db.execute(
                select(ProviderSetting).where(ProviderSetting.id == pdata["id"])
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Skipping provider {pdata['id']} (already exists)")
                continue
            ps = ProviderSetting(
                **pdata,
                is_enabled=bool(settings.provider_api_key(pdata["provider_type"])),
            )
            db.add(ps)
            logger.info(f"Added provider {pdata['id']}")

        # Seed models
        for model_data in SEED_MODELS:
            existing = await db.execute(
                select(OcrModel).where(OcrModel.id == model_data["id"])
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Skipping {model_data['name']} (already exists)")
                continue
            model = OcrModel(**model_data)
            db.add(model)
            logger.info(f"Added {model_data['name']}")

        # Seed model-specific prompts (benchmark IS NULL — a model may also have
        # separate benchmark-scoped prompts, so scope this check to the model row).
        for mp in SEED_MODEL_PROMPTS:
            existing_mp = await db.execute(
                select(PromptSetting).where(
                    PromptSetting.model_id == mp["model_id"],
                    PromptSetting.benchmark.is_(None),
                )
            )
            if existing_mp.scalar_one_or_none():
                logger.debug(f"Skipping model prompt for {mp['model_id']} (already exists)")
                continue
            db.add(
                PromptSetting(
                    name=mp["name"],
                    prompt_text=mp["prompt_text"],
                    user_prompt_text=mp["user_prompt_text"],
                    model_id=mp["model_id"],
                    is_default=False,
                )
            )
            logger.info(f"Added model prompt for {mp['model_id']}")

        # Seed benchmark-scoped prompts, keyed by (benchmark, model_id).
        for bp in SEED_BENCHMARK_PROMPTS:
            mid = bp["model_id"]
            model_cond = (
                PromptSetting.model_id.is_(None) if mid is None
                else PromptSetting.model_id == mid
            )
            existing_bp = await db.execute(
                select(PromptSetting).where(
                    PromptSetting.benchmark == bp["benchmark"],
                    model_cond,
                )
            )
            if existing_bp.scalar_one_or_none():
                logger.debug(f"Skipping benchmark prompt {bp['name']} (already exists)")
                continue
            db.add(
                PromptSetting(
                    name=bp["name"],
                    prompt_text=bp["prompt_text"],
                    user_prompt_text=bp["user_prompt_text"],
                    benchmark=bp["benchmark"],
                    model_id=mid,
                    is_default=False,
                )
            )
            logger.info(f"Added benchmark prompt {bp['name']}")

        # Seed default prompt
        existing_prompt = await db.execute(select(PromptSetting).where(PromptSetting.is_default))
        if not existing_prompt.scalar_one_or_none():
            default_prompt = PromptSetting(
                name="Default OCR Prompt",
                prompt_text=(
                    "You are a document OCR assistant. Convert the given document image "
                    "into well-formatted markdown text.\n"
                    "Rules:\n"
                    "- Preserve the document structure (headings, lists, tables, etc.)\n"
                    "- Use proper markdown syntax\n"
                    "- For tables, use markdown table format\n"
                    "- Preserve any special formatting (bold, italic, etc.)\n"
                    "- For mathematical formulas, use LaTeX notation with $...$ for inline and $$...$$ for display\n"
                    "- Output only the converted markdown content, no explanations"
                ),
                is_default=True,
            )
            db.add(default_prompt)
            logger.info("Added default prompt")
        else:
            logger.debug("Skipping default prompt (already exists)")

        await db.commit()
    logger.success("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
