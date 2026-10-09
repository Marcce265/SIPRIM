from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from backend.application.dto.evaluacion_ia_dto import DictamenIAResponse
from backend.application.dto.proyecto_dto import ProyectoCreate, ProyectoResponse, ValidacionProyectoResponse
from backend.application.use_cases.evaluar_proyecto_ia import EvaluarProyectoIAUseCase
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.application.use_cases.validar_proyecto import ValidarProyectoUseCase
from backend.domain.exceptions.ia_exceptions import (
    IAAuthenticationError,
    IAConfigurationError,
    IAError,
    IAGraphError,
    IARateLimitError,
    IATimeoutError,
)
from backend.infrastructure.config.dependencies import (
    get_evaluar_proyecto_ia_use_case,
    get_registrar_proyecto_use_case,
    get_validar_proyecto_use_case,
)
from backend.infrastructure.config.settings import get_settings


router = APIRouter(prefix="/api/v1/proyectos", tags=["Evaluacion IA"])


class DemoIAResponse(BaseModel):
    proyecto: ProyectoResponse
    validacion: ValidacionProyectoResponse
    dictamen: DictamenIAResponse


@router.post("/evaluacion-ia-demo", response_model=DemoIAResponse,
             summary="Demostracion integral y efimera de Gemini")
async def evaluar_demo_ia(
    data: ProyectoCreate,
    registrar: Annotated[RegistrarProyectoUseCase, Depends(get_registrar_proyecto_use_case)],
    validar: Annotated[ValidarProyectoUseCase, Depends(get_validar_proyecto_use_case)],
    evaluar: Annotated[EvaluarProyectoIAUseCase, Depends(get_evaluar_proyecto_ia_use_case)],
) -> DemoIAResponse:
    # Vercel Functions no garantiza memoria compartida entre solicitudes.
    # Este flujo reúne registro, validación y evaluación en una sola invocación.
    if not get_settings().vercel_demo_enabled:
        raise HTTPException(status_code=404, detail="Demostración no habilitada")
    proyecto = registrar.execute(data)
    validacion = validar.execute(proyecto.id)
    try:
        dictamen = await evaluar.execute(proyecto.id)
    except IAError as exc:
        raise _ia_http_error(exc) from None
    return DemoIAResponse(
        proyecto=ProyectoResponse.model_validate(proyecto),
        validacion=validacion,
        dictamen=dictamen,
    )


def _ia_http_error(exc: IAError) -> HTTPException:
    status_code = 502
    if isinstance(exc, (IAConfigurationError, IAAuthenticationError)):
        status_code = 503
    elif isinstance(exc, IARateLimitError):
        status_code = 429
    elif isinstance(exc, IATimeoutError):
        status_code = 504
    elif isinstance(exc, IAGraphError):
        status_code = 500
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


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
        raise _ia_http_error(exc) from None
