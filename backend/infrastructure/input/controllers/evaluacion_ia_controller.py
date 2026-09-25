from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.application.dto.evaluacion_ia_dto import DictamenIAResponse
from backend.application.use_cases.evaluar_proyecto_ia import EvaluarProyectoIAUseCase
from backend.domain.exceptions.ia_exceptions import (
    IAAuthenticationError,
    IAConfigurationError,
    IAError,
    IAGraphError,
    IARateLimitError,
    IATimeoutError,
)
from backend.infrastructure.config.dependencies import get_evaluar_proyecto_ia_use_case


router = APIRouter(prefix="/api/v1/proyectos", tags=["Evaluacion IA"])


@router.post(
    "/{proyecto_id}/evaluacion-ia",
    response_model=DictamenIAResponse,
    summary="Generar un dictamen preliminar con Gemini",
)
async def evaluar_proyecto_ia(
    proyecto_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[
        EvaluarProyectoIAUseCase,
        Depends(get_evaluar_proyecto_ia_use_case),
    ],
) -> DictamenIAResponse:
    try:
        return await use_case.execute(proyecto_id)
    except IAError as exc:
        status_code = 502
        if isinstance(exc, (IAConfigurationError, IAAuthenticationError)):
            status_code = 503
        elif isinstance(exc, IARateLimitError):
            status_code = 429
        elif isinstance(exc, IATimeoutError):
            status_code = 504
        elif isinstance(exc, IAGraphError):
            status_code = 500
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from None
