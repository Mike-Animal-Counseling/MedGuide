from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_verification import AIVerificationEvent
from app.repositories.base import BaseRepository


class AIVerificationEventRepository(BaseRepository[AIVerificationEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIVerificationEvent, session)
