import pytest
from app.domain.ports.ia_service import IIAService
from app.infrastructure.output.ai.fallback_service import FallbackIAService


class Falla(IIAService):
    async def generar_dictamen(self, proyecto):
        raise RuntimeError("fallo")


class Funciona(IIAService):
    async def generar_dictamen(self, proyecto):
        return {
            "puntaje": 80,
            "viabilidad": "ALTA",
            "justificacion": "Respuesta simulada valida para pruebas unitarias.",
            "observaciones": [],
            "recomendaciones": [],
        }


@pytest.mark.asyncio
async def test_usa_fallback_si_falla_principal():
    service = FallbackIAService(Falla(), Funciona())
    resultado = await service.generar_dictamen({"nombre": "Prueba"})
    assert resultado["puntaje"] == 80
