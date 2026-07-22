import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from extension.backend.config import settings
from extension.backend.database import execute, is_pg

logger = logging.getLogger("capsule.cleanup")

async def prune_old_data():
    logger.info(f"Running data retention cleanup for data older than {settings.DATA_RETENTION_DAYS} days.")
    try:
        if is_pg():
            await execute(f"DELETE FROM pr_analyses WHERE analyzed_at < NOW() - INTERVAL '{settings.DATA_RETENTION_DAYS} days'")
            await execute(f"DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '{settings.DATA_RETENTION_DAYS} days'")
        else:
            await execute(f"DELETE FROM pr_analyses WHERE analyzed_at < datetime('now', '-{settings.DATA_RETENTION_DAYS} days')")
            await execute(f"DELETE FROM audit_log WHERE timestamp < datetime('now', '-{settings.DATA_RETENTION_DAYS} days')")
        logger.info("Data retention cleanup completed.")
    except Exception as e:
        logger.error(f"Error during data cleanup: {e}")

def get_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(prune_old_data, 'cron', hour=0, minute=0) # Run daily at midnight
    return scheduler
