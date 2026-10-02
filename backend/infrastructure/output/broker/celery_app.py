from celery import Celery

from backend.infrastructure.config.settings import get_settings

settings = get_settings()
celery_app = Celery("siprim", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "siprim.economic.process": {"queue": "economic"},
        "siprim.platform.complete": {"queue": "platform"},
        "siprim.platform.started": {"queue": "platform"},
        "siprim.platform.publish_outbox": {"queue": "platform"},
    },
    beat_schedule={
        "recover-platform-outbox": {
            "task": "siprim.platform.publish_outbox",
            "schedule": 15.0,
        }
    },
)


class CeleryTaskDispatcher:
    def dispatch_economic(self, payload: dict) -> None:
        celery_app.send_task("siprim.economic.process", args=[payload], queue="economic")
