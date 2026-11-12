"""Request-bound processing for serverless; reuses the official idempotent workers."""
from backend.application.services.pmv1_services import (
    CompletionProcessor,
    EconomicProcessor,
    EvaluationStartedProcessor,
)
from backend.infrastructure.config.settings import get_settings


class ServerlessTaskDispatcher:
    def dispatch_economic(self, payload: dict) -> None:
        settings = get_settings()
        EvaluationStartedProcessor(settings.platform_db_url).process(payload["evaluation_id"])
        result = EconomicProcessor(settings.economic_db_url).process(payload)
        CompletionProcessor(settings.platform_db_url).process(result)
