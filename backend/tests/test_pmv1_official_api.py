from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.application.dto.pmv1_dto import PMV1ProjectCreate
from backend.application.services.pmv1_services import (
    EconomicProcessor,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import ConfiguracionPMV1Error
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_platform_service,
)
from backend.main import create_app

PROJECT_ID = UUID("a0000000-0000-4000-a000-00000000000a")
VERSION_ID = UUID("b0000000-0000-4000-a000-00000000000a")
EVALUATION_ID = UUID("d0000000-0000-4000-a000-00000000000a")
EVENT_ID = UUID("e0000000-0000-4000-a000-00000000000a")
ZONING_REVIEW_ID = UUID("11000000-0000-4000-a000-00000000000a")


class FakeAuth:
    def login(self, email: str, password: str) -> dict[str, Any]:
        return {
            "access_token": "token-prueba",
            "expires_in": 3600,
            "user_id": UUID("10000000-0000-4000-a000-000000000002"),
            "full_name": "Planificador de prueba",
            "roles": ["PLANNER"],
        }

    def decode(self, token: str) -> dict[str, Any]:
        return {
            "sub": "10000000-0000-4000-a000-000000000002",
            "roles": ["PLANNER"],
        }


class FakePlatform:
    def create_project(self, data: PMV1ProjectCreate, actor_id: UUID) -> dict[str, Any]:
        return self.get_project(PROJECT_ID)

    def get_project(self, project_id: UUID) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "code": "PRY-A",
            "version_number": 1,
            "status": "ready",
            "title": "Proyecto A",
            "description": "Prueba PMV1",
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "territorial_data_origin": "declared",
            "estimated_budget_pen": Decimal("120000.00"),
            "beneficiaries_count": 600,
        }

    def validate_project(self, project_id: UUID) -> dict[str, Any]:
        return {
            "complete": True,
            "status": "ready",
            "missing_fields": [],
            "message": "Expediente completo",
        }

    def request_evaluation(
        self, project_version_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        return {
            "evaluation_id": EVALUATION_ID,
            "event_id": EVENT_ID,
            "status": "queued",
            "duplicated": idempotency_key == "repetida",
            "publication_pending": False,
        }

    def get_evaluation(self, evaluation_id: UUID) -> dict[str, Any]:
        return {
            "evaluation_id": evaluation_id,
            "project_version_id": VERSION_ID,
            "criteria_version_id": UUID("c0000000-0000-4000-a000-000000000001"),
            "status": "completed",
            "result": {
                "economic_assessment_id": UUID("f0000000-0000-4000-a000-00000000000a"),
                "cost_per_beneficiary_pen": Decimal("200.00"),
                "score_0_100": Decimal("100.00"),
                "explanation": "presupuesto / beneficiarios",
                "algorithm_version": "economic-cost-per-beneficiary-v1",
            },
        }

    def record_legal_abstention(self, project_id: UUID, actor_id: UUID) -> None:
        return None

    def request_zoning_precheck(
        self, project_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        if idempotency_key == "used-by-other-project":
            raise ConfiguracionPMV1Error(
                "Idempotency-Key ya fue utilizada para otro expediente"
            )
        return {
            "review_id": ZONING_REVIEW_ID,
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "status": "requires_review",
            "compatible": None,
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "territorial_data_origin": "declared",
            "evidence": [],
            "alerts": [
                "No se puede concluir compatibilidad sin evidencia territorial versionada."
            ],
            "limitations": "Sin corpus PDU/PDM oficial ni capa GIS.",
            "requires_human_review": True,
            "duplicated": idempotency_key == "zoning-repeat",
        }


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuth()
    app.dependency_overrides[get_platform_service] = lambda: FakePlatform()
    with TestClient(app) as test_client:
        yield test_client


def test_ruta_oficial_exige_autenticacion(client: TestClient) -> None:
    response = client.get(f"/api/v1/projects/{PROJECT_ID}")
    assert response.status_code == 401


def test_hu11_carga_una_vez_y_encola_evaluacion(client: TestClient) -> None:
    headers = {"Authorization": "Bearer token-prueba"}
    created = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "code": "PRY-A",
            "title": "Proyecto A",
            "description": "Prueba PMV1",
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "estimated_budget_pen": 120000,
            "beneficiaries_count": 600,
        },
    )
    assert created.status_code == 201
    assert created.json()["project_version_id"] == str(VERSION_ID)

    queued = client.post(
        "/api/v1/evaluations",
        headers={**headers, "Idempotency-Key": "solicitud-1"},
        json={"project_version_id": str(VERSION_ID)},
    )
    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    assert queued.json()["duplicated"] is False


def test_hu12_reporta_campos_faltantes_antes_de_persistir() -> None:
    data = PMV1ProjectCreate(title="Proyecto incompleto")
    missing = PlatformService._missing(data)
    assert missing == [
        "description",
        "location",
        "proposed_land_use",
        "estimated_budget_pen",
        "beneficiaries_count",
    ]


def test_hu13_formula_documentada_y_sin_retorno_inventado(client: TestClient) -> None:
    cost_a, score_a = EconomicProcessor.calculate(
        Decimal(120000), 600, Decimal(200), Decimal(500)
    )
    cost_b, score_b = EconomicProcessor.calculate(
        Decimal(90000), 300, Decimal(200), Decimal(500)
    )
    assert (cost_a, score_a) == (Decimal("200.00"), Decimal("100.00"))
    assert (cost_b, score_b) == (Decimal("300.00"), Decimal("66.67"))

    response = client.get(
        f"/api/v1/evaluations/{EVALUATION_ID}",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["socioeconomic_return"] is None


def test_hu110_se_abstiene_sin_fuentes_normativas(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/legal-precheck",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["complies"] is None
    assert body["sources"] == []
    assert body["requires_review"] is True


def test_hu111_zonificacion_se_abstiene_y_exige_evidencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={
            "Authorization": "Bearer token-prueba",
            "Idempotency-Key": "zoning-1",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "requires_review"
    assert body["compatible"] is None
    assert body["evidence"] == []
    assert body["requires_human_review"] is True
    assert "evidencia territorial versionada" in body["alerts"][0]


def test_hu111_requiere_clave_de_idempotencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 422


def test_hu111_no_reutiliza_clave_de_otro_expediente(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={
            "Authorization": "Bearer token-prueba",
            "Idempotency-Key": "used-by-other-project",
        },
    )
    assert response.status_code == 409
    assert "otro expediente" in response.json()["detail"]
