from datetime import datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from backend.application.services.pmv1_services import (
    CompletionProcessor,
    PlatformService,
    RiskCheckpointEngine,
)
from backend.domain.exceptions.pmv1_exceptions import ConfiguracionPMV1Error
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PROJECT_C_ID = UUID("a0000000-0000-4000-a000-00000000000c")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


def get_test_db_url() -> str:
    settings = get_settings()
    return settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def get_test_platform_service() -> PlatformService:
    db_url = get_test_db_url()
    return PlatformService(
        db_url=db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )


def test_high_risk_checkpoint_pauses_evaluation_at_pending_review():
    """CA-HU3.1-01: Si se detecta riesgo alto configurado para revisión humana,
    el sistema detiene el procesamiento en un punto de control persistente,
    establece 'pending_review' y no continúa automáticamente hacia la finalización."""
    service = get_test_platform_service()

    project = service.get_project(PROJECT_C_ID)
    assert project["status"] == "pending_review"

    checkpoint = service.get_project_checkpoint(PROJECT_C_ID)
    assert checkpoint is not None
    assert checkpoint["checkpoint_type"] == "high_risk_pause"
    assert checkpoint["status"] == "pending_review"
    assert checkpoint["risk_level"] == "high"
    assert checkpoint["risk_source"] == "environmental"
    assert checkpoint["requires_human_review"] is True
    assert checkpoint["allows_final_approval"] is False
    assert "faja marginal" in checkpoint["reason"].lower() or "shullcas" in checkpoint["reason"].lower() or "cuerpo de agua" in checkpoint["reason"].lower()
    assert checkpoint["details"] is not None


def test_checkpoint_persists_across_reinstantiation_and_db_query():
    """Verifica que el punto de control persiste en base de datos de manera duradera."""
    db_url = get_test_db_url()
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """SELECT * FROM evaluation_checkpoints
            WHERE project_id = %s AND status = 'pending_review'""",
            (PROJECT_C_ID,),
        ).fetchall()
        assert len(rows) >= 1
        cp = rows[0]
        assert cp["checkpoint_type"] == "high_risk_pause"
        assert cp["risk_level"] == "high"
        assert cp["risk_source"] == "environmental"


def test_completion_processor_idempotency_on_retries():
    """CA-HU3.1-01: Los reintentos del procesador de eventos no duplican el checkpoint
    ni permiten avanzar hacia 'completed' o 'evaluated'."""
    db_url = get_test_db_url()
    service = get_test_platform_service()
    project = service.get_project(PROJECT_C_ID)
    project_version_id = project["project_version_id"]

    # Contar checkpoints existentes antes de reintentos
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        initial_count = conn.execute(
            """SELECT COUNT(*) AS total FROM evaluation_checkpoints
            WHERE project_version_id = %s AND risk_source = 'environmental'""",
            (project_version_id,),
        ).fetchone()["total"]
        assert initial_count >= 1

        # Crear una evaluación simulada para reintento
        criteria_row = conn.execute(
            "SELECT id FROM criteria_versions WHERE status='active' LIMIT 1"
        ).fetchone()
        eval_id = uuid4()
        conn.execute(
            """INSERT INTO evaluations (id, project_version_id, criteria_version_id,
            requested_by_user_id, status, idempotency_key)
            VALUES (%s, %s, %s, %s, 'processing', %s)""",
            (eval_id, project_version_id, criteria_row["id"], PLANNER_ID, str(uuid4())),
        )

    # Ejecutar procesador de finalización dos veces (simulando reintento Celery/inbox)
    processor = CompletionProcessor(db_url=db_url)
    payload = {
        "event_id": str(uuid4()),
        "evaluation_id": str(eval_id),
        "economic_assessment_id": str(uuid4()),
        "cost_per_beneficiary_pen": "250.00",
        "score_0_100": "80.00",
        "explanation": "Evaluación económica de prueba",
        "algorithm_version": "v1.0",
    }
    processor.process(payload)
    processor.process(payload)

    # Verificar que el estado no avanzó a completed/evaluated y no se duplicó el checkpoint
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        eval_row = conn.execute(
            "SELECT status FROM evaluations WHERE id = %s", (eval_id,)
        ).fetchone()
        assert eval_row["status"] == "pending_review"

        proj_row = conn.execute(
            "SELECT status FROM projects WHERE id = %s", (PROJECT_C_ID,)
        ).fetchone()
        assert proj_row["status"] == "pending_review"

        final_count = conn.execute(
            """SELECT COUNT(*) AS total FROM evaluation_checkpoints
            WHERE project_version_id = %s AND risk_source = 'environmental'""",
            (project_version_id,),
        ).fetchone()["total"]
        assert final_count == initial_count


