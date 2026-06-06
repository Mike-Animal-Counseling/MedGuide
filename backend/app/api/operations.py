import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import (
    HealthChecker,
    get_database_health_checker,
    get_redis_health_checker,
)
from app.core.errors import ServiceUnavailableError
from app.core.observability import MetricsService
from app.schemas.operations import HealthResponse, ReadyResponse

router = APIRouter(tags=["operations"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="medguide-api")


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    database: Annotated[HealthChecker, Depends(get_database_health_checker)],
    redis: Annotated[HealthChecker, Depends(get_redis_health_checker)],
) -> ReadyResponse:
    checks = await asyncio.gather(database.check(), redis.check(), return_exceptions=True)
    services = {
        "database": "available" if not isinstance(checks[0], BaseException) else "unavailable",
        "redis": "available" if not isinstance(checks[1], BaseException) else "unavailable",
    }
    if "unavailable" in services.values():
        raise ServiceUnavailableError("Required services are unavailable", {"services": services})
    return ReadyResponse(status="ready", services={"database": "available", "redis": "available"})


@router.get("/metrics")
async def metrics(request: Request) -> dict[str, dict[str, int]]:
    service = request.app.state.metrics
    if not isinstance(service, MetricsService):
        return {"counters": {}}
    return {"counters": service.snapshot()}
