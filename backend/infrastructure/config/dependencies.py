from functools import lru_cache

from fastapi import Depends

from backend.application.use_cases.evaluar_economia_proyecto import (
    EvaluarEconomiaProyectoUseCase,
)
from backend.application.use_cases.obtener_proyecto import ObtenerProyectoUseCase
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.application.use_cases.validar_proyecto import ValidarProyectoUseCase
from backend.domain.ports.evaluacion_economica_repository_port import (
    EvaluacionEconomicaRepositoryPort,
)
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.output.repositories.in_memory_evaluacion_economica_repository import (
    InMemoryEvaluacionEconomicaRepository,
)
from backend.infrastructure.output.repositories.in_memory_proyecto_repository import (
    InMemoryProyectoRepository,
)


@lru_cache
def get_proyecto_repository() -> ProyectoRepositoryPort:
    """Punto unico donde se elige el adaptador de persistencia."""

    if get_settings().use_in_memory_repository:
        return InMemoryProyectoRepository()

    # Importacion diferida: PostgreSQL solo se prepara si el adaptador esta activo.
    from backend.infrastructure.output.database.session import SessionLocal
    from backend.infrastructure.output.repositories.sqlalchemy_proyecto_repository import (
        SQLAlchemyProyectoRepository,
    )

    return SQLAlchemyProyectoRepository(SessionLocal)


@lru_cache
def get_evaluacion_economica_repository() -> EvaluacionEconomicaRepositoryPort:
    if get_settings().use_in_memory_repository:
        return InMemoryEvaluacionEconomicaRepository()

    from backend.infrastructure.output.database.session import SessionLocal
    from backend.infrastructure.output.repositories.sqlalchemy_evaluacion_economica_repository import (
        SQLAlchemyEvaluacionEconomicaRepository,
    )

    return SQLAlchemyEvaluacionEconomicaRepository(SessionLocal)


def get_registrar_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> RegistrarProyectoUseCase:
    return RegistrarProyectoUseCase(repository)


def get_obtener_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> ObtenerProyectoUseCase:
    return ObtenerProyectoUseCase(repository)


def get_validar_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> ValidarProyectoUseCase:
    return ValidarProyectoUseCase(repository)


def get_evaluar_economia_proyecto_use_case(
    proyecto_repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
    evaluacion_repository: EvaluacionEconomicaRepositoryPort = Depends(
        get_evaluacion_economica_repository
    ),
) -> EvaluarEconomiaProyectoUseCase:
    return EvaluarEconomiaProyectoUseCase(
        proyecto_repository=proyecto_repository,
        evaluacion_repository=evaluacion_repository,
    )

