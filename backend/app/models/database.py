import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)  # system prompt
    user_prompt_text: Mapped[str] = mapped_column(Text, default="", server_default="")  # user-turn text
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    model_id: Mapped[str | None] = mapped_column(String, ForeignKey("ocr_models.id"), nullable=True)
    # Scopes this prompt to an official benchmark ("omnidocbench"/"olmocr_bench").
    # None = applies to normal battle/playground/user runs.
    benchmark: Mapped[str | None] = mapped_column(String, nullable=True)


class OcrModel(Base):
    __tablename__ = "ocr_models"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, default="AI")
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


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    # "user" (uploaded) | "omnidocbench" | "olmocr_bench" (official, ground-truth scored)
    kind: Mapped[str] = mapped_column(String, default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CollectionDocument(Base):
    __tablename__ = "collection_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id: Mapped[str] = mapped_column(String, ForeignKey("collections.id"), nullable=False)
    # For user collections: relative to batch_uploads_dir.
    # For official collections: relative to benchmarks_dir/<kind>/.
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    # Ground-truth mapping key for official benchmarks:
    #  - omnidocbench: the GT image key (matches OmniDocBench.json)
    #  - olmocr_bench: the pdf basename (e.g. "multi_column_miss.pdf")
    gt_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_collection_documents_collection_id", "collection_id"),)


class BatchRun(Base):
    __tablename__ = "batch_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id: Mapped[str] = mapped_column(String, ForeignKey("collections.id"), nullable=False)
    model_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending/running/scoring/done/failed
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    # Official benchmark this run scores against (None for plain user collections)
    benchmark_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    # Per-model normalized official scores: {model_id: {...metrics...}}
    summary_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_batch_runs_collection_id", "collection_id"),)


class BatchRunItem(Base):
    __tablename__ = "batch_run_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_run_id: Mapped[str] = mapped_column(String, ForeignKey("batch_runs.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("collection_documents.id"))
    model_id: Mapped[str] = mapped_column(String, ForeignKey("ocr_models.id"))
    status: Mapped[str] = mapped_column(String, default="pending")  # pending/running/done/error
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_batch_run_items_batch_run_id", "batch_run_id"),
        Index(
            "ix_batch_run_items_unique",
            "batch_run_id",
            "document_id",
            "model_id",
            unique=True,
        ),
    )


engine = create_async_engine(get_settings().database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _migrate_add_columns(conn) -> None:
    """Additive, idempotent column migrations for SQLite (no Alembic in use)."""
    from sqlalchemy import text

    def _cols(table: str) -> set[str]:
        return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}

    def _add(table: str, col: str, ddl: str) -> None:
        if col not in _cols(table):
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    _add("prompt_settings", "user_prompt_text", "user_prompt_text TEXT DEFAULT ''")
    _add("prompt_settings", "benchmark", "benchmark VARCHAR")
    _add("collections", "kind", "kind VARCHAR DEFAULT 'user'")
    _add("collection_documents", "gt_ref", "gt_ref VARCHAR")
    _add("batch_runs", "benchmark_kind", "benchmark_kind VARCHAR")
    _add("batch_runs", "summary_scores", "summary_scores JSON DEFAULT '{}'")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_add_columns)


async def get_db():
    async with async_session() as session:
        yield session
