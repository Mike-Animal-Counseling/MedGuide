from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from anyio import to_thread
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    PasswordHasher,
    TokenManager,
    TokenType,
    authentication_error,
    hash_token,
)
from app.models.user import RefreshToken, User
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.audit import AuditService, NullAuditService


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        password_hasher: PasswordHasher,
        token_manager: TokenManager,
        audit: AuditService | NullAuditService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.password_hasher = password_hasher
        self.token_manager = token_manager
        self.audit = audit or NullAuditService()
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, request: RegisterRequest) -> tuple[User, TokenResponse]:
        if await self.users.email_exists(str(request.email)):
            raise AppError(
                code="email_conflict",
                message="Email is already registered",
                status_code=409,
            )

        password_hash = await to_thread.run_sync(self.password_hasher.hash, request.password)
        user = await self.users.add(
            User(
                email=str(request.email),
                password_hash=password_hash,
                full_name=request.full_name,
                role=request.role,
                timezone=request.timezone,
                accessibility_preferences=request.accessibility_preferences,
            )
        )
        tokens = await self._issue_tokens(user)
        await self.audit.record(
            action="user.registered",
            resource_type="user",
            actor_user_id=user.id,
            target_user_id=user.id,
            resource_id=user.id,
            metadata={"role": user.role.value},
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if not _is_email_conflict(exc):
                raise
            raise AppError(
                code="email_conflict",
                message="Email is already registered",
                status_code=409,
            ) from exc
        await self.session.refresh(user)
        return user, tokens

    async def login(self, request: LoginRequest) -> tuple[User, TokenResponse]:
        user = await self.users.get_active_by_email(str(request.email))
        if user is None:
            await to_thread.run_sync(self.password_hasher.hash, request.password)
            raise authentication_error("Invalid email or password")
        if not await to_thread.run_sync(
            self.password_hasher.verify, request.password, user.password_hash
        ):
            raise authentication_error("Invalid email or password")
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return user, tokens

    async def refresh(self, encoded_refresh_token: str) -> TokenResponse:
        payload = self.token_manager.decode(encoded_refresh_token, TokenType.REFRESH)
        user_id, token_id = _token_identifiers(payload)
        stored_token = await self.refresh_tokens.get_active(
            token_id, hash_token(encoded_refresh_token)
        )
        user = await self.users.get_active_by_id(user_id)
        if stored_token is None or user is None or stored_token.user_id != user.id:
            raise authentication_error("Refresh token is invalid or revoked")

        await self.refresh_tokens.revoke(stored_token)
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def logout(self, encoded_refresh_token: str) -> None:
        payload = self.token_manager.decode(encoded_refresh_token, TokenType.REFRESH)
        _, token_id = _token_identifiers(payload)
        stored_token = await self.refresh_tokens.get_active(
            token_id, hash_token(encoded_refresh_token)
        )
        if stored_token is None:
            raise authentication_error("Refresh token is invalid or revoked")
        await self.refresh_tokens.revoke(stored_token)
        await self.session.commit()

    async def _issue_tokens(self, user: User) -> TokenResponse:
        token_id = uuid4()
        refresh_token = self.token_manager.create_refresh_token(user.id, token_id)
        await self.refresh_tokens.add(
            RefreshToken(
                id=token_id,
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(days=self.settings.refresh_token_expire_days),
            )
        )
        return TokenResponse(
            access_token=self.token_manager.create_access_token(user.id, user.role.value),
            refresh_token=refresh_token,
            access_expires_in=self.settings.access_token_expire_minutes * 60,
            refresh_expires_in=self.settings.refresh_token_expire_days * 86400,
        )


def _token_identifiers(payload: dict[str, object]) -> tuple[UUID, UUID]:
    try:
        return UUID(str(payload["sub"])), UUID(str(payload["jti"]))
    except (KeyError, ValueError) as exc:
        raise authentication_error("Invalid token claims") from exc


def _is_email_conflict(exc: IntegrityError) -> bool:
    error_text = str(exc.orig).casefold()
    return "users.email" in error_text or "ix_users_email" in error_text
