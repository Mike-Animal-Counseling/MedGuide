from datetime import date, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication
from app.models.schedule import DoseLog, DoseStatus, MedicationSchedule
from app.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository[MedicationSchedule]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MedicationSchedule, session)

    async def list_for_user(self, user_id: UUID) -> list[MedicationSchedule]:
        result = await self.session.scalars(
            select(MedicationSchedule)
            .where(MedicationSchedule.user_id == user_id)
            .order_by(MedicationSchedule.created_at.desc())
        )
        return list(result)

    async def list_active_for_range(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[MedicationSchedule]:
        result = await self.session.scalars(
            self._active_query(user_id).where(
                MedicationSchedule.start_date <= end_date,
                (MedicationSchedule.end_date.is_(None))
                | (MedicationSchedule.end_date >= start_date),
            )
        )
        return list(result)

    async def get_for_user(self, schedule_id: UUID, user_id: UUID) -> MedicationSchedule | None:
        return cast(
            MedicationSchedule | None,
            await self.session.scalar(
                select(MedicationSchedule).where(
                    MedicationSchedule.id == schedule_id,
                    MedicationSchedule.user_id == user_id,
                )
            ),
        )

    async def get_record(self, schedule_id: UUID) -> MedicationSchedule | None:
        return cast(
            MedicationSchedule | None,
            await self.session.scalar(
                select(MedicationSchedule).where(MedicationSchedule.id == schedule_id)
            ),
        )

    def _active_query(self, user_id: UUID) -> Select[tuple[MedicationSchedule]]:
        return (
            select(MedicationSchedule)
            .join(Medication, Medication.id == MedicationSchedule.medication_id)
            .where(
                MedicationSchedule.user_id == user_id,
                MedicationSchedule.active.is_(True),
                Medication.active.is_(True),
                Medication.deleted_at.is_(None),
            )
        )


class DoseLogRepository(BaseRepository[DoseLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DoseLog, session)

    async def insert_pending_idempotently(
        self,
        *,
        user_id: UUID,
        medication_id: UUID,
        schedule_id: UUID,
        scheduled_times: list[datetime],
    ) -> None:
        if not scheduled_times:
            return
        values = [
            {
                "user_id": user_id,
                "medication_id": medication_id,
                "schedule_id": schedule_id,
                "scheduled_time": scheduled_time,
            }
            for scheduled_time in scheduled_times
        ]
        dialect_name = self.session.get_bind().dialect.name
        if dialect_name == "postgresql":
            await self.session.execute(
                postgresql_insert(DoseLog)
                .values(values)
                .on_conflict_do_nothing(constraint="uq_dose_logs_schedule_time")
            )
        elif dialect_name == "sqlite":
            await self.session.execute(
                sqlite_insert(DoseLog)
                .values(values)
                .on_conflict_do_nothing(index_elements=["schedule_id", "scheduled_time"])
            )
        else:
            raise RuntimeError(
                f"Unsupported database dialect for idempotent generation: {dialect_name}"
            )

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[DoseLog]:
        conditions = [DoseLog.user_id == user_id]
        if start is not None:
            conditions.append(DoseLog.scheduled_time >= start)
        if end is not None:
            conditions.append(DoseLog.scheduled_time < end)
        result = await self.session.scalars(
            select(DoseLog).where(and_(*conditions)).order_by(DoseLog.scheduled_time)
        )
        return list(result)

    async def get_for_user(self, dose_log_id: UUID, user_id: UUID) -> DoseLog | None:
        return cast(
            DoseLog | None,
            await self.session.scalar(
                select(DoseLog)
                .where(DoseLog.id == dose_log_id, DoseLog.user_id == user_id)
                .with_for_update()
            ),
        )

    async def get_record(self, dose_log_id: UUID) -> DoseLog | None:
        return cast(
            DoseLog | None,
            await self.session.scalar(select(DoseLog).where(DoseLog.id == dose_log_id)),
        )

    async def list_pending_before(self, cutoff: datetime) -> list[DoseLog]:
        result = await self.session.scalars(
            select(DoseLog)
            .where(
                DoseLog.status == DoseStatus.PENDING,
                DoseLog.scheduled_time <= cutoff,
            )
            .order_by(DoseLog.scheduled_time)
        )
        return list(result)
