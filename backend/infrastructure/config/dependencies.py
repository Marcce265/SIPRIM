from functools import lru_cache

from fastapi import Depends

from backend.application.use_cases.obtener_proyecto import ObtenerProyectoUseCase
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort
from backend.infrastructure.config.settings import get_settings
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


def get_registrar_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> RegistrarProyectoUseCase:
    return RegistrarProyectoUseCase(repository)


def get_obtener_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> ObtenerProyectoUseCase:
    return ObtenerProyectoUseCase(repository)