def test_submit_human_approval_strictly_blocked_while_paused():
    """Garantía de compuerta: mientras el expediente esté 'pending_review',
    submit_human_approval rechaza categóricamente la emisión de aprobación final."""
    service = get_test_platform_service()

    approval_status = service.get_human_approval(PROJECT_C_ID)
    assert approval_status["is_paused"] is True
    assert approval_status["requires_human_approval"] is False
    assert approval_status["is_evaluated"] is False

    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.submit_human_approval(
            project_id=PROJECT_C_ID,
            actor_id=PLANNER_ID,
            decision="approved",
            justification="Intento indebido de aprobar caso con riesgo alto sin resolver checkpoint",
            conditions=None,
            idempotency_key=f"blocked-test-{uuid4()}",
        )
    assert "Pendiente de revisión" in str(exc_info.value)
    assert "HU3.1" in str(exc_info.value)


def test_continuation_when_no_high_risk():
    """CA-HU3.1-02: Continuación cuando no hay riesgo alto.
    Proyectos sin riesgo alto (como PRY-A con riesgo moderado) no detienen el flujo
    ni solicitan revisión humana innecesaria."""
    service = get_test_platform_service()
    project = service.get_project(PROJECT_A_ID)
    db_url = get_test_db_url()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # Verificar que PRY-A no tiene riesgo alto
        risk_condition = RiskCheckpointEngine.detect_high_risk_condition(
            conn, project["project_version_id"]
        )
        assert risk_condition is None

        # Verificar que PRY-A no tiene checkpoint pendiente
        has_checkpoint = RiskCheckpointEngine.has_pending_checkpoint(
            conn, project["project_version_id"]
        )
        assert has_checkpoint is False


def test_insufficient_information_not_confounded_with_low_or_high_risk():
    """Verifica que casos con datos insuficientes (PRY-B) no se traten como bajo riesgo
    pero tampoco se invente un riesgo alto sin causa documentada."""
    service = get_test_platform_service()
    project = service.get_project(PROJECT_B_ID)
    db_url = get_test_db_url()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        risk_condition = RiskCheckpointEngine.detect_high_risk_condition(
            conn, project["project_version_id"]
        )
        # PRY-B no tiene riesgo alto
        assert risk_condition is None


