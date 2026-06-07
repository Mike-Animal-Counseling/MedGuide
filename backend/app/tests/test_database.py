from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import Environment, Settings
from app.core.dependencies import get_db_session
from app.db.base import Base
from app.db.session import (
    create_database_engine,
    create_session_factory,
    database_connection_settings,
)
from app.repositories.base import BaseRepository
from app.services.readiness import DatabaseHealthChecker


class ExampleRecord(Base):
    __tablename__ = "test_example_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


async def test_database_session_and_repository_use_isolated_database() -> None:
    settings = Settings(
        app_env=Environment.TEST,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        repository = BaseRepository(ExampleRecord, session)
        record = await repository.add(ExampleRecord(name="isolated"))
        await session.commit()
        loaded = await repository.get(record.id)

        assert loaded is not None
        assert loaded.name == "isolated"
        assert (await session.scalar(select(ExampleRecord.name))) == "isolated"

    await DatabaseHealthChecker(engine, timeout_seconds=1).check()
    await engine.dispose()


def test_database_session_dependency_uses_application_session_factory(
    client: TestClient,
) -> None:
    app = client.app
    assert isinstance(app, FastAPI)

    @app.get("/test-session")
    async def test_session(
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> dict[str, bool]:
        return {"is_async_session": isinstance(session, AsyncSession)}

    response = client.get("/test-session")

    assert response.status_code == 200
    assert response.json() == {"is_async_session": True}


def test_database_connection_settings_convert_asyncpg_sslmode() -> None:
    settings = Settings(
        app_env=Environment.TEST,
        database_url=(
            "postgresql+asyncpg://user:secret@db.example/neondb"
            "?sslmode=require&application_name=medguide"
        ),
    )

    url, engine_options = database_connection_settings(settings)

    assert url == "postgresql+asyncpg://user:secret@db.example/neondb?application_name=medguide"
    assert engine_options["connect_args"] == {"ssl": True}


def test_database_connection_settings_preserve_sslmode_disable() -> None:
    settings = Settings(
        app_env=Environment.TEST,
        database_url="postgresql+asyncpg://user:secret@db.example/neondb?sslmode=disable",
    )

    url, engine_options = database_connection_settings(settings)

    assert url == "postgresql+asyncpg://user:secret@db.example/neondb"
    assert engine_options["connect_args"] == {"ssl": False}
