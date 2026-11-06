import json
import psycopg
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from backend.application.services.pmv1_services import PlatformService
from backend.domain.exceptions.pmv1_exceptions import RecursoPMV1NoEncontradoError, ConfiguracionPMV1Error
from backend.infrastructure.config.settings import get_settings

PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")
ADMIN_ID = UUID("10000000-0000-4000-a000-000000000001")
ACTIVE_CRITERIA_ID = UUID("c0000000-0000-4000-a000-000000000001")


@pytest.fixture
def service():
    settings = get_settings()
    return PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )


@pytest.fixture
def db_conn():
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(db_url, autocommit=True)
    yield conn
    conn.close()


def _create_base_project(conn, code: str) -> tuple[UUID, UUID]:
    proj_id = uuid4()
    v1_id = uuid4()
    conn.execute(
        """
        INSERT INTO projects (id, code, created_by_user_id, status)
        VALUES (%s, %s, %s, 'ready')
        """,
        (proj_id, code, PLANNER_ID),
    )
    conn.execute(
        """
        INSERT INTO project_versions
        (id, project_id, version_number, title, description, location_description, proposed_land_use,
         territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
        VALUES (%s, %s, 1, 'Proyecto Multidimensional', 'Desc', 'Huancayo', 'Equipamiento', 'public', 150000, 1000, %s)
        """,
        (v1_id, proj_id, PLANNER_ID),
    )
    return proj_id, v1_id