def test_version_isolation_checkpoint_not_inherited():
    """Aislamiento por versión: si un proyecto crea una versión 2 con mitigación,
    no hereda automáticamente el punto de control de la versión 1."""
    db_url = get_test_db_url()
    v1_id = uuid4()
    v2_id = uuid4()
    test_project_id = uuid4()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # Crear proyecto y versión 1
        conn.execute(
            """INSERT INTO projects (id, code, created_by_user_id, status)
            VALUES (%s, %s, %s, 'ready')""",
            (test_project_id, f"PRY-ISO-{uuid4().hex[:6]}", PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, estimated_budget_pen, beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Versión 1', 'Prueba aislamiento', 150000.0, 500, %s)""",
            (v1_id, test_project_id, PLANNER_ID),
        )

        # Crear checkpoint de riesgo alto solo en versión 1
        RiskCheckpointEngine.create_or_get_checkpoint(
            conn,
            project_id=test_project_id,
            project_version_id=v1_id,
            evaluation_id=None,
            risk_info={
                "risk_source": "environmental",
                "risk_source_label": "Impacto ambiental",
                "risk_level": "high",
                "risk_level_label": "Riesgo Alto",
                "reason": "Riesgo alto en versión 1",
            },
        )

        # Verificar que v1 tiene checkpoint activo
        assert RiskCheckpointEngine.has_pending_checkpoint(conn, v1_id) is True

        # Crear versión 2
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, estimated_budget_pen, beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 2, 'Proyecto Versión 2 Mitigada', 'Sin riesgo alto', 150000.0, 500, %s)""",
            (v2_id, test_project_id, PLANNER_ID),
        )

        # Verificar que v2 NO tiene checkpoint activo heredado de v1
        assert RiskCheckpointEngine.has_pending_checkpoint(conn, v2_id) is False
        assert RiskCheckpointEngine.get_active_checkpoint(conn, v2_id) is None


def test_request_evaluation_high_risk_idempotency_returns_same_eval_without_fake_event_id():
    """HU3.1 Caso 1: Repetir request_evaluation con la misma Idempotency-Key
    para un proyecto de riesgo alto devuelve la evaluación y el punto de control existentes,
    con duplicated=True, sin error, sin nueva evaluación y con event_id=None (no ficticio)."""
    service = get_test_platform_service()
    project = service.get_project(PROJECT_C_ID)
    v_id = project["project_version_id"]
    idemp_key = f"idemp-risk-test-{uuid4()}"

    res1 = service.request_evaluation(v_id, PLANNER_ID, idemp_key)
    assert res1["status"] == "pending_review"
    assert res1["status_label"] == "Pendiente de revisión"
    assert res1["duplicated"] is False
    assert res1["event_id"] is None
    assert res1["publication_pending"] is False
    assert res1["checkpoint"] is not None
    assert res1["checkpoint"]["status"] == "pending_review"
    assert res1["checkpoint"]["risk_level"] == "high"

    eval_id_1 = res1["evaluation_id"]

    # Segundo intento con exactamente la misma Idempotency-Key
    res2 = service.request_evaluation(v_id, PLANNER_ID, idemp_key)
    assert res2["evaluation_id"] == eval_id_1
    assert res2["status"] == "pending_review"
    assert res2["status_label"] == "Pendiente de revisión"
    assert res2["duplicated"] is True
    assert res2["event_id"] is None  # Estrictamente None, nunca un UUID inventado
    assert res2["publication_pending"] is False
    assert res2["checkpoint"] is not None
    assert res2["checkpoint"]["status"] == "pending_review"

    # Verificar que no se creó una segunda evaluación en la BD
    db_url = get_test_db_url()
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        count = conn.execute(
            "SELECT count(*) AS total FROM evaluations WHERE idempotency_key = %s",
            (idemp_key,),
        ).fetchone()["total"]
        assert count == 1


def test_completion_processor_late_event_on_paused_evaluation_does_not_expose_result():
    """HU3.1 Caso 2: CompletionProcessor y get_evaluation impiden que una evaluación pausada
    exponga un resultado económico si llega un evento tardío o reintentado."""
    db_url = get_test_db_url()
    service = get_test_platform_service()
    project = service.get_project(PROJECT_C_ID)
    v_id = project["project_version_id"]

    # Crear una evaluación en pending_review
    eval_id = uuid4()
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        criteria_row = conn.execute(
            "SELECT id FROM criteria_versions WHERE status='active' LIMIT 1"
        ).fetchone()
        conn.execute(
            """INSERT INTO evaluations (id, project_version_id, criteria_version_id,
            requested_by_user_id, status, idempotency_key)
            VALUES (%s, %s, %s, %s, 'pending_review', %s)""",
            (eval_id, v_id, criteria_row["id"], PLANNER_ID, str(uuid4())),
        )

    # Llega un evento de finalización económico tardío
    late_event_id = uuid4()
    processor = CompletionProcessor(db_url=db_url)
    payload = {
        "event_id": str(late_event_id),
        "evaluation_id": str(eval_id),
        "economic_assessment_id": str(uuid4()),
        "cost_per_beneficiary_pen": "300.00",
        "score_0_100": "75.00",
        "explanation": "Resultado económico tardío que no debe publicarse",
        "algorithm_version": "v1.0",
    }

    processor.process(payload)

    # Comprobar en base de datos:
    # 1. inbox_events registró el evento para evitar reprocesamiento
    # 2. NO se insertó en economic_result_projections
    # 3. La evaluación sigue en pending_review
    # 4. El proyecto sigue en pending_review
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        inbox = conn.execute(
            "SELECT * FROM inbox_events WHERE event_id = %s", (late_event_id,)
        ).fetchone()
        assert inbox is not None

        proj_row = conn.execute(
            "SELECT count(*) AS total FROM economic_result_projections WHERE evaluation_id = %s",
            (eval_id,),
        ).fetchone()
        assert proj_row["total"] == 0

        ev_row = conn.execute(
            "SELECT status FROM evaluations WHERE id = %s", (eval_id,)
        ).fetchone()
        assert ev_row["status"] == "pending_review"

        p_row = conn.execute(
            "SELECT status FROM projects WHERE id = %s", (PROJECT_C_ID,)
        ).fetchone()
        assert p_row["status"] == "pending_review"

    # 5. get_evaluation devuelve result=None
    eval_data = service.get_evaluation(eval_id)
    assert eval_data["status"] == "pending_review"
    assert eval_data["status_label"] == "Pendiente de revisión"
    assert eval_data["result"] is None
    assert eval_data["checkpoint"] is not None

    # Reintentar el mismo payload: debe descartarse silenciosamente por idempotencia de inbox
    processor.process(payload)
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        proj_count = conn.execute(
            "SELECT count(*) AS total FROM economic_result_projections WHERE evaluation_id = %s",
            (eval_id,),
        ).fetchone()["total"]
        assert proj_count == 0


def test_full_version_lifecycle_v1_high_risk_v2_mitigated_completes_without_inherited_pause():
    """HU3.1 Caso 3: Ciclo de vida completo por versiones.
    Versión 1 con proximidad crítica < 50m genera checkpoint y pausa en pending_review.
    Versión 2 con retiro reglamentario >= 50m evalúa sin riesgo alto, solicita evaluación
    económica con outbox normal y completa sin heredar el bloqueo de la versión 1."""
    db_url = get_test_db_url()
    service = get_test_platform_service()
    project_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-LIFECYCLE-{uuid4().hex[:6]}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        criteria_row = conn.execute(
            "SELECT id FROM criteria_versions WHERE status='active' LIMIT 1"
        ).fetchone()
        # 1. Crear proyecto y versión 1
        conn.execute(
            """INSERT INTO projects (id, code, created_by_user_id, status)
            VALUES (%s, %s, %s, 'ready')""",
            (project_id, code, PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Ciclo V1', 'Diseño inicial junto a río',
                    'Margen izquierda río Shullcas', 'recreacion', 120000.0, 600, %s)""",
            (v1_id, project_id, PLANNER_ID),
        )
        # Registro ambiental crítico para v1 (18 m < 50 m)
        conn.execute(
            """INSERT INTO project_environmental_records
            (id, project_id, project_version_id, project_code, has_sufficient_data,
             environmental_component, declared_impacts, declared_measures, verifiable_evidence,
             proximity_to_water_meters, is_in_protected_or_risk_area, source_name, data_origin)
            VALUES (%s, %s, %s, %s, TRUE, 'recurso_hidrico',
                    'Movimiento de tierras en faja', 'Muro de contención',
                    'Ubicación a 18 m de faja marginal río Shullcas', 18.0, TRUE,
                    'Levantamiento topográfico municipal', 'simulated')""",
            (uuid4(), project_id, v1_id, code),
        )

    # Evaluar ambientalmente v1 -> riesgo alto
    env_v1 = service.evaluate_environmental_assessment(project_id, PLANNER_ID)
    assert env_v1["risk_level"] == "high"
    assert env_v1["requires_human_review"] is True
    assert env_v1["favorable"] is not True  # Nunca favorable automáticamente ante riesgo alto

    # Solicitar evaluación para v1 -> se detiene en checkpoint
    req_v1 = service.request_evaluation(v1_id, PLANNER_ID, f"req-v1-{uuid4()}")
    assert req_v1["status"] == "pending_review"
    assert req_v1["event_id"] is None
    assert req_v1["checkpoint"] is not None
    assert req_v1["checkpoint"]["status"] == "pending_review"

    proj_v1_state = service.get_project(project_id)
    assert proj_v1_state["status"] == "pending_review"

    # 2. Diseñar Versión 2: replanteo del trazo con retiro a 65 m (fuera de faja marginal)
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 2, 'Proyecto Ciclo V2 Reubicado', 'Rediseño con retiro de 65m de la faja marginal',
                    'Zona alta El Tambo fuera de faja marginal', 'recreacion', 130000.0, 600, %s)""",
            (v2_id, project_id, PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_environmental_records
            (id, project_id, project_version_id, project_code, has_sufficient_data,
             environmental_component, declared_impacts, declared_measures, verifiable_evidence,
             proximity_to_water_meters, is_in_protected_or_risk_area, source_name, data_origin)
            VALUES (%s, %s, %s, %s, TRUE, 'recurso_hidrico',
                    'Polvo y tránsito vehicular moderado', 'Riego diario y señalización',
                    'Retiro acreditado a 65 m del cauce hídrico', 65.0, FALSE,
                    'Plano de replanteo y levantamiento acreditado', 'simulated')""",
            (uuid4(), project_id, v2_id, code),
        )
        conn.execute(
            """INSERT INTO project_green_area_records
            (id, project_id, project_version_id, project_code, has_sufficient_data,
             total_project_area_m2, green_area_m2, green_area_percentage, delimitation_description,
             declared_affectation, verifiable_affectation, affectation_type, protection_measures,
             has_sufficient_measures, score_effect_pts, effect_type, calculation_explanation,
             source_name, data_origin)
            VALUES (%s, %s, %s, %s, TRUE, 2000.0, 600.0, 30.0, 'Parque ecológico delimitado',
                    'Sin tala', 'Conservación de arbolado nativo', 'conservacion_positiva',
                    'Riego tecnificado y cerco vivo', TRUE, 15.0, 'bonus',
                    'Bonificación por conservación (+15.0 pts)', 'Plano paisajístico', 'simulated')""",
            (uuid4(), project_id, v2_id, code),
        )

    # Evaluar ambientalmente v2 -> riesgo moderado/bajo y favorable
    env_v2 = service.evaluate_environmental_assessment(project_id, PLANNER_ID)
    assert env_v2["risk_level"] != "high"
    assert env_v2["requires_human_review"] is False
    assert env_v2["favorable"] is True

    # Comprobar que detect_high_risk_condition para v2 retorna None
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        risk_v2 = RiskCheckpointEngine.detect_high_risk_condition(conn, v2_id)
        assert risk_v2 is None
        assert RiskCheckpointEngine.has_pending_checkpoint(conn, v2_id) is False

    # Solicitar evaluación para v2 -> Flujo normal (CA-HU3.1-02)
    req_v2 = service.request_evaluation(v2_id, PLANNER_ID, f"req-v2-{uuid4()}")
    assert req_v2["status"] == "queued"
    assert req_v2["event_id"] is not None
    assert req_v2["checkpoint"] is None
    assert req_v2["duplicated"] is False

    # Simular procesamiento económico para v2
    processor = CompletionProcessor(db_url=db_url)
    completion_payload = {
        "event_id": str(uuid4()),
        "evaluation_id": str(req_v2["evaluation_id"]),
        "economic_assessment_id": str(uuid4()),
        "cost_per_beneficiary_pen": "216.67",
        "score_0_100": "94.44",
        "explanation": "Costo por beneficiario favorable",
        "algorithm_version": "v1.0",
    }
    processor.process(completion_payload)

    # Verificar que v2 completó satisfactoriamente
    eval_v2 = service.get_evaluation(req_v2["evaluation_id"])
    assert eval_v2["status"] == "completed"
    assert eval_v2["status_label"] == "Completada"
    assert eval_v2["checkpoint"] is None
    assert eval_v2["result"] is not None
    assert float(eval_v2["result"]["score_0_100"]) == 94.44

    proj_final = service.get_project(project_id)
    assert proj_final["status"] == "evaluated"

    # Verificar que el checkpoint de v1 permanece aislado en pending_review
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        assert RiskCheckpointEngine.has_pending_checkpoint(conn, v1_id) is True
