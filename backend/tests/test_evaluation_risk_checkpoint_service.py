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
