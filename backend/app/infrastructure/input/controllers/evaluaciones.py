from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app.application.schemas.dictamen_ia import DictamenIA
from app.application.schemas.proyecto import ProyectoCreate
from app.application.services.ai_evaluation_service import AIEvaluationService
from app.application.use_cases.evaluar_proyecto import EvaluarProyecto
from app.domain.errors import (
    IAError, IAConfigurationError, IAAuthenticationError, IATimeoutError,
    IARateLimitError, IAGraphError,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.output.ai.gemini_adapter import GeminiAdapter

router = APIRouter(prefix="/api/evaluaciones", tags=["Evaluaciones IA"])


def get_evaluar_proyecto() -> EvaluarProyecto:
    settings = get_settings()
    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
    adapter = GeminiAdapter(key, settings.ai_model, settings.ai_timeout_seconds)
    return EvaluarProyecto(AIEvaluationService(adapter))


@router.post("", response_model=DictamenIA, responses={
    429: {"description": "Cuota de IA agotada"},
    502: {"description": "Error del proveedor o dictamen inválido"},
    503: {"description": "IA no configurada o credenciales rechazadas"},
    504: {"description": "Tiempo de espera agotado"},
    500: {"description": "Error interno del flujo"},
})
async def evaluar(
    payload: ProyectoCreate,
    use_case: Annotated[EvaluarProyecto, Depends(get_evaluar_proyecto)],
) -> DictamenIA:
    try:
        return await use_case.ejecutar(payload.model_dump())
    except IAError as exc:
        status = 502
        if isinstance(exc, (IAConfigurationError, IAAuthenticationError)):
            status = 503
        elif isinstance(exc, IATimeoutError):
            status = 504
        elif isinstance(exc, IARateLimitError):
            status = 429
        elif isinstance(exc, IAGraphError):
            status = 500
        raise HTTPException(status_code=status, detail={
            "code": exc.code, "message": exc.message,
        }) from None
    except Exception:
        raise HTTPException(status_code=500, detail={
            "code": "IA_INTERNAL_ERROR", "message": "No se pudo completar la evaluación.",
        }) from None
