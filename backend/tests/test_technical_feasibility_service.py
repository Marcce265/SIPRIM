from decimal import Decimal
from uuid import UUID, uuid4
import psycopg
from psycopg.rows import dict_row
import pytest

from backend.application.services.pmv1_services import (
    TechnicalFeasibilityEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import (
    VersionNoPertenecienteError,
    RecursoPMV1NoEncontradoError,
    ConfiguracionPMV1Error,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")  # PRY-A (Cumple)
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")  # PRY-B (Info insuficiente)
PROJECT_C_ID = UUID("a0000000-0000-4000-a000-00000000000c")  # PRY-C (Observado)
PROJECT_D_ID = UUID("a0000000-0000-4000-a000-00000000000d")  # PRY-D (Info insuficiente total)
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


def get_test_db_url() -> str:
    settings = get_settings()
    return settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def get_test_platform_service() -> PlatformService:
    return PlatformService(
        db_url=get_test_db_url(),
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )


# ==============================================================================
# 1. Pruebas unitarias de motor (TechnicalFeasibilityEngine)
# ==============================================================================

def test_engine_criterion_soil_mechanics_compliant():
    meta = TechnicalFeasibilityEngine.CANONICAL_CRITERIA[0]  # mecanica_suelos
    row = {
        "has_sufficient_data": True,
        "parameter_name": "Capacidad portante admisible q_adm",
        "parameter_value_numeric": 1.45,
        "parameter_unit": "kg/cm²",
        "supporting_document": "Informe Técnico N.° 048-2026-EMS/MDT",
        "source_origin": "simulated",
        "is_simulated": True,
    }
    item = TechnicalFeasibilityEngine.evaluate_criterion(meta, row)
    assert item["status"] == "cumple"
    assert item["status_label"] == "Cumple"
    assert item["correction_guidance"] is None
    assert "1.45" in item["explanation"]


def test_engine_criterion_soil_mechanics_observed():
    meta = TechnicalFeasibilityEngine.CANONICAL_CRITERIA[0]  # mecanica_suelos
    row = {
        "has_sufficient_data": True,
        "parameter_name": "Capacidad portante admisible q_adm",
        "parameter_value_numeric": 0.65,
        "parameter_unit": "kg/cm²",
        "supporting_document": "Informe Geotécnico N.° 014-2026-GEO",
        "source_origin": "simulated",
        "is_simulated": True,
    }
    item = TechnicalFeasibilityEngine.evaluate_criterion(meta, row)
    assert item["status"] == "observado"
    assert item["status_label"] == "Observado"
    assert item["correction_guidance"] is not None
    assert "cimentación profunda" in item["correction_guidance"]


def test_engine_criterion_insufficient_data():
    meta = TechnicalFeasibilityEngine.CANONICAL_CRITERIA[1]  # servicios_basicos
    row = {
        "has_sufficient_data": False,
        "parameter_value_numeric": None,
    }
    item = TechnicalFeasibilityEngine.evaluate_criterion(meta, row)
    assert item["status"] == "informacion_insuficiente"
    assert item["status_label"] == "Información insuficiente"
    assert item["correction_guidance"] is not None
    assert "SEDAM Huancayo" in item["correction_guidance"]


def test_engine_evaluate_all_compliant():
    params = [
        {"criterion_code": "mecanica_suelos", "has_sufficient_data": True, "parameter_value_numeric": 1.5, "parameter_unit": "kg/cm²", "supporting_document": "Doc 1"},
        {"criterion_code": "servicios_basicos", "has_sufficient_data": True, "parameter_value_numeric": 20.0, "parameter_unit": "m", "supporting_document": "Doc 2"},
        {"criterion_code": "topografia_taludes", "has_sufficient_data": True, "parameter_value_numeric": 5.0, "parameter_unit": "%", "supporting_document": "Doc 3"},
        {"criterion_code": "dimensionamiento_predio", "has_sufficient_data": True, "parameter_value_numeric": 500.0, "parameter_unit": "m²", "supporting_document": "Doc 4"},
    ]
    res = TechnicalFeasibilityEngine.evaluate(uuid4(), "PRY-TEST", uuid4(), 1, params)
    assert res["overall_result"] == "cumple"
    assert res["is_viable"] is True
    assert res["technical_score"] == 100.0
    assert res["criteria_summary"]["total"] == 4
    assert res["criteria_summary"]["cumple"] == 4
    assert res["criteria_summary"]["observado"] == 0
    assert res["criteria_summary"]["informacion_insuficiente"] == 0
    assert "opinión preliminar automatizada" in res["disclaimer"].lower()


def test_engine_evaluate_observed_fails_viability():
    params = [
        {"criterion_code": "mecanica_suelos", "has_sufficient_data": True, "parameter_value_numeric": 0.70, "parameter_unit": "kg/cm²", "supporting_document": "Doc 1"},
        {"criterion_code": "servicios_basicos", "has_sufficient_data": True, "parameter_value_numeric": 20.0, "parameter_unit": "m", "supporting_document": "Doc 2"},
        {"criterion_code": "topografia_taludes", "has_sufficient_data": True, "parameter_value_numeric": 5.0, "parameter_unit": "%", "supporting_document": "Doc 3"},
        {"criterion_code": "dimensionamiento_predio", "has_sufficient_data": True, "parameter_value_numeric": 500.0, "parameter_unit": "m²", "supporting_document": "Doc 4"},
    ]
    res = TechnicalFeasibilityEngine.evaluate(uuid4(), "PRY-TEST", uuid4(), 1, params)
    assert res["overall_result"] == "observado"
    assert res["is_viable"] is False
    assert res["technical_score"] == 75.0  # 3 de 4 cumplen
    assert res["criteria_summary"]["observado"] == 1


def test_engine_evaluate_insufficient_data_score_is_strictly_none():
    """Cero falsos positivos: si falta información, el puntaje técnico DEBE ser None (CA-HU1.8-03)."""
    params = [
        {"criterion_code": "mecanica_suelos", "has_sufficient_data": False, "parameter_value_numeric": None},
        {"criterion_code": "servicios_basicos", "has_sufficient_data": True, "parameter_value_numeric": 20.0, "parameter_unit": "m", "supporting_document": "Doc 2"},
        {"criterion_code": "topografia_taludes", "has_sufficient_data": True, "parameter_value_numeric": 5.0, "parameter_unit": "%", "supporting_document": "Doc 3"},
        {"criterion_code": "dimensionamiento_predio", "has_sufficient_data": True, "parameter_value_numeric": 500.0, "parameter_unit": "m²", "supporting_document": "Doc 4"},
    ]
    res = TechnicalFeasibilityEngine.evaluate(uuid4(), "PRY-TEST", uuid4(), 1, params)
    assert res["overall_result"] == "informacion_insuficiente"
    assert res["is_viable"] is False
    assert res["technical_score"] is None
    assert "no determinado" in res["score_explanation"].lower()


# ==============================================================================
# 2. Pruebas de integración con base de datos (PlatformService)
# ==============================================================================

def test_evaluate_pry_a_fully_compliant():
    service = get_test_platform_service()
    res = service.evaluate_technical_feasibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
    )
    assert res["overall_result"] == "cumple"
    assert res["is_viable"] is True
    assert res["technical_score"] == 100.0
    assert res["criteria_summary"]["cumple"] == 4
    assert res["criteria_summary"]["observado"] == 0
    assert res["criteria_summary"]["informacion_insuficiente"] == 0
    assert "ADVERTENCIA DE CONTROL" in res["disclaimer"]
    assert "preliminar" in res["dimension_conclusion"].lower()

    # Comprobar evento de auditoría
    with psycopg.connect(get_test_db_url(), row_factory=dict_row) as conn:
        audit = conn.execute(
            """
            SELECT * FROM audit_events
            WHERE action = 'TECHNICAL_ASSESSMENT_COMPLETED'
              AND (details->>'project_id') = %s
            ORDER BY occurred_at DESC LIMIT 1
            """,
            (str(PROJECT_A_ID),),
        ).fetchone()
        assert audit is not None
        assert audit["details"]["overall_result"] == "cumple"


def test_evaluate_pry_c_with_observations():
    service = get_test_platform_service()
    res = service.evaluate_technical_feasibility(
        project_id=PROJECT_C_ID,
        actor_id=PLANNER_ID,
    )
    assert res["overall_result"] == "observado"
    assert res["is_viable"] is False
    assert res["criteria_summary"]["observado"] == 2  # suelos y servicios
    assert res["criteria_summary"]["cumple"] == 2
    assert res["technical_score"] == 50.0  # 2/4 = 50%

    # Verificar que los criterios observados contienen motivo y acción requerida
    criteria_map = {c["criterion_code"]: c for c in res["criteria"]}
    soil = criteria_map["mecanica_suelos"]
    assert soil["status"] == "observado"
    assert "0.65" in soil["explanation"]
    assert soil["correction_guidance"] is not None
    assert "cimentación profunda" in soil["correction_guidance"]

    services = criteria_map["servicios_basicos"]
    assert services["status"] == "observado"
    assert "145" in services["explanation"]
    assert services["correction_guidance"] is not None


def test_evaluate_pry_b_and_d_insufficient_information():
    service = get_test_platform_service()

    # PRY-B tiene 2 criterios insuficientes
    res_b = service.evaluate_technical_feasibility(
        project_id=PROJECT_B_ID,
        actor_id=PLANNER_ID,
    )
    assert res_b["overall_result"] == "informacion_insuficiente"
    assert res_b["is_viable"] is False
    assert res_b["technical_score"] is None
    assert res_b["criteria_summary"]["informacion_insuficiente"] == 2

    # PRY-D tiene 4 criterios insuficientes
    res_d = service.evaluate_technical_feasibility(
        project_id=PROJECT_D_ID,
        actor_id=PLANNER_ID,
    )
    assert res_d["overall_result"] == "informacion_insuficiente"
    assert res_d["is_viable"] is False
    assert res_d["technical_score"] is None
    assert res_d["criteria_summary"]["informacion_insuficiente"] == 4


def test_idempotency_returns_cached_assessment():
    service = get_test_platform_service()
    idem_key = f"idem-tech-{uuid4()}"

    res1 = service.evaluate_technical_feasibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
        idempotency_key=idem_key,
    )
    assert res1["duplicated"] is False

    res2 = service.evaluate_technical_feasibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
        idempotency_key=idem_key,
    )
    assert res2["duplicated"] is True
    assert res2["assessment_id"] == res1["assessment_id"]