def test_hu1_12_ca01_consolidation_of_all_five_dimensions(service, db_conn):
    """
    CA-HU1.12-01: Reúne los resultados de las cinco dimensiones (económica, social, ambiental,
    técnica y jurídica) en una sola vista con la conclusión y justificación de la versión vigente.
    Verifica además la correcta identificación de datos técnicos simulados (HU1.8) y citas (HU2.2).
    """
    code = f"PRY-ALL-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # 1. Económica
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 150.00, 85.00, 'completed', 'Costo unitario dentro del rango de excelencia', 'v1.0')
        """,
        (eval_id, uuid4()),
    )

    # 2. Social
    db_conn.execute(
        """
        INSERT INTO social_accessibility_assessments (
            id, project_id, project_version_id, requested_by_user_id, idempotency_key,
            status, summary, results_json, equity_json, social_score, score_explanation
        ) VALUES (
            %s, %s, %s, %s, %s,
            'completed', 'Cobertura social óptima', '[{"is_simulated": true}]'::jsonb, '{}'::jsonb, 90.00, 'Alta proximidad a postas y colegios'
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 3. Ambiental
    db_conn.execute(
        """
        INSERT INTO environmental_assessments (
            id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
            status, risk_level, risk_observation, requires_human_review, favorable,
            summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score
        ) VALUES (
            %s, %s, %s, %s, %s,
            'sufficient', 'low', 'Sin riesgos significativos', FALSE, TRUE,
            'Impacto ambiental bajo y controlado', '{"is_simulated": true}'::jsonb, '[]'::jsonb, '[]'::jsonb, 80.00
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 4. Técnica (con datos simulados HU1.8)
    db_conn.execute(
        """
        INSERT INTO technical_feasibility_assessments (
            id, project_id, project_version_id, requested_by_user_id, idempotency_key,
            status, overall_result, overall_result_label, is_viable, is_preliminary_opinion,
            disclaimer, summary, criteria_summary, findings_json, technical_score,
            dimension_conclusion, dimension_justification
        ) VALUES (
            %s, %s, %s, %s, %s,
            'completed', 'cumple', 'Viable (Cumple)', TRUE, TRUE,
            'Datos preliminares', 'Viabilidad técnica favorable', '{"total": 4, "cumple": 4}'::jsonb,
            '[{"criterion_code": "mecanica_suelos", "is_simulated": true}]'::jsonb, 78.50,
            'Diseño geométrico y mecánica de suelos cumplen tolerancias normativas.',
            'Cálculos sustentados en parámetros preliminares de ingeniería.'
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 5. Jurídica (con citas verificadas HU2.2)
    db_conn.execute(
        """
        INSERT INTO legal_assessments (
            id, project_id, project_code, project_version_id, status, summary,
            findings_json, total_findings, verifiable_citations_count, unverifiable_citations_count,
            requires_human_review, has_legal_alert, is_resolved
        ) VALUES (
            %s, %s, %s, %s, 'verified', 'Dictamen normativo conforme',
            '[]'::jsonb, 3, 3, 0,
            FALSE, FALSE, FALSE
        )
        """,
        (uuid4(), proj_id, code, v1_id),
    )

    # Ejecutar consulta del resumen
    res = service.get_unified_assessment_summary(project_id=proj_id)

    assert res["project_id"] == proj_id
    assert res["version_number"] == 1
    assert res["is_complete"] is True
    assert res["status"] == "completed"
    assert res["allows_final_approval"] is True
    assert len(res["dimensions"]) == 5

    dim_map = {d["dimension_code"]: d for d in res["dimensions"]}
    assert set(dim_map.keys()) == {"economic", "social", "environmental", "technical", "legal"}

    # Conclusión y justificación presentes en todas
    for code_d, dim in dim_map.items():
        assert dim["conclusion"], f"Falta conclusion en {code_d}"
        assert dim["justification"], f"Falta justificacion en {code_d}"
        assert dim["status"] == "completed"

    # Distinción de datos técnicos simulados (HU1.8)
    assert dim_map["technical"]["is_simulated"] is True
    assert "simulado" in dim_map["technical"]["warning"].lower()

    # Distinción de dimensión jurídica sin score arbitrario
    assert dim_map["legal"]["score"] is None
    assert dim_map["legal"]["details"]["verifiable_citations_count"] == 3


def test_hu1_12_ca02_explainable_global_score_calculation(service, db_conn):
    """
    CA-HU1.12-02: Expone las puntuaciones de entrada, sus pesos y la fórmula utilizada
    para obtener la valoración consolidada a partir de la versión activa de criterios.
    """
    code = f"PRY-SC-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # Insertar versión de criterios activa con pesos específicos
    crit_id = uuid4()
    temp_version = int(datetime.now(timezone.utc).timestamp()) % 1000000 + 10000
    try:
        db_conn.execute("UPDATE criteria_versions SET status = 'retired' WHERE status = 'active'")
        db_conn.execute(
            """
            INSERT INTO criteria_versions (id, version_number, status, excellent_cost_pen, unacceptable_cost_pen, created_by_user_id, activated_at)
            VALUES (%s, %s, 'active', 200, 500, %s, now())
            """,
            (crit_id, temp_version, ADMIN_ID),
        )
        db_conn.execute(
            """
            INSERT INTO criterion_weights (criteria_version_id, criterion_code, weight_percent)
            VALUES
                (%s, 'ECONOMIC', 50.00),
                (%s, 'TECHNICAL', 50.00)
            """,
            (crit_id, crit_id),
        )
        # Económica: score 80
        eval_id = uuid4()
        db_conn.execute(
            """
            INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
            VALUES (%s, %s, %s, %s, %s, 'completed')
            """,
            (eval_id, v1_id, crit_id, PLANNER_ID, str(uuid4())),
        )
        db_conn.execute(
            """
            INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 180.00, 80.00, 'completed', 'Económica aceptable', 'v1.0')
            """,
            (eval_id, uuid4()),
        )

        # Social: score 90 (no tiene peso en esta versión de política)
        db_conn.execute(
            """
            INSERT INTO social_accessibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, summary, results_json, equity_json, social_score, score_explanation)
            VALUES (%s, %s, %s, %s, %s, 'completed', 'Social ok', '[]'::jsonb, '{}'::jsonb, 90.00, 'Ok')
            """,
            (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
        )

        # Ambiental: score 70
        db_conn.execute(
            """
            INSERT INTO environmental_assessments (id, project_id, project_version_id, assessed_by_user_id, idempotency_key, status, risk_level, risk_observation, requires_human_review, favorable, summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score)
            VALUES (%s, %s, %s, %s, %s, 'sufficient', 'low', 'Bajo', FALSE, TRUE, 'Ambiental ok', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, 70.00)
            """,
            (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
        )

        # Técnica: score 90
        db_conn.execute(
            """
            INSERT INTO technical_feasibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, overall_result, overall_result_label, is_viable, is_preliminary_opinion, disclaimer, summary, criteria_summary, findings_json, technical_score, dimension_conclusion, dimension_justification)
            VALUES (%s, %s, %s, %s, %s, 'completed', 'cumple', 'Viable', TRUE, TRUE, 'Discl', 'Summary', '{}'::jsonb, '[]'::jsonb, 90.00, 'Conc', 'Just')
            """,
            (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
        )

        # Jurídica: completada sin alertas
        db_conn.execute(
            """
            INSERT INTO legal_assessments (id, project_id, project_code, project_version_id, status, summary, findings_json, total_findings, verifiable_citations_count, unverifiable_citations_count, requires_human_review, has_legal_alert, is_resolved)
            VALUES (%s, %s, %s, %s, 'verified', 'Legal ok', '[]'::jsonb, 1, 1, 0, FALSE, FALSE, FALSE)
            """,
            (uuid4(), proj_id, code, v1_id),
        )

        res = service.get_unified_assessment_summary(project_id=proj_id)
        gs = res["global_score"]

        assert gs["is_calculated"] is True
        # (80 * 50% + 90 * 50%) / 100% = 85.0 pts
        assert gs["score"] == 85.0
        assert gs["criteria_version_number"] == temp_version
        assert gs["weights"] == {"ECONOMIC": 50.0, "TECHNICAL": 50.0}
        assert "85.00 pts" in gs["formula"]
        assert "ECONOMIC: 80.0" in gs["formula"]
        assert "TECHNICAL: 90.0" in gs["formula"]

    finally:
        # Restaurar criterios v1 como activos
        db_conn.execute("UPDATE criteria_versions SET status = 'retired' WHERE id = %s", (crit_id,))
        db_conn.execute("UPDATE criteria_versions SET status = 'active' WHERE id = %s", (ACTIVE_CRITERIA_ID,))


def test_hu1_12_ca03_incomplete_dimensions_detected_and_blocks_approval(service, db_conn):
    """
    CA-HU1.12-03: Si alguna dimensión sigue pendiente, identifica la dimensión afectada
    y no presenta una evaluación incompleta como resultado final aprobado.
    """
    code = f"PRY-INC-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # Solo registramos económica; social, ambiental, técnica y jurídica quedan pendientes
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 150.00, 85.00, 'completed', 'Económica ok', 'v1.0')
        """,
        (eval_id, uuid4()),
    )

    res = service.get_unified_assessment_summary(project_id=proj_id)

    assert res["is_complete"] is False
    assert res["status"] == "incomplete"
    assert res["allows_final_approval"] is False
    assert set(res["missing_dimensions"]) == {"Social", "Ambiental", "Tecnica", "Juridica"}

    # Puntuación global no calculable
    assert res["global_score"]["is_calculated"] is False
    assert res["global_score"]["score"] is None
    assert "faltan dimensiones indispensables" in res["global_score"]["formula"]


def test_hu1_12_ca03_failed_or_insufficient_data_dimension_detected(service, db_conn):
    """
    CA-HU1.12-03: Dimensión técnica con información insuficiente o no viable se detecta como incompleta.
    """
    code = f"PRY-FAIL-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # 1. Económica ok
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 150.00, 85.00, 'completed', 'Ok', 'v1.0')
        """,
        (eval_id, uuid4()),
    )

    # 2. Social ok
    db_conn.execute(
        """
        INSERT INTO social_accessibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, summary, results_json, equity_json, social_score, score_explanation)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'Ok', '[]'::jsonb, '{}'::jsonb, 80.00, 'Ok')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 3. Ambiental ok
    db_conn.execute(
        """
        INSERT INTO environmental_assessments (id, project_id, project_version_id, assessed_by_user_id, idempotency_key, status, risk_level, risk_observation, requires_human_review, favorable, summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score)
        VALUES (%s, %s, %s, %s, %s, 'sufficient', 'low', 'Bajo', FALSE, TRUE, 'Ok', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, 80.00)
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 4. Técnica con INFORMACIÓN INSUFICIENTE
    db_conn.execute(
        """
        INSERT INTO technical_feasibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, overall_result, overall_result_label, is_viable, is_preliminary_opinion, disclaimer, summary, criteria_summary, findings_json, technical_score, dimension_conclusion, dimension_justification)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'informacion_insuficiente', 'Información insuficiente', FALSE, TRUE, 'Discl', 'Faltan parámetros', '{}'::jsonb, '[]'::jsonb, NULL, 'Falta mecánica de suelos', 'No se puede dictaminar')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 5. Jurídica ok
    db_conn.execute(
        """
        INSERT INTO legal_assessments (id, project_id, project_code, project_version_id, status, summary, findings_json, total_findings, verifiable_citations_count, unverifiable_citations_count, requires_human_review, has_legal_alert, is_resolved)
        VALUES (%s, %s, %s, %s, 'verified', 'Ok', '[]'::jsonb, 1, 1, 0, FALSE, FALSE, FALSE)
        """,
        (uuid4(), proj_id, code, v1_id),
    )

    res = service.get_unified_assessment_summary(project_id=proj_id)

    assert res["is_complete"] is False
    assert "Tecnica (Informacion insuficiente)" in res["missing_dimensions"]
    assert res["allows_final_approval"] is False
    assert res["global_score"]["is_calculated"] is False


def test_hu1_12_active_legal_alert_blocks_approval_and_marks_blocked(service, db_conn):
    """
    HU2.3 / HU1.12: Alerta Legal activa en la versión vigente bloquea el resumen y la aprobación.
    """
    code = f"PRY-LBLK-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # Completamos todas las evaluaciones, pero la jurídica tiene ALERTA LEGAL activa
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 150.00, 95.00, 'completed', 'Ok', 'v1.0')
        """,
        (eval_id, uuid4()),
    )
    db_conn.execute(
        """
        INSERT INTO social_accessibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, summary, results_json, equity_json, social_score, score_explanation)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'Ok', '[]'::jsonb, '{}'::jsonb, 90.00, 'Ok')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO environmental_assessments (id, project_id, project_version_id, assessed_by_user_id, idempotency_key, status, risk_level, risk_observation, requires_human_review, favorable, summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score)
        VALUES (%s, %s, %s, %s, %s, 'sufficient', 'low', 'Bajo', FALSE, TRUE, 'Ok', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, 85.00)
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO technical_feasibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, overall_result, overall_result_label, is_viable, is_preliminary_opinion, disclaimer, summary, criteria_summary, findings_json, technical_score, dimension_conclusion, dimension_justification)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'cumple', 'Viable', TRUE, TRUE, 'Discl', 'Ok', '{}'::jsonb, '[]'::jsonb, 88.00, 'Ok', 'Ok')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    # Jurídica con alerta legal activa
    db_conn.execute(
        """
        INSERT INTO legal_assessments (
            id, project_id, project_code, project_version_id, status, summary,
            findings_json, total_findings, verifiable_citations_count, unverifiable_citations_count,
            requires_human_review, has_legal_alert, legal_alert_motive, legal_alert_norm, is_resolved
        ) VALUES (
            %s, %s, %s, %s, 'alerta_legal', 'Incompatibilidad de zonificación detectada',
            '[]'::jsonb, 1, 1, 0,
            TRUE, TRUE, 'Uso prohibido en zona residencial', 'PDU Huancayo 2024', FALSE
        )
        """,
        (uuid4(), proj_id, code, v1_id),
    )

    res = service.get_unified_assessment_summary(project_id=proj_id)

    assert res["status"] == "blocked"
    assert res["allows_final_approval"] is False
    assert len(res["blocking_reasons"]) > 0
    assert any("Alerta Legal" in r for r in res["blocking_reasons"])

    legal_dim = next(d for d in res["dimensions"] if d["dimension_code"] == "legal")
    assert legal_dim["status"] == "blocked"
    assert legal_dim["has_blocker"] is True
    assert "Uso prohibido" in legal_dim["blocker_message"]


def test_hu1_12_version_isolation_new_version_does_not_leak_prior_evaluations(service, db_conn):
    """
    Aislamiento por versión: Las evaluaciones finalizadas en v1 no se presentan como vigentes en v2.
    """
    code = f"PRY-VER-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # Completar v1 al 100%
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 150.00, 85.00, 'completed', 'Ok', 'v1.0')
        """,
        (eval_id, uuid4()),
    )
    db_conn.execute(
        """
        INSERT INTO social_accessibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, summary, results_json, equity_json, social_score, score_explanation)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'Ok', '[]'::jsonb, '{}'::jsonb, 90.00, 'Ok')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO environmental_assessments (id, project_id, project_version_id, assessed_by_user_id, idempotency_key, status, risk_level, risk_observation, requires_human_review, favorable, summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score)
        VALUES (%s, %s, %s, %s, %s, 'sufficient', 'low', 'Bajo', FALSE, TRUE, 'Ok', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, 85.00)
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO technical_feasibility_assessments (id, project_id, project_version_id, requested_by_user_id, idempotency_key, status, overall_result, overall_result_label, is_viable, is_preliminary_opinion, disclaimer, summary, criteria_summary, findings_json, technical_score, dimension_conclusion, dimension_justification)
        VALUES (%s, %s, %s, %s, %s, 'completed', 'cumple', 'Viable', TRUE, TRUE, 'Discl', 'Ok', '{}'::jsonb, '[]'::jsonb, 88.00, 'Ok', 'Ok')
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO legal_assessments (id, project_id, project_code, project_version_id, status, summary, findings_json, total_findings, verifiable_citations_count, unverifiable_citations_count, requires_human_review, has_legal_alert, is_resolved)
        VALUES (%s, %s, %s, %s, 'verified', 'Ok', '[]'::jsonb, 1, 1, 0, FALSE, FALSE, FALSE)
        """,
        (uuid4(), proj_id, code, v1_id),
    )

    # Verificar que v1 está completa
    res_v1 = service.get_unified_assessment_summary(project_id=proj_id, version_id=v1_id)
    assert res_v1["is_complete"] is True
    assert res_v1["version_number"] == 1

    # Crear versión v2
    v2_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO project_versions
        (id, project_id, version_number, title, description, location_description, proposed_land_use,
         territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
        VALUES (%s, %s, 2, 'Proyecto Versión 2 Subsanada', 'Desc 2', 'Huancayo 2', 'Equipamiento', 'public', 160000, 1100, %s)
        """,
        (v2_id, proj_id, PLANNER_ID),
    )
    db_conn.execute(
        "UPDATE projects SET status = 'ready' WHERE id = %s",
        (proj_id,),
    )

    # Consultar resumen para v2 (debe mostrar las 5 dimensiones pendientes)
    res_v2 = service.get_unified_assessment_summary(project_id=proj_id, version_id=v2_id)
    assert res_v2["version_number"] == 2
    assert res_v2["is_complete"] is False
    assert res_v2["status"] == "incomplete"
    assert res_v2["allows_final_approval"] is False
    assert len(res_v2["missing_dimensions"]) == 5
    for d in res_v2["dimensions"]:
        assert d["status"] == "pending"


def test_hu1_12_read_only_side_effect_free(service, db_conn):
    """
    Comprueba que get_unified_assessment_summary es una operación estrictamente de solo lectura,
    sin efectos secundarios ni mutaciones de estado en la base de datos.
    """
    code = f"PRY-RO-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # Capturar conteos de tablas
    t_names = [
        "projects", "project_versions", "evaluations", "economic_result_projections",
        "social_accessibility_assessments", "environmental_assessments",
        "technical_feasibility_assessments", "legal_assessments", "human_approvals", "audit_events"
    ]
    counts_before = {t: db_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in t_names}

    # Llamar 3 veces seguidas
    r1 = service.get_unified_assessment_summary(project_id=proj_id)
    r2 = service.get_unified_assessment_summary(project_id=proj_id)
    r3 = service.get_unified_assessment_summary(project_id=proj_id)

    assert r1["summary_text"] == r2["summary_text"] == r3["summary_text"]

    counts_after = {t: db_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in t_names}
    assert counts_before == counts_after, "La consulta GET generó efectos secundarios en la base de datos"

def test_hu1_12_api_endpoint(service, db_conn):
    """
    Comprueba el endpoint GET /api/v1/projects/{project_id}/unified-summary
    con autenticación y serialización DTO correcta.
    """
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from backend.infrastructure.config.dependencies import get_current_user

    code = f"PRY-API-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": PLANNER_ID,
        "roles": ["PLANNER"],
        "email": "planificador@siprim.gob.pe"
    }

    with TestClient(app) as client:
        res = client.get(f"/api/v1/projects/{proj_id}/unified-summary")
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == str(proj_id)
        assert len(data["dimensions"]) == 5
        assert data["is_complete"] is False
        assert "missing_dimensions" in data
        assert "global_score" in data



def test_hu1_12_legal_dimension_in_requires_review_blocks_final_approval_and_marks_incomplete(service, db_conn):
    """
    HU1.12 CORRECCIÓN: Una dimensión jurídica en 'requires_review' (por citas no verificables
    o dictamen legal pendiente) NO puede contar como evaluación final plenamente resuelta
    ni habilitar la aprobación definitiva.
    - is_complete debe ser False.
    - allows_final_approval debe ser False en el resumen y en la compuerta humana.
    - blocking_reasons debe identificar explícitamente el pendiente legal.
    - submit_human_approval debe rechazar la decisión 'approved'.
    """
    code = f"PRY-REQREV-{uuid4().hex[:6]}"
    proj_id, v1_id = _create_base_project(db_conn, code)

    # 1. Económica completa
    eval_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO evaluations (id, project_version_id, criteria_version_id, requested_by_user_id, idempotency_key, status)
        VALUES (%s, %s, %s, %s, %s, 'completed')
        """,
        (eval_id, v1_id, ACTIVE_CRITERIA_ID, PLANNER_ID, str(uuid4())),
    )
    db_conn.execute(
        """
        INSERT INTO economic_result_projections (evaluation_id, economic_assessment_id, cost_per_beneficiary_pen, score_0_100, status, explanation, algorithm_version)
        VALUES (%s, %s, 180.00, 85.00, 'completed', 'Costo óptimo por habitante', 'v1.0')
        """,
        (eval_id, uuid4()),
    )

    # 2. Social completa
    db_conn.execute(
        """
        INSERT INTO social_accessibility_assessments (
            id, project_id, project_version_id, requested_by_user_id, idempotency_key,
            status, summary, results_json, equity_json, social_score, score_explanation
        ) VALUES (
            %s, %s, %s, %s, %s,
            'completed', 'Cobertura favorable', '[]'::jsonb, '{}'::jsonb, 90.00, 'Acceso óptimo'
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 3. Ambiental completa
    db_conn.execute(
        """
        INSERT INTO environmental_assessments (
            id, project_id, project_version_id, assessed_by_user_id, idempotency_key,
            status, risk_level, risk_observation, requires_human_review, favorable,
            summary, declared_vs_evidence_json, impacts_json, mitigations_json, environmental_score
        ) VALUES (
            %s, %s, %s, %s, %s,
            'sufficient', 'low', 'Sin riesgo ambiental', FALSE, TRUE,
            'Bajo impacto', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, 85.00
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 4. Técnica completa
    db_conn.execute(
        """
        INSERT INTO technical_feasibility_assessments (
            id, project_id, project_version_id, requested_by_user_id, idempotency_key,
            status, overall_result, overall_result_label, is_viable, is_preliminary_opinion,
            disclaimer, summary, criteria_summary, findings_json, technical_score,
            score_explanation, dimension_conclusion, dimension_justification
        ) VALUES (
            %s, %s, %s, %s, %s,
            'completed', 'cumple', 'Viable (Cumple)', TRUE, FALSE,
            'Dictamen técnico preliminar', 'Diseño conforme', '{}'::jsonb, '[]'::jsonb, 80.00,
            'Puntuación técnica 80.0/100', 'Conclusión técnica favorable', 'Justificación técnica completa'
        )
        """,
        (uuid4(), proj_id, v1_id, PLANNER_ID, str(uuid4())),
    )

    # 5. Jurídica PENDIENTE en 'requires_review' con citas no verificables (HU2.2)
    db_conn.execute(
        """
        INSERT INTO legal_assessments (
            id, project_id, project_code, project_version_id, status, summary, findings_json,
            total_findings, verifiable_citations_count, unverifiable_citations_count,
            requires_human_review, has_legal_alert, is_resolved, evaluated_at
        ) VALUES (
            %s, %s, %s, %s, 'requires_review',
            'Dictamen legal con citas no verificables pendientes de cotejo manual',
            '[]'::jsonb, 2, 1, 1, TRUE, FALSE, FALSE, now()
        )
        """,
        (uuid4(), proj_id, code, v1_id),
    )

    # Marcar proyecto como evaluated preliminarmente
    db_conn.execute("UPDATE projects SET status = 'evaluated' WHERE id = %s", (proj_id,))

    # 1. Consultar resumen unificado (HU1.12)
    res = service.get_unified_assessment_summary(project_id=proj_id)

    # Verificaciones estrictas
    assert res["is_complete"] is False, "Una dimensión jurídica en requires_review no puede considerarse completa"
    assert res["allows_final_approval"] is False, "Una dimensión jurídica en requires_review no puede habilitar aprobación"
    assert res["status"] == "blocked"
    assert any("Juridica" in d for d in res["missing_dimensions"]), "Debe reportar la dimensión jurídica pendiente"
    assert any("requires_review" in r or "juridica" in r.lower() for r in res["blocking_reasons"])

    # 2. Consultar compuerta humana (HU1.12 / HU2.2)
    human_gate = service.get_human_approval(proj_id)
    assert human_gate["allows_final_approval"] is False, "La compuerta humana debe reportar allows_final_approval=False"

    # 3. Intentar aprobación formal: debe ser rechazada por la compuerta backend
    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.submit_human_approval(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            decision="approved",
            justification="Se aprueba indebidamente ignorando citas no verificables.",
            conditions=None,
            idempotency_key=f"appr-fail-reqrev-{uuid4()}",
        )
    assert "requires_review" in str(exc_info.value)
