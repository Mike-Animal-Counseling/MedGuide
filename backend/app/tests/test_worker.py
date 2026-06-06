import pytest

from app.services.reminder import ReminderProcessor
from app.worker import _run_locked, celery_app


def test_celery_worker_has_durable_delivery_and_periodic_jobs() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert set(celery_app.conf.beat_schedule) == {
        "dose-reminders-every-minute",
        "dose-escalations-every-minute",
        "image-retention-cleanup-hourly",
    }


async def test_worker_skips_when_distributed_lock_is_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HeldLock:
        async def acquire(self) -> bool:
            return False

    class FakeRedis:
        def lock(self, *args: object, **kwargs: object) -> HeldLock:
            return HeldLock()

        async def aclose(self) -> None:
            return None

    fake_redis = FakeRedis()
    monkeypatch.setattr(
        "app.worker.Redis.from_url",
        lambda *args, **kwargs: fake_redis,
    )
    called = False

    async def operation(processor: ReminderProcessor) -> None:
        nonlocal called
        called = True

    await _run_locked("held-lock", operation)

    assert called is False
