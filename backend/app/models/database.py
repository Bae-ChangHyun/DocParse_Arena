from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, Index
from datetime import datetime, timezone
import uuid

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class ProviderSetting(Base):
    __tablename__ = "provider_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    provider_type: Mapped[str] = mapped_column(String, default="")  # claude, openai, ..., custom
    api_key: Mapped[str] = mapped_column(String, default="")
    base_url: Mapped[str] = mapped_column(String, default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class PromptSetting(Base):
    __tablename__ = "prompt_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    model_id: Mapped[str | None] = mapped_column(String, ForeignKey("ocr_models.id"), nullable=True)


class OcrModel(Base):
    __tablename__ = "ocr_models"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, default="🤖")
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, default="")
    base_url: Mapped[str] = mapped_column(String, default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    elo: Mapped[int] = mapped_column(Integer, default=1500)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    total_battles: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Battle(Base):
    __tablename__ = "battles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_path: Mapped[str] = mapped_column(String, nullable=False)
    model_a_id: Mapped[str] = mapped_column(String, ForeignKey("ocr_models.id"))
    model_b_id: Mapped[str] = mapped_column(String, ForeignKey("ocr_models.id"))
    model_a_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_b_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_a_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_b_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner: Mapped[str | None] = mapped_column(String, nullable=True)
    voted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_battles_model_a_id", "model_a_id"),
        Index("ix_battles_model_b_id", "model_b_id"),
        Index("ix_battles_winner", "winner"),
        Index("ix_battles_models_pair", "model_a_id", "model_b_id"),
    )


engine = create_async_engine(get_settings().database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session
