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
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_platform_service,
)
from backend.main import create_app

PROJECT_ID = UUID("a0000000-0000-4000-a000-00000000000a")
VERSION_ID = UUID("b0000000-0000-4000-a000-00000000000a")
EVALUATION_ID = UUID("d0000000-0000-4000-a000-00000000000a")
EVENT_ID = UUID("e0000000-0000-4000-a000-00000000000a")


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
            "estimated_budget_pen": Decimal("120000.00"),
            "beneficiaries_count": 600,
        }

    def validate_project(self, project_id: UUID) -> dict[str, Any]:
        return {"complete": True, "status": "ready", "missing_fields": [], "message": "Expediente completo"}

    def request_evaluation(self, project_version_id: UUID, actor_id: UUID, idempotency_key: str) -> dict[str, Any]:
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
    assert missing == ["description", "estimated_budget_pen", "beneficiaries_count"]


def test_hu13_formula_documentada_y_sin_retorno_inventado(client: TestClient) -> None:
    cost_a, score_a = EconomicProcessor.calculate(Decimal(120000), 600, Decimal(200), Decimal(500))
    cost_b, score_b = EconomicProcessor.calculate(Decimal(90000), 300, Decimal(200), Decimal(500))
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