def test_idempotency_key_cross_project_rejected():
    service = get_test_platform_service()
    idem_key = f"idem-cross-{uuid4()}"

    service.evaluate_technical_feasibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
        idempotency_key=idem_key,
    )

    with pytest.raises(ConfiguracionPMV1Error, match="utilizada para otro expediente"):
        service.evaluate_technical_feasibility(
            project_id=PROJECT_B_ID,
            actor_id=PLANNER_ID,
            idempotency_key=idem_key,
        )


def test_get_technical_feasibility_alien_version_rejected():
    service = get_test_platform_service()
    with psycopg.connect(get_test_db_url(), row_factory=dict_row) as conn:
        pv_b = conn.execute(
            "SELECT id FROM project_versions WHERE project_id = %s LIMIT 1",
            (PROJECT_B_ID,),
        ).fetchone()
        assert pv_b is not None

    with pytest.raises(VersionNoPertenecienteError):
        service.get_technical_feasibility(
            project_id=PROJECT_A_ID,
            version_id=pv_b["id"],
        )


def test_get_project_includes_technical_assessment_strictly_read_only():
    service = get_test_platform_service()
    # Asegurar que PRY-A está evaluado
    service.evaluate_technical_feasibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
    )

    # get_project debe incluir technical_assessment
    proj = service.get_project(PROJECT_A_ID)
    assert proj["technical_assessment"] is not None
    assert proj["technical_assessment"]["overall_result"] == "cumple"
    assert proj["technical_assessment"]["technical_score"] == 100.0


