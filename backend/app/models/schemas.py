from datetime import datetime

from pydantic import BaseModel, field_serializer


def _mask_key(v: str) -> str:
    """Mask API key for safe display: show first 3 + last 4 chars."""
    if not v:
        return ""
    if len(v) > 8:
        return v[:3] + "***" + v[-4:]
    return "***"


class OcrModelOut(BaseModel):
    id: str
    name: str
    display_name: str
    icon: str
    provider: str
    elo: int
    wins: int
    losses: int
    total_battles: int
    avg_latency_ms: float
    is_active: bool

    model_config = {"from_attributes": True}


class OcrModelAdmin(BaseModel):
    id: str
    name: str
    display_name: str
    icon: str
    provider: str
    model_id: str
    api_key: str
    base_url: str
    config: dict = {}
    elo: int
    wins: int
    losses: int
    total_battles: int
    avg_latency_ms: float
    is_active: bool

    model_config = {"from_attributes": True}

    @field_serializer("api_key")
    @classmethod
    def mask_api_key(cls, v: str) -> str:
        return _mask_key(v)


class OcrModelCreate(BaseModel):
    name: str
    display_name: str
    icon: str = "AI"
    provider: str
    model_id: str
    api_key: str = ""
    base_url: str = ""
    config: dict = {}
    is_active: bool = False


class OcrModelUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    icon: str | None = None
    provider: str | None = None
    model_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class ModelOptionsRequest(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""


class ProviderSettingOut(BaseModel):
    id: str
    display_name: str
    provider_type: str
    api_key: str
    base_url: str
    is_enabled: bool

    model_config = {"from_attributes": True}

    @field_serializer("api_key")
    @classmethod
    def mask_api_key(cls, v: str) -> str:
        return _mask_key(v)


class ProviderSettingUpdate(BaseModel):
    display_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    is_enabled: bool | None = None


class BattleStartResponse(BaseModel):
    battle_id: str
    document_url: str
    model_a_label: str
    model_b_label: str


class BattleAbortResponse(BaseModel):
    battle_id: str
    model_a_latency_ms: int
    model_b_latency_ms: int


class BattleStreamEvent(BaseModel):
    event: str
    data: str
    latency_ms: int | None = None


class VoteRequest(BaseModel):
    winner: str


class VoteResponse(BaseModel):
    battle_id: str
    winner: str
    model_a: OcrModelOut
    model_b: OcrModelOut
    model_a_elo_change: int
    model_b_elo_change: int


class LeaderboardEntry(BaseModel):
    rank: int
    id: str
    name: str
    display_name: str
    icon: str
    provider: str
    elo: int
    wins: int
    losses: int
    total_battles: int
    win_rate: float
    avg_latency_ms: float


class HeadToHeadEntry(BaseModel):
    model_a_id: str
    model_a_name: str
    model_b_id: str
    model_b_name: str
    a_wins: int
    b_wins: int
    ties: int
    total: int


class PlaygroundRequest(BaseModel):
    model_id: str


class PlaygroundResponse(BaseModel):
    model_id: str
    model_name: str
    result: str
    latency_ms: int


class PromptSettingOut(BaseModel):
    id: str
    name: str
    prompt_text: str
    user_prompt_text: str = ""
    is_default: bool
    model_id: str | None = None
    benchmark: str | None = None

    model_config = {"from_attributes": True}


class PromptSettingCreate(BaseModel):
    name: str
    prompt_text: str
    user_prompt_text: str = ""
    is_default: bool = False
    model_id: str | None = None
    benchmark: str | None = None


class PromptSettingUpdate(BaseModel):
    name: str | None = None
    prompt_text: str | None = None
    user_prompt_text: str | None = None
    is_default: bool | None = None
    model_id: str | None = None
    benchmark: str | None = None


class AdminLoginRequest(BaseModel):
    password: str


class ImageSettingOut(BaseModel):
    enabled: bool
    max_width: int
    max_height: int


class ImageSettingUpdate(BaseModel):
    enabled: bool | None = None
    max_width: int | None = None
    max_height: int | None = None


class OcrResult(BaseModel):
    text: str
    latency_ms: int
    error: str | None = None


# ── Benchmark collections & batch runs ───────────────────────
class CollectionCreate(BaseModel):
    name: str
    description: str = ""


class CollectionDocumentOut(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size: int

    model_config = {"from_attributes": True}


class CollectionOut(BaseModel):
    id: str
    name: str
    description: str
    kind: str = "user"
    created_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class BatchRunCreate(BaseModel):
    collection_id: str
    model_ids: list[str]


class BatchRunOut(BaseModel):
    id: str
    collection_id: str
    status: str
    total: int
    completed: int
    benchmark_kind: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfficialBenchmarkOut(BaseModel):
    kind: str
    name: str
    downloaded: bool
    document_count: int
    collection_id: str | None = None


class BatchRunItemOut(BaseModel):
    document_id: str
    model_id: str
    status: str
    result_text: str | None = None
    latency_ms: int | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class BatchRunDetail(BaseModel):
    id: str
    collection_id: str
    status: str
    total: int
    completed: int
    created_at: datetime
    benchmark_kind: str | None = None
    summary_scores: dict = {}
    documents: list[CollectionDocumentOut]
    model_ids: list[str]
    items: list[BatchRunItemOut]
