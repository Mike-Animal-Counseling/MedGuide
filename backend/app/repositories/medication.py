from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication
from app.repositories.base import BaseRepository


class MedicationRepository(BaseRepository[Medication]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Medication, session)

    async def list_for_user(self, user_id: UUID) -> list[Medication]:
        result = await self.session.scalars(
            select(Medication)
            .where(Medication.user_id == user_id, Medication.deleted_at.is_(None))
            .order_by(Medication.created_at.desc())
        )
        return list(result)

    async def get_for_user(self, medication_id: UUID, user_id: UUID) -> Medication | None:
        return cast(
            Medication | None,
            await self.session.scalar(
                select(Medication).where(
                    Medication.id == medication_id,
                    Medication.user_id == user_id,
                    Medication.deleted_at.is_(None),
                )
            ),
        )

    async def get_active_record(self, medication_id: UUID) -> Medication | None:
        return cast(
            Medication | None,
            await self.session.scalar(
                select(Medication).where(
                    Medication.id == medication_id,
                    Medication.deleted_at.is_(None),
                )
            ),
        )

    async def soft_delete(self, medication: Medication) -> None:
        medication.deleted_at = datetime.now(UTC)
        medication.active = False
        await self.session.flush()