def test_version_isolation():
    """Una versión nueva creada no debe heredar ni exhibir automáticamente la evaluación técnica anterior."""
    service = get_test_platform_service()
    with psycopg.connect(get_test_db_url(), row_factory=dict_row) as conn:
        # Crear versión 2 temporal en PRY-A
        new_v_id = uuid4()
        conn.execute(
            """
            INSERT INTO project_versions (id, project_id, version_number, title, description,
                                         location_description, estimated_budget_pen, beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 99, 'Versión 99 Aislamiento', 'Test aislamiento HU1.8',
                    'El Tambo', 500000, 1000, %s)
            """,
            (new_v_id, PROJECT_A_ID, PLANNER_ID),
        )
        conn.commit()

    try:
        # Consulta para v99 no debe tener evaluación previa
        v99_assessment = service.get_technical_feasibility(PROJECT_A_ID, version_id=new_v_id)
        assert v99_assessment is None
    finally:
        with psycopg.connect(get_test_db_url()) as conn:
            conn.execute("DELETE FROM project_versions WHERE id = %s", (new_v_id,))
            conn.commit()

# ==============================================================================
# 3. Pruebas de API HTTP (FastAPI Controller)
# ==============================================================================
from typing import Any
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.infrastructure.config.dependencies import get_auth_service, get_platform_service
from backend.domain.exceptions.pmv1_exceptions import CredencialesInvalidasError

