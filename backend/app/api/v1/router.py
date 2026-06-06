from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.caregivers import router as caregivers_router
from app.api.v1.devices import router as devices_router
from app.api.v1.dose_logs import router as dose_logs_router
from app.api.v1.medications import router as medications_router
from app.api.v1.privacy import router as privacy_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router

router = APIRouter()
router.include_router(ai_router)
router.include_router(auth_router)
router.include_router(caregivers_router)
router.include_router(users_router)
router.include_router(medications_router)
router.include_router(schedules_router)
router.include_router(dose_logs_router)
router.include_router(devices_router)
router.include_router(uploads_router)
router.include_router(privacy_router)
