import asyncio
import logging

from sqlalchemy import text
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.database import engine
from app.core.logging import setup_logging

setup_logging("production")
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def init() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e


def main() -> None:
    logger.info("Initializing service")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
