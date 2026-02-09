from pydantic import BaseModel
from datetime import datetime


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
    elo: int
    wins: int
    losses: int
    total_battles: int
    avg_latency_ms: float
    is_active: bool

    model_config = {"from_attributes": True}


class OcrModelCreate(BaseModel):
    name: str
    display_name: str
    icon: str = "🤖"
    provider: str
    model_id: str
    api_key: str = ""
    base_url: str = ""
    is_active: bool = True


class OcrModelUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    icon: str | None = None
    provider: str | None = None
    model_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    is_active: bool | None = None


class ProviderSettingOut(BaseModel):
    id: str
    display_name: str
    api_key: str
    base_url: str
    is_enabled: bool

    model_config = {"from_attributes": True}


class ProviderSettingUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    is_enabled: bool | None = None


class BattleStartResponse(BaseModel):
    battle_id: str
    document_url: str
    model_a_label: str
    model_b_label: str


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


class OcrResult(BaseModel):
    text: str
    latency_ms: int
    error: str | None = None
