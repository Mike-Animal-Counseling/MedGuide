from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        engine_options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_pool_max_overflow,
        )
    return create_async_engine(settings.database_url, **engine_options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
