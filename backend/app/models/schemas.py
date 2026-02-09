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


class BattleStartResponse(BaseModel):
    battle_id: str
    document_url: str
    model_a_label: str
    model_b_label: str


class BattleStreamEvent(BaseModel):
    event: str  # "model_a_result", "model_b_result", "error", "done"
    data: str
    latency_ms: int | None = None


class VoteRequest(BaseModel):
    winner: str  # "a", "b", "tie"


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
