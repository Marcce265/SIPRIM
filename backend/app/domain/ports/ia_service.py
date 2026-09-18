from abc import ABC, abstractmethod
from typing import Any, Mapping
from app.domain.value_objects.dictamen_ia import DictamenIA


class IIAService(ABC):
    """Puerto de evaluación; no conoce SDKs ni motores de orquestación."""

    @abstractmethod
    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        raise NotImplementedError
