from typing import Any

from backend.application.services.pmv1_services import (
    CompletionProcessor,
    EconomicProcessor,
    EvaluationStartedProcessor,
    OutboxPublisher,
)
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.output.broker.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="siprim.economic.process",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_economic(self, payload: dict[str, Any]) -> dict[str, Any]:
    celery_app.send_task(
        "siprim.platform.started", args=[payload["evaluation_id"]], queue="platform"
    )
    completion = EconomicProcessor(get_settings().economic_db_url).process(payload)
    celery_app.send_task(
        "siprim.platform.complete", args=[completion], queue="platform"
    )
    return completion


@celery_app.task(
    bind=True,
    name="siprim.platform.complete",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def complete_economic(self, payload: dict[str, Any]) -> None:
    CompletionProcessor(get_settings().platform_db_url).process(payload)


@celery_app.task(name="siprim.platform.started")
def mark_evaluation_started(evaluation_id: str) -> None:
    EvaluationStartedProcessor(get_settings().platform_db_url).process(evaluation_id)


@celery_app.task(name="siprim.platform.publish_outbox")
def publish_outbox() -> int:
    from backend.infrastructure.output.broker.celery_app import CeleryTaskDispatcher

    return OutboxPublisher(
        get_settings().platform_db_url, CeleryTaskDispatcher()
    ).publish_pending()
