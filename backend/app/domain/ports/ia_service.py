from abc import ABC, abstractmethod
from typing import Any, Mapping


class IIAService(ABC):
    """Puerto de salida para proveedores de inteligencia artificial."""

    @abstractmethod
    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
