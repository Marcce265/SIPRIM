from backend.domain.entities.proyecto import Proyecto
from backend.domain.exceptions.proyecto_exceptions import ProyectoNoEncontradoError
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class ObtenerProyectoUseCase:
    def __init__(self, repository: ProyectoRepositoryPort) -> None:
        self._repository = repository

    def execute(self, proyecto_id: int) -> Proyecto:
        proyecto = self._repository.obtener_por_id(proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoError(proyecto_id)
        return proyecto

