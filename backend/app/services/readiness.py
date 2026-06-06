import asyncio
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class DatabaseHealthChecker:
    engine: AsyncEngine
    timeout_seconds: float

    async def check(self) -> None:
        async with asyncio.timeout(self.timeout_seconds):
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))


@dataclass(frozen=True)
class RedisHealthChecker:
    client: Redis
    timeout_seconds: float

    async def check(self) -> None:
        async with asyncio.timeout(self.timeout_seconds):
            await self.client.ping()
