from typing import Any, Mapping
from app.domain.ports.ia_service import IIAService


class FallbackIAService(IIAService):
    def __init__(self, principal: IIAService, fallback: IIAService | None = None) -> None:
        self.principal = principal
        self.fallback = fallback

    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> dict[str, Any]:
        try:
            return await self.principal.generar_dictamen(proyecto)
        except Exception:
            if self.fallback is None:
                raise
            return await self.fallback.generar_dictamen(proyecto)
