import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.models.database import init_db
from app.routers import battle, leaderboard, playground, documents, admin

# Configure loguru: remove default handler, add custom format
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> [<level>{level}</level>] <cyan>{name}</cyan>: {message}",
    level="INFO",
)


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


settings = get_settings()

app = FastAPI(
    title="DocParse Arena",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
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
