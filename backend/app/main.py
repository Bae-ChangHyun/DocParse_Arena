import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import init_db
from app.routers import battle, leaderboard, playground, documents, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("docparse-arena")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    settings = get_settings()
    if not settings.admin_password:
        logger.warning(
            "ADMIN_PASSWORD is not set — admin endpoints are unprotected. "
            "Set ADMIN_PASSWORD in .env for production use."
        )

    yield


app = FastAPI(title="DocParse Arena", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.public_router)
app.include_router(battle.router)
app.include_router(leaderboard.router)
app.include_router(playground.router)
app.include_router(documents.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
