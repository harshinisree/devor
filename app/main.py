from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.errors import register_error_handlers
from app.core.redis import get_redis
from app.db.session import get_session

app = FastAPI(title="Devor")
register_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/livez")
async def livez() -> dict[str, str]:
    return {"status": "ok"}


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
