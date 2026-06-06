import asyncio
from collections.abc import Awaitable, Callable

from celery import Celery  # type: ignore[import-untyped]
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory
from app.services.push_notification import create_notification_provider
from app.services.reminder import ReminderProcessor
from app.services.retention import RetentionCleanupService
from app.services.storage import create_storage_provider

settings = get_settings()
celery_app = Celery("medguide", broker=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dose-reminders-every-minute": {
            "task": "medguide.process_reminders",
            "schedule": 60.0,
        },
        "dose-escalations-every-minute": {
            "task": "medguide.process_escalations",
            "schedule": 60.0,
        },
        "image-retention-cleanup-hourly": {
            "task": "medguide.cleanup_expired_images",
            "schedule": 3600.0,
        },
    },
)


@celery_app.task(name="medguide.process_reminders")  # type: ignore[untyped-decorator]
def process_reminders() -> None:
    asyncio.run(_run_locked("medguide:worker:reminders", ReminderProcessor.process_reminders))


@celery_app.task(name="medguide.process_escalations")  # type: ignore[untyped-decorator]
def process_escalations() -> None:
    asyncio.run(_run_locked("medguide:worker:escalations", ReminderProcessor.process_escalations))


@celery_app.task(name="medguide.cleanup_expired_images")  # type: ignore[untyped-decorator]
def cleanup_expired_images() -> None:
    asyncio.run(_cleanup_locked())


async def _run_locked(
    lock_name: str,
    operation: Callable[[ReminderProcessor], Awaitable[None]],
) -> None:
    worker_settings = Settings()
    redis = Redis.from_url(worker_settings.redis_url, decode_responses=True)
    lock = redis.lock(lock_name, timeout=110, blocking_timeout=1)
    acquired = await lock.acquire()
    if not acquired:
        await redis.aclose()
        return
    engine = create_database_engine(worker_settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            processor = ReminderProcessor(
                session,
                worker_settings,
                create_notification_provider(worker_settings),
            )
            await operation(processor)
    finally:
        await lock.release()
        await redis.aclose()
        await engine.dispose()


async def _cleanup_locked() -> None:
    worker_settings = Settings()
    redis = Redis.from_url(worker_settings.redis_url, decode_responses=True)
    lock = redis.lock("medguide:worker:image-retention", timeout=600, blocking_timeout=1)
    acquired = await lock.acquire()
    if not acquired:
        await redis.aclose()
        return
    engine = create_database_engine(worker_settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            await RetentionCleanupService(
                session, worker_settings, create_storage_provider(worker_settings)
            ).cleanup_expired_images()
    finally:
        await lock.release()
        await redis.aclose()
        await engine.dispose()
