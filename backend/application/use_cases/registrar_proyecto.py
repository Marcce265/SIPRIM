from backend.application.dto.proyecto_dto import ProyectoCreate
from backend.domain.entities.proyecto import Proyecto
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class RegistrarProyectoUseCase:
    """Orquesta el registro sin conocer FastAPI, SQLAlchemy ni PostgreSQL."""

    def __init__(self, repository: ProyectoRepositoryPort) -> None:
        self._repository = repository

    def execute(self, data: ProyectoCreate) -> Proyecto:
        proyecto = Proyecto(
            nombre=data.nombre,
            descripcion=data.descripcion,
            ubicacion=data.ubicacion,
            presupuesto=data.presupuesto,
            beneficiarios=data.beneficiarios,
            tipo_proyecto=data.tipo_proyecto,
        )
        return self._repository.guardar(proyecto)

