from typing import Any, Mapping
from pydantic import ValidationError
from app.domain.errors import IAInvalidResponseError
from app.domain.ports.ia_service import IIAService
from app.domain.value_objects.dictamen_ia import DictamenIA


class EvaluarProyecto:
    def __init__(self, ia_service: IIAService) -> None:
        self.ia_service = ia_service

    async def ejecutar(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        resultado = await self.ia_service.generar_dictamen(proyecto)
        try:
            return DictamenIA.model_validate(resultado)
        except ValidationError:
            raise IAInvalidResponseError() from None
