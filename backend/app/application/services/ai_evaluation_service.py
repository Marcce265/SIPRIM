from typing import Any, Mapping
from app.domain.ports.ia_service import IIAService
from app.domain.value_objects.dictamen_ia import DictamenIA


class AIEvaluationService(IIAService):
    """Servicio de aplicación; la orquestación concreta vive tras el puerto."""

    def __init__(self, ia_service: IIAService) -> None:
        self.ia_service = ia_service

    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        return await self.ia_service.generar_dictamen(proyecto)
