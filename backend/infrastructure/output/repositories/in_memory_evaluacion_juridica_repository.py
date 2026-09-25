from threading import RLock

from backend.domain.entities.evaluacion_juridica import EvaluacionJuridica
from backend.domain.ports.evaluacion_juridica_repository_port import (
    EvaluacionJuridicaRepositoryPort,
)


class InMemoryEvaluacionJuridicaRepository(EvaluacionJuridicaRepositoryPort):
    def __init__(self) -> None:
        self._evaluaciones: dict[int, EvaluacionJuridica] = {}
        self._lock = RLock()

    def guardar(self, evaluacion: EvaluacionJuridica) -> EvaluacionJuridica:
        with self._lock:
            self._evaluaciones[evaluacion.proyecto_id] = evaluacion
            return evaluacion

    def obtener_por_proyecto(self, proyecto_id: int) -> EvaluacionJuridica | None:
        with self._lock:
            return self._evaluaciones.get(proyecto_id)
