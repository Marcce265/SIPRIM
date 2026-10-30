# backend/tests/test_environmental_assessment_service.py
from datetime import datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.errors import CheckViolation
from psycopg.types.json import Jsonb

from backend.application.services.pmv1_services import (
    EnvironmentalAssessmentEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import ConfiguracionPMV1Error
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PROJECT_C_ID = UUID("a0000000-0000-4000-a000-00000000000c")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


def test_environmental_engine_complete_moderate():
    """CA-HU1.6-01: Muestra impactos, nivel de riesgo, sustento y mitigaciones, diferenciando declaraciones de evidencias."""
    sample_records = [
        {
            "environmental_component": "aire_acustico_residuos",
            "has_sufficient_data": True,
            "declared_impacts": "Polvo y ruido temporal durante movimiento de tierras.",
            "declared_measures": "Riego diario y cerco perimétrico.",
            "verifiable_evidence": "Ubicación en zona consolidada a más de 400 m de faja marginal fluvial.",
            "proximity_to_water_meters": 420.0,
            "is_in_protected_or_risk_area": False,
            "source_name": "PDM Huancayo 2017-2037 / CENEPRED (Simulado)",
            "data_origin": "simulated",
        }
    ]

    result = EnvironmentalAssessmentEngine.evaluate(
        project_id=PROJECT_A_ID,
        project_code="PRY-A",
        project_version_id=uuid4(),
        records=sample_records,
    )

    assert result["status"] == "sufficient"
    assert result["risk_level"] == "moderate"
    assert result["requires_human_review"] is False
    assert result["favorable"] is True

    # Diferenciación entre lo declarado y la evidencia verificable
    d_vs_e = result["declared_vs_evidence"]
    assert "Polvo y ruido temporal" in d_vs_e["declared_by_applicant"]
    assert "Riego diario" in d_vs_e["declared_measures"]
    assert "zona consolidada a más de 400 m" in d_vs_e["verifiable_evidence"]
    assert d_vs_e["is_simulated"] is True

    # Impactos y mitigaciones
    assert len(result["impacts"]) >= 1
    for impact in result["impacts"]:
        assert impact["component"] != ""
        assert impact["description"] != ""
        assert impact["severity"] in ("baja", "moderada")
        assert impact["substantiation"] != ""
        assert len(impact["mitigations"]) > 0

    assert len(result["mitigations"]) >= 1


def test_environmental_engine_high_risk_requires_human_review():
    """CA-HU1.6-02: Ante posible impacto alto, registra observación de riesgo que requiere consideración humana antes de decisión favorable."""
    sample_records = [
        {
            "environmental_component": "recurso_hidrico_ecosistema",
            "has_sufficient_data": True,
            "declared_impacts": "Almacenamiento de vehículos sin impacto ambiental según el administrado.",
            "declared_measures": "Piso de afirmado compacto.",
            "verifiable_evidence": "Predio ubicado a 25 metros del Río Shullcas en faja marginal intangible no mitigable (PDM Huancayo / CENEPRED-SIGRID).",
            "proximity_to_water_meters": 25.0,
            "is_in_protected_or_risk_area": True,
            "source_name": "PDM Huancayo / ANA-ALA Mantaro / SIGRID (Simulado)",
            "data_origin": "simulated",
        }
    ]

    result = EnvironmentalAssessmentEngine.evaluate(
        project_id=PROJECT_C_ID,
        project_code="PRY-C",
        project_version_id=uuid4(),
        records=sample_records,
    )

    assert result["status"] == "sufficient"
    assert result["risk_level"] == "high"
    assert result["requires_human_review"] is True
    # NO puede tener aprobación automática
    assert result["favorable"] is not True
    assert result["risk_observation"] is not None
    assert "OBSERVACIÓN DE RIESGO AMBIENTAL ALTO" in result["risk_observation"]
    assert "prohíbe la aprobación automática" in result["risk_observation"]


def test_environmental_engine_insufficient_data():
    """CA-HU1.6-03: Si faltan datos esenciales, muestra 'Información insuficiente' y nunca una conclusión favorable por defecto."""
    sample_records = [
        {
            "environmental_component": "integral",
            "has_sufficient_data": False,
            "declared_impacts": None,
            "declared_measures": None,
            "verifiable_evidence": None,
            "proximity_to_water_meters": None,
            "is_in_protected_or_risk_area": None,
            "source_name": "Catastro Municipal El Tambo (Sin DIA ni línea base)",
            "data_origin": "simulated",
        }
    ]

    result = EnvironmentalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        records=sample_records,
    )

    assert result["status"] == "insufficient"
    assert result["risk_level"] == "insufficient"
    assert result["risk_level_label"] == "Información insuficiente"
    # NUNCA favorable por defecto
    assert result["favorable"] is None
    assert result["favorable"] is not True
    assert "Información insuficiente" in result["summary"]
    assert len(result["impacts"]) == 0
    assert result["declared_vs_evidence"]["is_in_protected_or_risk_area"] is None
    assert result["declared_vs_evidence"]["is_in_protected_or_risk_area"] is not False


