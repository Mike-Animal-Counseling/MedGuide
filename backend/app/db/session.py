from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    url, engine_options = database_connection_settings(settings)
    return create_async_engine(url, **engine_options)


def database_connection_settings(
    settings: Settings, *, include_pool_options: bool = True
) -> tuple[str, dict[str, object]]:
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        if include_pool_options:
            engine_options.update(
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_pool_max_overflow,
            )
        url, connect_args = _normalize_asyncpg_sslmode(settings.database_url)
        if connect_args:
            engine_options["connect_args"] = connect_args
        return url, engine_options
    return settings.database_url, engine_options


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _normalize_asyncpg_sslmode(database_url: str) -> tuple[str, dict[str, object]]:
    if not database_url.startswith("postgresql+asyncpg"):
        return database_url, {}

    split_url = urlsplit(database_url)
    query_items = parse_qsl(split_url.query, keep_blank_values=True)
    sslmode = next((value for key, value in query_items if key == "sslmode"), None)
    if sslmode is None:
        return database_url, {}

    filtered_query = [(key, value) for key, value in query_items if key != "sslmode"]
    normalized_url = urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(filtered_query),
            split_url.fragment,
        )
    )
    return normalized_url, {"ssl": sslmode != "disable"}
