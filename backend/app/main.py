from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.operations import router as operations_router
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.observability import InMemoryMetricsService, configure_sentry
from app.core.openapi import configure_openapi
from app.db.session import create_database_engine, create_session_factory
from app.services.ocr import create_ocr_provider
from app.services.readiness import DatabaseHealthChecker, RedisHealthChecker
from app.services.storage import create_storage_provider
from app.services.vision import create_vision_provider


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings)
    configure_sentry(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(app_settings)
        redis = Redis.from_url(app_settings.redis_url, decode_responses=True)
        app.state.settings = app_settings
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        app.state.metrics = InMemoryMetricsService()
        app.state.storage_provider = create_storage_provider(app_settings)
        app.state.ocr_provider = create_ocr_provider(app_settings)
        app.state.vision_provider = create_vision_provider(app_settings)
        app.state.database_health_checker = DatabaseHealthChecker(
            engine, app_settings.readiness_timeout_seconds
        )
        app.state.redis_health_checker = RedisHealthChecker(
            redis, app_settings.readiness_timeout_seconds
        )
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        description="Medication assistance API. It does not provide medical advice.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(operations_router)
    app.include_router(api_v1_router, prefix=app_settings.api_v1_prefix)
    configure_openapi(app)
    return app


app = create_app()
