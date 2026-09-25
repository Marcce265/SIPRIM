from threading import RLock

from backend.domain.entities.evaluacion_economica import EvaluacionEconomica
from backend.domain.ports.evaluacion_economica_repository_port import (
    EvaluacionEconomicaRepositoryPort,
)


class InMemoryEvaluacionEconomicaRepository(EvaluacionEconomicaRepositoryPort):
    """Almacena una evaluacion economica vigente por proyecto."""

    def __init__(self) -> None:
        self._evaluaciones: dict[int, EvaluacionEconomica] = {}
        self._lock = RLock()

    def guardar(self, evaluacion: EvaluacionEconomica) -> EvaluacionEconomica:
        with self._lock:
            self._evaluaciones[evaluacion.proyecto_id] = evaluacion
            return evaluacion

    def obtener_por_proyecto(
        self, proyecto_id: int
    ) -> EvaluacionEconomica | None:
        with self._lock:
            return self._evaluaciones.get(proyecto_id)
