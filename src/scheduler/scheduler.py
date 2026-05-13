from apscheduler.schedulers.blocking import BlockingScheduler

from main import run_all
from src.config import CONFIG
from src.logger import logger


def start_scheduler():
    enabled = CONFIG.get("scheduler", {}).get("enabled", False)
    if not enabled:
        logger.info("Scheduler disabled via config")
        return

    scheduler = BlockingScheduler()

    cron_expr = CONFIG.get("scheduler", {}).get("cron", "0 3 * * *")
    hour, minute = map(int, cron_expr.split()[:2])

    scheduler.add_job(
        run_all,
        "cron",
        hour=hour,
        minute=minute
    )

    logger.info(f"Scheduler started with cron: {cron_expr}")
    scheduler.start()