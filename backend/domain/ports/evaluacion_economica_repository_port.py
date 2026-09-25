from abc import ABC, abstractmethod

from backend.domain.entities.evaluacion_economica import EvaluacionEconomica


class EvaluacionEconomicaRepositoryPort(ABC):
    """Puerto para persistir el resultado economico sin acoplar la aplicacion."""

    @abstractmethod
    def guardar(self, evaluacion: EvaluacionEconomica) -> EvaluacionEconomica:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_proyecto(
        self, proyecto_id: int
    ) -> EvaluacionEconomica | None:
        raise NotImplementedError
