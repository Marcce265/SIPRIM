from abc import ABC, abstractmethod

from backend.domain.entities.evaluacion_juridica import EvaluacionJuridica


class EvaluacionJuridicaRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, evaluacion: EvaluacionJuridica) -> EvaluacionJuridica:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_proyecto(self, proyecto_id: int) -> EvaluacionJuridica | None:
        raise NotImplementedError
