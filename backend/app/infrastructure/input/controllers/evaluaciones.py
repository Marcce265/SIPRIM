from fastapi import APIRouter, HTTPException
from app.application.schemas.dictamen_ia import DictamenIA
from app.application.schemas.proyecto import ProyectoCreate
from app.application.services.ai_evaluation_service import AIEvaluationService
from app.application.use_cases.evaluar_proyecto import EvaluarProyecto
from app.infrastructure.config.settings import get_settings
from app.infrastructure.output.ai.fallback_service import FallbackIAService
from app.infrastructure.output.ai.provider_factory import AIProviderFactory

router = APIRouter(prefix="/api/evaluaciones", tags=["Evaluaciones IA"])


@router.post("", response_model=DictamenIA)
async def evaluar(payload: ProyectoCreate) -> DictamenIA:
    settings = get_settings()
    try:
        principal = AIProviderFactory.crear(settings.ai_provider, settings)
        fallback = None
        if settings.ai_fallback_provider and settings.ai_fallback_provider != settings.ai_provider:
            fallback = AIProviderFactory.crear(settings.ai_fallback_provider, settings)
        proveedor = FallbackIAService(principal, fallback)
        servicio = AIEvaluationService(proveedor)
        return await EvaluarProyecto(servicio).ejecutar(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error de integracion IA: {exc}") from exc
