from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import authorization_error
from app.models.caregiver import CaregiverPermission
from app.models.user import User, UserRole
from app.repositories.caregiver import CaregiverLinkRepository
from app.repositories.user import UserRepository


class CaregiverAuthorizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.links = CaregiverLinkRepository(session)
        self.users = UserRepository(session)

    async def resolve_patient(
        self,
        actor: User,
        patient_id: UUID | None,
        *,
        required_permission: CaregiverPermission = CaregiverPermission.VIEW_ONLY,
    ) -> User:
        if actor.role is UserRole.PATIENT:
            if patient_id is not None and patient_id != actor.id:
                raise authorization_error()
            return actor
        if actor.role is not UserRole.CAREGIVER or patient_id is None:
            raise authorization_error()
        link = await self.links.get_active(patient_id, actor.id)
        if link is None or not _has_permission(link.permission_level, required_permission):
            raise authorization_error()
        patient = await self.users.get_active_by_id(patient_id)
        if patient is None or patient.role is not UserRole.PATIENT:
            raise authorization_error()
        return patient


def _has_permission(actual: CaregiverPermission, required: CaregiverPermission) -> bool:
    rank = {
        CaregiverPermission.VIEW_ONLY: 1,
        CaregiverPermission.MANAGE_MEDICATIONS: 2,
        CaregiverPermission.FULL_ACCESS: 3,
    }
    return rank[actual] >= rank[required]
