"""Seed the database with initial OCR models and provider settings."""
import asyncio
from app.models.database import init_db, async_session, OcrModel, ProviderSetting, PromptSetting
from sqlalchemy import select

SEED_PROVIDERS = [
    {"id": "claude", "display_name": "Anthropic Claude", "provider_type": "claude"},
    {"id": "openai", "display_name": "OpenAI", "provider_type": "openai"},
    {"id": "gemini", "display_name": "Google Gemini", "provider_type": "gemini"},
    {"id": "mistral", "display_name": "Mistral AI", "provider_type": "mistral"},
    {"id": "ollama", "display_name": "Ollama (Local)", "provider_type": "ollama", "base_url": "http://localhost:11434"},
]

SEED_MODELS = [
    {
        "id": "claude-sonnet",
        "name": "claude-sonnet",
        "display_name": "Claude Sonnet 4",
        "provider": "claude",
        "model_id": "claude-sonnet-4-20250514",
        "icon": "🟠",
        "is_active": False,
    },
    {
        "id": "claude-haiku",
        "name": "claude-haiku",
        "display_name": "Claude Haiku 3.5",
        "provider": "claude",
        "model_id": "claude-haiku-4-5-20251001",
        "icon": "🟡",
        "is_active": False,
    },
    {
        "id": "gpt-4o",
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
        "icon": "🟢",
        "is_active": False,
    },
    {
        "id": "gpt-4o-mini",
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "icon": "🔵",
        "is_active": False,
    },
    {
        "id": "gemini-2-flash",
        "name": "gemini-2-flash",
        "display_name": "Gemini 2.0 Flash",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash",
        "icon": "🔴",
        "is_active": False,
    },
    {
        "id": "gemini-2-flash-lite",
        "name": "gemini-2-flash-lite",
        "display_name": "Gemini 2.0 Flash Lite",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash-lite",
        "icon": "🩷",
        "is_active": False,
    },
    {
        "id": "mistral-small",
        "name": "mistral-small",
        "display_name": "Mistral Small",
        "provider": "mistral",
        "model_id": "mistral-small-latest",
        "icon": "🟣",
        "is_active": False,
    },
    {
        "id": "llava",
        "name": "llava",
        "display_name": "LLaVA (Ollama)",
        "provider": "ollama",
        "model_id": "llava",
        "icon": "⚪",
        "is_active": False,
    },
]


async def seed():
    await init_db()
    async with async_session() as db:
        # Seed providers
        for pdata in SEED_PROVIDERS:
            existing = await db.execute(
                select(ProviderSetting).where(ProviderSetting.id == pdata["id"])
            )
            if existing.scalar_one_or_none():
                print(f"  Skipping provider {pdata['id']} (already exists)")
                continue
            ps = ProviderSetting(**pdata)
            db.add(ps)
            print(f"  Added provider {pdata['id']}")

        # Seed models
        for model_data in SEED_MODELS:
            existing = await db.execute(
                select(OcrModel).where(OcrModel.id == model_data["id"])
            )
            if existing.scalar_one_or_none():
                print(f"  Skipping {model_data['name']} (already exists)")
                continue
            model = OcrModel(**model_data)
            db.add(model)
            print(f"  Added {model_data['name']}")

        # Seed default prompt
        existing_prompt = await db.execute(
            select(PromptSetting).where(PromptSetting.is_default == True)
        )
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
            print("  Added default prompt")
        else:
            print("  Skipping default prompt (already exists)")

        await db.commit()
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
