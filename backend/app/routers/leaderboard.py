from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, OcrModel, Battle, ProviderSetting
from app.models.schemas import LeaderboardEntry, HeadToHeadEntry

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OcrModel).where(OcrModel.is_active == True).order_by(OcrModel.elo.desc())
    )
    models = result.scalars().all()

    # Resolve provider IDs to display names
    provider_ids = {m.provider for m in models}
    prov_result = await db.execute(
        select(ProviderSetting.id, ProviderSetting.display_name)
        .where(ProviderSetting.id.in_(provider_ids))
    )
    provider_names = {row.id: row.display_name for row in prov_result.all()}

    entries = []
    for rank, model in enumerate(models, 1):
        win_rate = 0.0
        if model.total_battles > 0:
            win_rate = round(model.wins / model.total_battles * 100, 1)
        entries.append(
            LeaderboardEntry(
                rank=rank,
                id=model.id,
                name=model.name,
                display_name=model.display_name,
                icon=model.icon,
                provider=provider_names.get(model.provider, model.provider),
                elo=model.elo,
                wins=model.wins,
                losses=model.losses,
                total_battles=model.total_battles,
                win_rate=win_rate,
                avg_latency_ms=round(model.avg_latency_ms, 0),
            )
        )
    return entries


@router.get("/head-to-head", response_model=list[HeadToHeadEntry])
async def get_head_to_head(db: AsyncSession = Depends(get_db)):
    # Normalize pairs so model_a_id < model_b_id to aggregate both directions
    pair_lo = func.min(Battle.model_a_id, Battle.model_b_id).label("pair_lo")
    pair_hi = func.max(Battle.model_a_id, Battle.model_b_id).label("pair_hi")

    # Count wins for the "lo" model (the one with the smaller id string)
    lo_wins = func.count().filter(
        # "lo" was in position A and won, or "lo" was in position B and won
        (
            (Battle.model_a_id < Battle.model_b_id) & (Battle.winner == "a")
        ) | (
            (Battle.model_a_id > Battle.model_b_id) & (Battle.winner == "b")
        )
    ).label("lo_wins")

    hi_wins = func.count().filter(
        (
            (Battle.model_a_id < Battle.model_b_id) & (Battle.winner == "b")
        ) | (
            (Battle.model_a_id > Battle.model_b_id) & (Battle.winner == "a")
        )
    ).label("hi_wins")

    ties = func.count().filter(Battle.winner == "tie").label("ties")
    total = func.count().label("total")

    stmt = (
        select(pair_lo, pair_hi, lo_wins, hi_wins, ties, total)
        .where(Battle.winner.isnot(None))
        .group_by(pair_lo, pair_hi)
    )
    pairs_result = await db.execute(stmt)
    pairs = pairs_result.all()

    if not pairs:
        return []

    # Fetch model names in a single query
    model_ids = set()
    for row in pairs:
        model_ids.add(row.pair_lo)
        model_ids.add(row.pair_hi)

    models_result = await db.execute(
        select(OcrModel.id, OcrModel.display_name).where(OcrModel.id.in_(model_ids))
    )
    name_map = {row.id: row.display_name for row in models_result.all()}

    entries = []
    for row in pairs:
        if row.total > 0:
            entries.append(
                HeadToHeadEntry(
                    model_a_id=row.pair_lo,
                    model_a_name=name_map.get(row.pair_lo, "Unknown"),
                    model_b_id=row.pair_hi,
                    model_b_name=name_map.get(row.pair_hi, "Unknown"),
                    a_wins=row.lo_wins,
                    b_wins=row.hi_wins,
                    ties=row.ties,
                    total=row.total,
                )
            )

    return entries
