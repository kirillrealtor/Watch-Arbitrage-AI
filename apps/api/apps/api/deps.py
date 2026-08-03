from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from apps.api.infrastructure.database import engine

logger = logging.getLogger("chronoarb.api")

_DB_STATUS_TIMEOUT = 5


async def get_db_status() -> str:
    try:
        async with asyncio.timeout(_DB_STATUS_TIMEOUT):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.commit()
        return "connected"
    except TimeoutError:
        logger.warning("database_status_check_timeout", extra={"timeout_s": _DB_STATUS_TIMEOUT})
        return "unreachable"
    except Exception:
        logger.exception("database_status_check_failed")
        return "unreachable"
