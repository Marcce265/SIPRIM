from abc import ABC, abstractmethod
from typing import Any, Mapping

from backend.domain.entities.dictamen_ia import DictamenIA


class IAServicePort(ABC):
    """Puerto de salida para evaluar proyectos sin acoplarse a Gemini."""

    @abstractmethod
    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        raise NotImplementedError
