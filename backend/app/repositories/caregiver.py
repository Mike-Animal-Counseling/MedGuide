from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caregiver import CaregiverLink, CaregiverLinkStatus
from app.models.user import User
from app.repositories.base import BaseRepository


class CaregiverLinkRepository(BaseRepository[CaregiverLink]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CaregiverLink, session)

    async def get_pending_by_token_hash(self, token_hash: str) -> CaregiverLink | None:
        return cast(
            CaregiverLink | None,
            await self.session.scalar(
                select(CaregiverLink)
                .where(
                    CaregiverLink.invite_token_hash == token_hash,
                    CaregiverLink.status == CaregiverLinkStatus.PENDING,
                )
                .with_for_update()
            ),
        )

    async def get_active(self, patient_id: UUID, caregiver_id: UUID) -> CaregiverLink | None:
        return cast(
            CaregiverLink | None,
            await self.session.scalar(
                select(CaregiverLink).where(
                    CaregiverLink.patient_id == patient_id,
                    CaregiverLink.caregiver_id == caregiver_id,
                    CaregiverLink.status == CaregiverLinkStatus.ACTIVE,
                )
            ),
        )

    async def get_for_patient(self, link_id: UUID, patient_id: UUID) -> CaregiverLink | None:
        return cast(
            CaregiverLink | None,
            await self.session.scalar(
                select(CaregiverLink)
                .where(CaregiverLink.id == link_id, CaregiverLink.patient_id == patient_id)
                .with_for_update()
            ),
        )

    async def get_unrevoked_for_email(
        self, patient_id: UUID, caregiver_email: str
    ) -> CaregiverLink | None:
        return cast(
            CaregiverLink | None,
            await self.session.scalar(
                select(CaregiverLink).where(
                    CaregiverLink.patient_id == patient_id,
                    CaregiverLink.caregiver_email == caregiver_email,
                    CaregiverLink.status != CaregiverLinkStatus.REVOKED,
                )
            ),
        )

    async def list_active_patients(self, caregiver_id: UUID) -> list[tuple[CaregiverLink, User]]:
        rows = await self.session.execute(
            select(CaregiverLink, User)
            .join(User, User.id == CaregiverLink.patient_id)
            .where(
                CaregiverLink.caregiver_id == caregiver_id,
                CaregiverLink.status == CaregiverLinkStatus.ACTIVE,
                User.deleted_at.is_(None),
            )
            .order_by(CaregiverLink.accepted_at.desc())
        )
        return list(rows.tuples())

    async def list_active_for_patient(self, patient_id: UUID) -> list[CaregiverLink]:
        result = await self.session.scalars(
            select(CaregiverLink).where(
                CaregiverLink.patient_id == patient_id,
                CaregiverLink.status == CaregiverLinkStatus.ACTIVE,
                CaregiverLink.caregiver_id.is_not(None),
            )
        )
        return list(result)

    async def revoke(self, link: CaregiverLink) -> None:
        link.status = CaregiverLinkStatus.REVOKED
        link.revoked_at = datetime.now(UTC)
        await self.session.flush()
