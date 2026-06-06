from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[ModelType: Base]:
    def __init__(self, model_type: type[ModelType], session: AsyncSession) -> None:
        self.model_type = model_type
        self.session = session

    async def get(self, identity: Any) -> ModelType | None:
        return await self.session.get(self.model_type, identity)

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()
        return instance
