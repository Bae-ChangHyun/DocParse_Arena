"""Seed the database with initial OCR models."""
import asyncio
from app.models.database import init_db, async_session, OcrModel
from sqlalchemy import select

SEED_MODELS = [
    {
        "id": "claude-sonnet",
        "name": "claude-sonnet",
        "display_name": "Claude Sonnet 4",
        "provider": "claude",
        "model_id": "claude-sonnet-4-20250514",
        "icon": "🟠",
    },
    {
        "id": "claude-haiku",
        "name": "claude-haiku",
        "display_name": "Claude Haiku 3.5",
        "provider": "claude",
        "model_id": "claude-haiku-4-5-20251001",
        "icon": "🟡",
    },
    {
        "id": "gpt-4o",
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
        "icon": "🟢",
    },
    {
        "id": "gpt-4o-mini",
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "icon": "🔵",
    },
    {
        "id": "gemini-2-flash",
        "name": "gemini-2-flash",
        "display_name": "Gemini 2.0 Flash",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash",
        "icon": "🔴",
    },
    {
        "id": "gemini-2-flash-lite",
        "name": "gemini-2-flash-lite",
        "display_name": "Gemini 2.0 Flash Lite",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash-lite",
        "icon": "🩷",
    },
    {
        "id": "mistral-small",
        "name": "mistral-small",
        "display_name": "Mistral Small",
        "provider": "mistral",
        "model_id": "mistral-small-latest",
        "icon": "🟣",
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

        await db.commit()
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
