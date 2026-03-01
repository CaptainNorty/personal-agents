from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.config import settings

scheduler = AsyncIOScheduler(timezone=settings.timezone)


def start_scheduler() -> None:
    """Start the APScheduler instance."""
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Shut down the APScheduler instance."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


def register_job(func, trigger, **trigger_args) -> None:
    """Register a job with the scheduler."""
    scheduler.add_job(func, trigger, **trigger_args)
    logger.info(f"Registered job: {func.__name__} ({trigger})")
