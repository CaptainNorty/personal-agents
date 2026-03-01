from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

import app.db  # noqa: F401 — registers models with Base.metadata
from app.bots.nutrition.scheduler import register_nutrition_jobs
from app.bots.podcast.scheduler import register_podcast_jobs
from app.bots.social.scheduler import register_social_jobs
from app.common.scheduler import start_scheduler, stop_scheduler
from app.common.telegram import register_webhooks
from app.db.session import create_tables
from app.webhooks.telegram import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    await create_tables()
    await register_webhooks()
    register_podcast_jobs()
    register_nutrition_jobs()
    register_social_jobs()
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Shut down complete")


app = FastAPI(title="Personal Agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