def test_insufficient_evidence_sets_risk_area_as_unknown():
    """Impide que un dato ambiental ausente se interprete como ausencia de riesgo (False en vez de None)."""
    # 1. Sin registros: estado desconocido (None), nunca False
    res_empty = EnvironmentalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=None,
        records=[],
    )
    assert res_empty["declared_vs_evidence"]["is_in_protected_or_risk_area"] is None
    assert res_empty["declared_vs_evidence"]["is_in_protected_or_risk_area"] is not False

    # 2. Con registro insuficiente: estado desconocido (None), nunca False
    res_insufficient = EnvironmentalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=None,
        records=[{
            "environmental_component": "integral",
            "has_sufficient_data": False,
            "declared_impacts": None,
            "declared_measures": None,
            "verifiable_evidence": None,
            "proximity_to_water_meters": None,
            "is_in_protected_or_risk_area": None,
            "source_name": "Catastro Municipal",
        }],
    )
    assert res_insufficient["declared_vs_evidence"]["is_in_protected_or_risk_area"] is None
    assert res_insufficient["declared_vs_evidence"]["is_in_protected_or_risk_area"] is not False


def test_db_check_constraints_prevent_invalid_environmental_states():
    """Comprueba las restricciones check de la base de datos para HU1.6."""
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(db_url) as conn:
        # 1. chk_insufficient_not_favorable: status='insufficient' con favorable=TRUE debe fallar
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO environmental_assessments
                    (id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
                     status, risk_level, requires_human_review, favorable, summary,
                     declared_vs_evidence_json, impacts_json, mitigations_json)
                    VALUES (%s, %s, (SELECT id FROM project_versions WHERE project_id=%s LIMIT 1),
                            %s, 'test-key-invalid-fav', 'insufficient', 'insufficient', FALSE, TRUE,
                            'Invalido', '{}', '[]', '[]')
                    """,
                    (uuid4(), PROJECT_B_ID, PROJECT_B_ID, PLANNER_ID),
                )

        # 2. chk_high_risk_requires_human_review: risk_level='high' con requires_human_review=FALSE debe fallar
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO environmental_assessments
                    (id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
                     status, risk_level, requires_human_review, favorable, summary,
                     declared_vs_evidence_json, impacts_json, mitigations_json)
                    VALUES (%s, %s, (SELECT id FROM project_versions WHERE project_id=%s LIMIT 1),
                            %s, 'test-key-invalid-high-rev', 'sufficient', 'high', FALSE, NULL,
                            'Invalido', '{}', '[]', '[]')
                    """,
                    (uuid4(), PROJECT_C_ID, PROJECT_C_ID, PLANNER_ID),
                )

        # 4. chk_env_insufficient_no_evidence: has_sufficient_data=FALSE con is_in_protected_or_risk_area=FALSE debe fallar
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO project_environmental_records
                    (id, project_id, project_code, has_sufficient_data, environmental_component,
                     is_in_protected_or_risk_area, source_name)
                    VALUES (%s, %s, 'PRY-TEST', FALSE, 'integral', FALSE, 'test')
                    """,
                    (uuid4(), PROJECT_B_ID),
                )

        # 3. chk_high_risk_not_auto_favorable: risk_level='high' con favorable=TRUE debe fallar
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO environmental_assessments
                    (id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
                     status, risk_level, requires_human_review, favorable, summary,
                     declared_vs_evidence_json, impacts_json, mitigations_json)
                    VALUES (%s, %s, (SELECT id FROM project_versions WHERE project_id=%s LIMIT 1),
                            %s, 'test-key-invalid-high-fav', 'sufficient', 'high', TRUE, TRUE,
                            'Invalido', '{}', '[]', '[]')
                    """,
                    (uuid4(), PROJECT_C_ID, PROJECT_C_ID, PLANNER_ID),
                )


def test_platform_service_environmental_flow():
    """Verifica el flujo completo de evaluación ambiental en PlatformService con base de datos real."""
    settings = get_settings()
    service = PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )

    # 1. Caso PRY-A (Moderado, favorable condicionado a mitigación)
    res_a = service.evaluate_environmental_assessment(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
        idempotency_key=f"test-env-a-{uuid4().hex[:8]}",
    )
    assert res_a["status"] == "sufficient"
    assert res_a["risk_level"] == "moderate"
    assert res_a["favorable"] is True
    assert len(res_a["impacts"]) >= 1

    # 2. Caso PRY-C (Alto riesgo, requiere revisión humana)
    res_c = service.evaluate_environmental_assessment(
        project_id=PROJECT_C_ID,
        actor_id=PLANNER_ID,
        idempotency_key=f"test-env-c-{uuid4().hex[:8]}",
    )
    assert res_c["status"] == "sufficient"
    assert res_c["risk_level"] == "high"
    assert res_c["requires_human_review"] is True
    assert res_c["favorable"] is not True
    assert res_c["risk_observation"] is not None

    # 3. Caso PRY-B (Información insuficiente, nunca favorable por defecto)
    res_b = service.evaluate_environmental_assessment(
        project_id=PROJECT_B_ID,
        actor_id=PLANNER_ID,
        idempotency_key=f"test-env-b-{uuid4().hex[:8]}",
    )
    assert res_b["status"] == "insufficient"
    assert res_b["risk_level"] == "insufficient"
    assert res_b["favorable"] is None
    assert "Información insuficiente" in res_b["summary"]
    assert res_b["declared_vs_evidence"]["is_in_protected_or_risk_area"] is None
    assert res_b["declared_vs_evidence"]["is_in_protected_or_risk_area"] is not False

    # 4. get_environmental_assessment recupera la evaluación
    fetched_c = service.get_environmental_assessment(PROJECT_C_ID)
    assert fetched_c["risk_level"] == "high"
    assert fetched_c["requires_human_review"] is True
