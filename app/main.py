from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_session

app = FastAPI(title="Devor")


@app.get("/health")
async def health(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    result: dict[str, Any] = {"status": "ok", "db": "ok", "redis": "ok"}
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        result["db"] = "error"
    try:
        await redis.ping()
    except Exception:
        result["redis"] = "error"
    if "error" in (result["db"], result["redis"]):
        result["status"] = "degraded"
        return JSONResponse(result, status_code=503)
    return JSONResponse(result)
