from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_active_by_id(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.id == user_id, User.deleted_at.is_(None))
            ),
        )

    async def get_active_by_email(self, email: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.email == email, User.deleted_at.is_(None))
            ),
        )

    async def email_exists(self, email: str) -> bool:
        return (
            await self.session.scalar(select(User.id).where(User.email == email).limit(1))
            is not None
        )

    async def list_active_patients(self) -> list[User]:
        result = await self.session.scalars(
            select(User).where(
                User.role == UserRole.PATIENT,
                User.deleted_at.is_(None),
            )
        )
        return list(result)

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(UTC)
        await self.session.flush()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RefreshToken, session)

    async def get_active(self, token_id: UUID, token_hash: str) -> RefreshToken | None:
        return cast(
            RefreshToken | None,
            await self.session.scalar(
                select(RefreshToken)
                .where(
                    RefreshToken.id == token_id,
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.now(UTC),
                )
                .with_for_update(),
            ),
        )

    async def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
