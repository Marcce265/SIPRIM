from abc import ABC, abstractmethod

from backend.domain.entities.evaluacion_juridica import EvaluacionJuridica
from backend.domain.entities.proyecto import Proyecto


class EvaluacionJuridicaPort(ABC):
    """Puerto que posteriormente sera implementado por el servicio RAG juridico."""

    @abstractmethod
    def evaluar(self, proyecto: Proyecto) -> EvaluacionJuridica:
        raise NotImplementedError
