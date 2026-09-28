from typing import Any, Mapping

from fastapi.testclient import TestClient

from backend.domain.entities.dictamen_ia import DictamenIA
from backend.domain.ports.ia_service_port import IAServicePort
from backend.infrastructure.config.dependencies import (
    get_ia_service,
    get_proyecto_repository,
)
from backend.main import create_app


class FakeIAService(IAServicePort):
    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> DictamenIA:
        return DictamenIA(
            puntaje=78.0,
            viabilidad="ALTA",
            justificacion=(
                f"El proyecto {proyecto['nombre']} presenta una ficha coherente."
            ),
            observaciones=["La evaluacion es preliminar."],
            recomendaciones=["Validar el expediente tecnico."],
        )


def test_evaluacion_ia_por_id_sin_consumir_gemini() -> None:
    get_proyecto_repository.cache_clear()
    app = create_app()
    app.dependency_overrides[get_ia_service] = lambda: FakeIAService()

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/proyectos",
            json={
                "nombre": "Mejoramiento de parque urbano",
                "descripcion": "Recuperacion de espacio publico",
                "ubicacion": "El Tambo - Huancayo",
                "presupuesto": 2_500_000,
                "beneficiarios": 5_000,
                "tipo_proyecto": "Infraestructura urbana",
            },
        )
        proyecto_id = created.json()["proyecto"]["id"]
        response = client.post(
            f"/api/v1/proyectos/{proyecto_id}/evaluacion-ia"
        )

    assert response.status_code == 200
    assert response.json() == {
        "puntaje": 78.0,
        "viabilidad": "ALTA",
        "justificacion": (
            "El proyecto Mejoramiento de parque urbano presenta una ficha coherente."
        ),
        "observaciones": ["La evaluacion es preliminar."],
        "recomendaciones": ["Validar el expediente tecnico."],
    }
    get_proyecto_repository.cache_clear()


def test_evaluacion_ia_bloquea_expediente_incompleto() -> None:
    get_proyecto_repository.cache_clear()
    app = create_app()
    app.dependency_overrides[get_ia_service] = lambda: FakeIAService()

    with TestClient(app) as client:
        client.post("/api/v1/proyectos", json={"nombre": "Proyecto en borrador"})
        response = client.post("/api/v1/proyectos/1/evaluacion-ia")

    assert response.status_code == 409
    assert "descripcion" in response.json()["campos_faltantes"]
    get_proyecto_repository.cache_clear()
