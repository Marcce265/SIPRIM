from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from backend.application.dto.proyecto_dto import (
    EvaluacionEconomicaResponse,
    ProyectoCreate,
    ProyectoResponse,
    RegistrarProyectoResponse,
    ValidacionProyectoResponse,
)
from backend.application.use_cases.evaluar_economia_proyecto import (
    EvaluarEconomiaProyectoUseCase,
)
from backend.application.use_cases.obtener_proyecto import ObtenerProyectoUseCase
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.application.use_cases.validar_proyecto import ValidarProyectoUseCase
from backend.infrastructure.config.dependencies import (
    get_evaluar_economia_proyecto_use_case,
    get_obtener_proyecto_use_case,
    get_registrar_proyecto_use_case,
    get_validar_proyecto_use_case,
)


router = APIRouter(prefix="/api/v1/proyectos", tags=["Proyectos"])


@router.post(
    "",
    response_model=RegistrarProyectoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un proyecto urbano",
)
def registrar_proyecto(
    data: ProyectoCreate,
    use_case: Annotated[
        RegistrarProyectoUseCase, Depends(get_registrar_proyecto_use_case)
    ],
) -> RegistrarProyectoResponse:
    # El controlador adapta HTTP; las reglas y la orquestacion viven fuera de el.
    proyecto = use_case.execute(data)
    return RegistrarProyectoResponse(
        mensaje="Proyecto registrado correctamente",
        proyecto=ProyectoResponse.model_validate(proyecto),
    )


@router.get(
    "/{proyecto_id}",
    response_model=ProyectoResponse,
    summary="Consultar un proyecto por id",
)
def obtener_proyecto(
    proyecto_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[
        ObtenerProyectoUseCase, Depends(get_obtener_proyecto_use_case)
    ],
) -> ProyectoResponse:
    proyecto = use_case.execute(proyecto_id)
    return ProyectoResponse.model_validate(proyecto)


@router.post(
    "/{proyecto_id}/validar",
    response_model=ValidacionProyectoResponse,
    summary="Validar que el expediente este completo",
)
def validar_proyecto(
    proyecto_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[
        ValidarProyectoUseCase, Depends(get_validar_proyecto_use_case)
    ],
) -> ValidacionProyectoResponse:
    return use_case.execute(proyecto_id)


@router.post(
    "/{proyecto_id}/evaluacion-economica",
    response_model=EvaluacionEconomicaResponse,
    summary="Calcular la evaluacion economica parcial",
)
def evaluar_economia_proyecto(
    proyecto_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[
        EvaluarEconomiaProyectoUseCase,
        Depends(get_evaluar_economia_proyecto_use_case),
    ],
) -> EvaluacionEconomicaResponse:
    return use_case.execute(proyecto_id)

