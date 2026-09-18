from dataclasses import replace
from threading import RLock

from backend.domain.entities.proyecto import Proyecto
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class InMemoryProyectoRepository(ProyectoRepositoryPort):
    """Adaptador temporal, seguro para accesos concurrentes del proceso."""

    def __init__(self) -> None:
        self._proyectos: dict[int, Proyecto] = {}
        self._next_id = 1
        self._lock = RLock()

    def guardar(self, proyecto: Proyecto) -> Proyecto:
        with self._lock:
            proyecto_guardado = replace(proyecto, id=self._next_id)
            self._proyectos[self._next_id] = proyecto_guardado
            self._next_id += 1
            return replace(proyecto_guardado)

    def obtener_por_id(self, proyecto_id: int) -> Proyecto | None:
        with self._lock:
            proyecto = self._proyectos.get(proyecto_id)
            return replace(proyecto) if proyecto is not None else None

