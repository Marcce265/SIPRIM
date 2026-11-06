import psycopg
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from backend.application.services.pmv1_services import (
    PlatformService,
    RiskCheckpointEngine,
)
from backend.domain.exceptions.pmv1_exceptions import (
    AccesoDenegadoError,
    ConfiguracionPMV1Error,
    RecursoPMV1NoEncontradoError,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")
ADMIN_ID = UUID("10000000-0000-4000-a000-000000000001")
LEGAL_ADVISOR_ID = UUID("10000000-0000-4000-a000-000000000003")


@pytest.fixture
def service():
    settings = get_settings()
    return PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )


def test_hu3_4_ca01_valid_resume_continues_and_preserves_results(service):
    """
    CA-HU3.4-01: Con pausa persistida y decisión válida de un responsable autorizado,
    continúa desde el checkpoint, conserva los resultados anteriores y no repite etapas ya completadas.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-HITL-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto con riesgo alto pausado', 'Desc', 'Río Mantaro', 'Parque', 'public', 200000, 1000, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            # Fila de evaluación ambiental previa (etapa completada que debe conservarse)
            conn.execute(
                """
                INSERT INTO environmental_assessments
                (id, project_id, project_version_id, assessed_by_user_id, idempotency_key, status, risk_level,
                 risk_observation, requires_human_review, favorable, summary, impacts_json, mitigations_json, declared_vs_evidence_json, evaluated_at)
                VALUES (%s, %s, %s, %s, 'env-key-prior', 'evaluated', 'high',
                        'Proximidad crítica a cuerpo de agua (15m)', TRUE, FALSE, 'Resumen ambiental', '[]', '[]', '{"proximity_to_water_meters": 15}', now())
                """,
                (uuid4(), proj_id, v1_id, PLANNER_ID),
            )
            # Checkpoint persistido en pending_review
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Causa técnica de pausa: Riesgo ambiental alto por proximidad a agua', 'environmental', 'high',
                        '{"cause": "Proximidad crítica a agua", "observation": "Requiere verificación de enrocado de contención"}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        # 1. Comprobar que el proyecto y checkpoint están en 'pending_review'
        cp_before = service.get_project_checkpoint(proj_id)
        assert cp_before is not None
        assert cp_before["status"] == "pending_review"
        assert cp_before["allows_final_approval"] is False

        # 2. Planificador/Gerente autorizado reanuda formalmente
        resume_key = f"resume-test-{uuid4()}"
        res = service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Se aprueba continuar tras verificación de muro de gaviones y expediente de contención fluvial.",
            conditions="Verificar periódicamente el nivel de socavación en ribera.",
            idempotency_key=resume_key,
        )

        assert res["status"] == "resolved"
        assert res["project_status"] == "evaluated"
        assert res["resolved_by_user_id"] == PLANNER_ID
        assert res["resolution_motive"] == "Se aprueba continuar tras verificación de muro de gaviones y expediente de contención fluvial."
        assert res["resolution_conditions"] == "Verificar periódicamente el nivel de socavación en ribera."
        assert res["duplicated"] is False

        # 3. Comprobar que en base de datos se conserva la evaluación ambiental anterior
        with psycopg.connect(db_url) as conn:
            env_row = conn.execute(
                "SELECT risk_level, risk_observation FROM environmental_assessments WHERE project_version_id = %s",
                (v1_id,),
            ).fetchone()
            assert env_row is not None
            assert env_row[0] == "high", "Resultados ambientales anteriores deben conservarse sin reiniciarse"

            # Checkpoint persistido como resolved con auditoría
            cp_db = conn.execute(
                "SELECT status, resolution_motive, resolved_by_user_id FROM evaluation_checkpoints WHERE project_version_id = %s",
                (v1_id,),
            ).fetchone()
            assert cp_db[0] == "resolved"
            assert cp_db[2] == PLANNER_ID

            # Evento de auditoría registrado
            audit = conn.execute(
                "SELECT action, details FROM audit_events WHERE action = 'CHECKPOINT_RESUMED' ORDER BY occurred_at DESC LIMIT 1"
            ).fetchone()
            assert audit is not None
            assert audit[0] == "CHECKPOINT_RESUMED"

        # 4. Estado del proyecto recuperado es 'evaluated' y checkpoint resuelto
        p_after = service.get_project(proj_id)
        assert p_after["status"] == "evaluated"

        cp_after = service.get_project_checkpoint(proj_id)
        assert cp_after is not None
        assert cp_after["status"] == "resolved"
        assert cp_after["allows_final_approval"] is True

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM environmental_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu3_4_ca02_unauthorized_user_rejected_retains_pending_review(service):
    """
    CA-HU3.4-02: Sin autorización válida o con un usuario sin permiso (ej. Asesor Legal
    intentando decidir sobre reanudación de planeamiento), rechaza la reanudación y conserva 'Pendiente de revisión'.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-UNAUTH-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto para prueba no autorizada', 'Desc', 'Río', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Pausa por riesgo ambiental', 'environmental', 'high', '{}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        # Usuario no autorizado: Asesor Legal intenta reanudar checkpoint de planeamiento
        with pytest.raises(AccesoDenegadoError) as exc_info:
            service.resume_project_checkpoint(
                project_id=proj_id,
                actor_id=LEGAL_ADVISOR_ID,
                justification="Asesor legal intentando reanudar proceso de planeamiento",
                conditions=None,
                idempotency_key=f"unauth-resume-{uuid4()}",
            )
        assert "no cuenta con perfil de Gerente de Planeamiento" in str(exc_info.value)

        # Verificar que el checkpoint y el proyecto CONSERVAN estrictamente 'pending_review'
        cp = service.get_project_checkpoint(proj_id)
        assert cp is not None
        assert cp["status"] == "pending_review"

        p = service.get_project(proj_id)
        assert p["status"] == "pending_review"

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu3_4_ca03_new_version_does_not_reuse_previous_approval(service):
    """
    CA-HU3.4-03: Si el expediente se modificó sustancialmente desde la pausa (nueva versión v2),
    el sistema NO reutiliza la aprobación de reanudación previa para la nueva versión
    y exige una evaluación correspondiente a los datos actualizados.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-V2-CP-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            # Versión 1
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Versión 1 pausada', 'Desc', 'Río', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Pausa v1', 'environmental', 'high', '{}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        # Reanudar versión 1
        service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Reanudación aprobada para versión 1",
            conditions=None,
            idempotency_key=f"resume-v1-{uuid4()}",
        )

        # Se crea la Versión 2 por cambios sustanciales
        service.create_project_version(
            project_id=proj_id,
            title="Versión 2 con trazo reformulado",
            description="Nueva propuesta sustancial",
            location_description="Zona alta alejada de ribera",
            proposed_land_use="Vivienda",
            estimated_budget_pen=Decimal("150000.00"),
            beneficiaries_count=600,
            actor_id=PLANNER_ID,
        )

        # Consultar la versión vigente v2: no debe heredar la resolución de v1
        cp_v2 = service.get_project_checkpoint(proj_id)
        # La nueva versión no tiene checkpoint hasta que se evalúe de nuevo
        assert cp_v2 is None

        # Si se genera un nuevo riesgo en v2, tendrá su propio checkpoint en pending_review
        p_current = service.get_project(proj_id)
        assert p_current["version_number"] == 2
        assert p_current["status"] == "ready"

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu3_4_idempotent_retry_and_mismatch_protection(service):
    """
    HU3.4: Reintentos exactos con la misma idempotency key devuelven duplicated=True.
    Reutilizar la clave con otra justificación u otro expediente es rechazado.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-IDEM-CP-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto para idempotencia CP', 'Desc', 'Sitio', 'Urbano', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Pausa por riesgo', 'environmental', 'high', '{}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        key = f"key-cp-{uuid4()}"
        res1 = service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Justificación original primera vez",
            conditions="Condición A",
            idempotency_key=key,
        )
        assert res1["duplicated"] is False

        # Reintento exacto
        res2 = service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Justificación original primera vez",
            conditions="Condición A",
            idempotency_key=key,
        )
        assert res2["duplicated"] is True

        # Reintento con justificación cambiada
        with pytest.raises(ConfiguracionPMV1Error) as exc_info:
            service.resume_project_checkpoint(
                project_id=proj_id,
                actor_id=PLANNER_ID,
                justification="Justificación adulterada distinta",
                conditions=None,
                idempotency_key=key,
            )
        assert "justificación distinta" in str(exc_info.value)

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu3_4_resuming_does_not_equal_final_human_approval(service):
    """
    HU3.4: Autorizar la continuación del procesamiento no equivale a aprobar definitivamente el proyecto.
    El dictamen formal humano debe realizarse por separado.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-APPR-CP-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto para verificar no aprobación automática', 'Desc', 'Sitio', 'Urbano', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Pausa temporal', 'environmental', 'high', '{}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        # Reanudar desde el checkpoint
        service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Levantamiento de pausa para continuar análisis",
            conditions=None,
            idempotency_key=f"resume-not-final-{uuid4()}",
        )

        # Comprobar que en human_approvals NO se ha registrado aprobación final automática
        approval_state = service.get_human_approval(proj_id)
        assert approval_state["current_approval"] is None
        assert approval_state["current_approval"] is None
        # El proyecto pasó a evaluated, no a approved
        p = service.get_project(proj_id)
        assert p["status"] == "evaluated"
        assert p["status"] != "approved"

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu3_4_invalid_or_short_justification_rejected(service):
    """
    HU3.4: Rechaza solicitudes de reanudación con justificación vacía o menor a 5 caracteres.
    """
    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.resume_project_checkpoint(
            project_id=PROJECT_B_ID,
            actor_id=PLANNER_ID,
            justification="  ab  ",  # Solo 2 caracteres útiles
            conditions=None,
            idempotency_key=f"short-just-{uuid4()}",
        )
    assert "al menos 5 caracteres" in str(exc_info.value)


def test_hu3_4_nonexistent_checkpoint_rejected(service):
    """
    HU3.4: Si el expediente no tiene un punto de control en su versión vigente,
    la reanudación falla con recurso no encontrado.
    """
    fake_proj = uuid4()
    with pytest.raises(RecursoPMV1NoEncontradoError):
        service.resume_project_checkpoint(
            project_id=fake_proj,
            actor_id=PLANNER_ID,
            justification="Reanudación sobre proyecto inexistente",
            conditions=None,
            idempotency_key=f"fake-{uuid4()}",
        )


def test_hu3_4_already_resolved_checkpoint_rejected_for_new_request(service):
    """
    HU3.4: Si un checkpoint ya fue resuelto previamente, un nuevo intento con distinta clave
    es rechazado indicando que ya fue resuelto.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-ALR-RES-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'pending_review')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto para doble reanudación', 'Desc', 'Río', 'Urbano', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO evaluation_checkpoints
                (id, project_id, project_version_id, checkpoint_type, status, reason, risk_source, risk_level, details)
                VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                        'Pausa inicial', 'environmental', 'high', '{}')
                """,
                (uuid4(), proj_id, v1_id),
            )

        # 1. Primera reanudación exitosa
        service.resume_project_checkpoint(
            project_id=proj_id,
            actor_id=PLANNER_ID,
            justification="Primera reanudación válida autorizada",
            conditions=None,
            idempotency_key=f"first-res-{uuid4()}",
        )

        # 2. Segunda reanudación con clave nueva sobre el mismo checkpoint ya resuelto
        with pytest.raises(ConfiguracionPMV1Error) as exc_info:
            service.resume_project_checkpoint(
                project_id=proj_id,
                actor_id=PLANNER_ID,
                justification="Segunda reanudación indebida sobre checkpoint resuelto",
                conditions=None,
                idempotency_key=f"second-res-{uuid4()}",
            )
        assert "ya ha sido resuelto o reanudado previamente" in str(exc_info.value)

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM evaluation_checkpoints WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))
