from typing import Any, Mapping
from app.domain.ports.ia_service import IIAService
from app.application.schemas.dictamen_ia import DictamenIA


class EvaluarProyecto:
    def __init__(self, ia_service: IIAService) -> None:
        self.ia_service = ia_service

    async def ejecutar(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        resultado = await self.ia_service.generar_dictamen(proyecto)
        return DictamenIA.model_validate(resultado)
