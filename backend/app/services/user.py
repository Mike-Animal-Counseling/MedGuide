from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.schemas.user import UserUpdateRequest


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def update_current_user(self, user: User, request: UserUpdateRequest) -> User:
        changes = request.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(user, field, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_current_user(self, user: User) -> None:
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.users.soft_delete(user)
        await self.session.commit()
