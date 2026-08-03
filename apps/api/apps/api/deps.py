from __future__ import annotations

import asyncio
import logging


logger = logging.getLogger("chronoarb.api")


async def get_db_status() -> str:
    try:
        await asyncio.sleep(0.001)
        return "not_configured"
    except Exception:
        logger.exception("database_status_check_failed")
        return "unreachable"