class MockAuthService:
    def decode(self, token: str) -> dict[str, Any]:
        if token == "planner-token":
            return {"sub": str(PLANNER_ID), "roles": ["PLANNER"]}
        if token == "citizen-token":
            return {"sub": str(uuid4()), "roles": ["CITIZEN"]}
        raise CredencialesInvalidasError("Token no válido o expirado")


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_platform_service] = get_test_platform_service
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService()
    return TestClient(app)


def test_api_post_technical_assessment_planner_success(client: TestClient):
    resp = client.post(
        f"/api/v1/projects/{PROJECT_A_ID}/technical-assessment",
        headers={"Authorization": "Bearer planner-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_result"] == "cumple"
    assert data["is_viable"] is True
    assert data["technical_score"] == 100.0
    assert len(data["criteria"]) == 4


def test_api_post_technical_assessment_forbidden_for_citizen(client: TestClient):
    resp = client.post(
        f"/api/v1/projects/{PROJECT_A_ID}/technical-assessment",
        headers={"Authorization": "Bearer citizen-token"},
    )
    assert resp.status_code == 403


def test_api_post_technical_assessment_unauthorized_without_token(client: TestClient):
    resp = client.post(f"/api/v1/projects/{PROJECT_A_ID}/technical-assessment")
    assert resp.status_code == 401


def test_api_get_technical_assessment_success(client: TestClient):
    resp = client.get(
        f"/api/v1/projects/{PROJECT_A_ID}/technical-assessment",
        headers={"Authorization": "Bearer planner-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["overall_result"] == "cumple"


def test_api_get_technical_assessment_alien_version_bad_request(client: TestClient):
    with psycopg.connect(get_test_db_url(), row_factory=dict_row) as conn:
        pv_b = conn.execute(
            "SELECT id FROM project_versions WHERE project_id = %s LIMIT 1",
            (PROJECT_B_ID,),
        ).fetchone()

    resp = client.get(
        f"/api/v1/projects/{PROJECT_A_ID}/technical-assessment?version_id={pv_b['id']}",
        headers={"Authorization": "Bearer planner-token"},
    )
    assert resp.status_code == 400
    assert "no pertenece" in resp.json()["detail"].lower()

