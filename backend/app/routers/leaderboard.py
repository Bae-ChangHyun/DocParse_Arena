from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, OcrModel, Battle
from app.models.schemas import LeaderboardEntry, HeadToHeadEntry

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OcrModel).where(OcrModel.is_active == True).order_by(OcrModel.elo.desc())
    )
    models = result.scalars().all()

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
                provider=model.provider,
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
    models_result = await db.execute(
        select(OcrModel).where(OcrModel.is_active == True).order_by(OcrModel.elo.desc())
    )
    models = list(models_result.scalars().all())

    entries = []
    for i, model_a in enumerate(models):
        for model_b in models[i + 1:]:
            battles_result = await db.execute(
                select(
                    func.count().filter(Battle.winner == "a").label("a_wins_as_a"),
                    func.count().filter(Battle.winner == "b").label("b_wins_as_a"),
                    func.count().filter(Battle.winner == "tie").label("ties_as_a"),
                ).where(
                    and_(
                        Battle.model_a_id == model_a.id,
                        Battle.model_b_id == model_b.id,
                        Battle.winner.isnot(None),
                    )
                )
            )
            row_a = battles_result.one()

            battles_result2 = await db.execute(
                select(
                    func.count().filter(Battle.winner == "a").label("a_wins_as_b"),
                    func.count().filter(Battle.winner == "b").label("b_wins_as_b"),
                    func.count().filter(Battle.winner == "tie").label("ties_as_b"),
                ).where(
                    and_(
                        Battle.model_a_id == model_b.id,
                        Battle.model_b_id == model_a.id,
                        Battle.winner.isnot(None),
                    )
                )
            )
            row_b = battles_result2.one()

            a_wins = (row_a[0] or 0) + (row_b[1] or 0)
            b_wins = (row_a[1] or 0) + (row_b[0] or 0)
            ties = (row_a[2] or 0) + (row_b[2] or 0)
            total = a_wins + b_wins + ties

            if total > 0:
                entries.append(
                    HeadToHeadEntry(
                        model_a_id=model_a.id,
                        model_a_name=model_a.display_name,
                        model_b_id=model_b.id,
                        model_b_name=model_b.display_name,
                        a_wins=a_wins,
                        b_wins=b_wins,
                        ties=ties,
                        total=total,
                    )
                )

    return entries
