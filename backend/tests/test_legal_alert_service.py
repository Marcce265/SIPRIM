import psycopg
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.application.services.pmv1_services import (
    LegalAssessmentEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import (
    ConfiguracionPMV1Error,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PROJECT_D_ID = UUID("a0000000-0000-4000-a000-00000000000d")

LEGAL_ADVISOR_ID = UUID("10000000-0000-4000-a000-000000000004")
ADMIN_ID = UUID("10000000-0000-4000-a000-000000000001")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


@pytest.fixture
def service():
    settings = get_settings()
    return PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )


def test_hu2_3_ca01_detection_sustained_legal_alert(service):
    """
    CA-HU2.3-01: Cuando la revisión encuentra evidencia de incompatibilidad con el plan urbano
    o zona intangible (PRY-D con trazo en faja marginal), el expediente queda marcado con
    'Alerta Legal', indicando motivo y fuente normativa de sustento.
    """
    eval_res = service.evaluate_legal_assessment(PROJECT_D_ID, LEGAL_ADVISOR_ID)

    assert eval_res["status"] == "alerta_legal"
    assert "Alerta Legal" in eval_res["status_label"]
    assert eval_res["has_legal_alert"] is True
    assert eval_res["requires_human_review"] is True
    assert eval_res["legal_alert_motive"] is not None
    motive_lower = eval_res["legal_alert_motive"].lower()
    assert "faja" in motive_lower or "intangible" in motive_lower or "riesgo" in motive_lower
    assert eval_res["legal_alert_norm"] is not None
    assert "SINAGERD" in eval_res["legal_alert_norm"] or "PDM" in eval_res["legal_alert_norm"]

    # Verificar persistencia en base de datos
    get_res = service.get_legal_assessment(PROJECT_D_ID)
    assert get_res["status"] == "alerta_legal"
    assert get_res["has_legal_alert"] is True
    assert get_res["legal_alert_motive"] == eval_res["legal_alert_motive"]


def test_hu2_3_ca01_blocks_human_approval_when_legal_alert_active(service):
    """
    CA-HU2.3-01: Mientras la alerta legal exista, el sistema impide continuar a la aprobación
    definitiva por humanos y a la priorización, hasta que sea levantada por Asesoría Jurídica.
    """
    # 1. Asegurar que PRY-D está evaluado jurídicamente y tiene alerta
    service.evaluate_legal_assessment(PROJECT_D_ID, LEGAL_ADVISOR_ID)

    # 2. Consultar compuerta humana: debe reportar allows_final_approval=False
    status = service.get_human_approval(PROJECT_D_ID)
    assert status["has_legal_alert"] is True
    assert status["allows_final_approval"] is False
    assert len(status["blocking_reasons"]) >= 1
    assert any("Alerta Legal" in r for r in status["blocking_reasons"])

    # 3. Intentar aprobar definitivamente debe fallar con excepción controlada
    idempotency_key = f"approval-attempt-blocked-{uuid4()}"
    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.submit_human_approval(
            project_id=PROJECT_D_ID,
            actor_id=ADMIN_ID,
            decision="approved",
            justification="Aprobación indebida de obra en faja marginal",
            conditions=None,
            idempotency_key=idempotency_key,
        )
    assert "Alerta Legal activa" in str(exc_info.value)
    assert "bloqueada" in str(exc_info.value).lower()


def test_hu2_3_ca02_unproven_situation_sets_requires_review_without_alert(service):
    """
    CA-HU2.3-02: Cuando la revisión no consigue sustento verificable para afirmar una vulneración,
    el sistema señala 'Requiere revisión' en vez de presentar una infracción confirmada o alerta legal.
    """
    eval_res = service.evaluate_legal_assessment(PROJECT_B_ID, LEGAL_ADVISOR_ID)

    assert eval_res["status"] == "requires_review"
    assert eval_res["status_label"] == "Requiere revisión humana"
    assert eval_res["has_legal_alert"] is False  # NUNCA alerta infundada
    assert eval_res["requires_human_review"] is True


def test_hu2_3_resolution_by_authorized_legal_advisor(service):
    """
    HU2.3: La alerta legal puede ser resuelta o levantada formalmente por personal autorizado
    de Asesoría Jurídica con justificación técnica y registro de trazabilidad.
    Tras el levantamiento, la aprobación definitiva queda habilitada.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-RES-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'evaluated')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'Proyecto con alerta resoluble', 'Desc', 'Faja', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'riesgo_faja', 'Afectacion faja', 'Vulnera faja marginal',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (uuid4(), proj_id, v1_id, code),
            )

        # 1. Evaluar para tener alerta activa
        eval_initial = service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)
        assert eval_initial["has_legal_alert"] is True
        assert eval_initial["status"] == "alerta_legal"

        # 2. Asesor legal levanta la alerta formalmente
        resolve_key = f"resolve-pry-{uuid4()}"
        res = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="Acreditación de resolución ANA - Rediseño fuera de faja",
            justification="Se adjunta Resolución Directoral ANA que aprueba la delimitación definitiva de la faja marginal.",
            idempotency_key=resolve_key,
        )
        assert res["project_id"] == proj_id
        assert res["resolution_action"] == "Acreditación de resolución ANA - Rediseño fuera de faja"
        assert res["duplicated"] is False

        # 3. Idempotencia: repetir la misma clave devuelve el registro existente sin duplicar
        res_dup = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="Acreditación de resolución ANA - Rediseño fuera de faja",
            justification="Se adjunta Resolución Directoral ANA que aprueba la delimitación definitiva de la faja marginal.",
            idempotency_key=resolve_key,
        )
        assert res_dup["duplicated"] is True

        # 4. Verificar que get_legal_assessment refleja que la alerta fue levantada
        legal_state = service.get_legal_assessment(proj_id)
        assert legal_state["has_legal_alert"] is False
        assert legal_state["is_resolved"] is True

        # 5. La compuerta humana ahora permite aprobación
        status_after = service.get_human_approval(proj_id)
        assert status_after["has_legal_alert"] is False
        assert status_after["allows_final_approval"] is True

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM legal_alert_resolutions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM legal_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_legal_findings WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu2_3_version_isolation(service):
    """
    HU2.3 - Aislamiento por versiones: una versión posterior mitigada o compatible
    no hereda la alerta legal de una versión anterior sin evaluarse.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-ISO-{uuid4().hex[:6]}"

    try:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO projects (id, code, created_by_user_id, status)
                VALUES (%s, %s, %s, 'evaluated')
                """,
                (proj_id, code, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'V1 con alerta', 'Descripcion v1', 'Rio', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            # Hallazgo no conforme en v1
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'riesgo_faja', 'Afectacion faja marginal', 'Vulnera zona intangible',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (uuid4(), proj_id, v1_id, code),
            )

        # Evaluar V1: debe tener alerta legal
        eval_v1 = service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)
        assert eval_v1["has_legal_alert"] is True
        assert eval_v1["status"] == "alerta_legal"

        # Ahora crear V2 mitigada (sin hallazgos no conformes, nuevo trazo)
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 2, 'V2 Mitigada', 'Trazo rediseñado fuera de faja', 'Calle alterna', 'Parque', 'public', 120000, 600, %s)
                """,
                (v2_id, proj_id, PLANNER_ID),
            )
            # Hallazgo conforme en v2
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'competencia_mun', 'Competencia municipal', 'Conforme a competencias',
                        'LEY27972-01', TRUE, 'Art. 73', TRUE, FALSE)
                """,
                (uuid4(), proj_id, v2_id, code),
            )

        # Evaluar V2: NO hereda la alerta legal de V1
        eval_v2 = service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)
        assert eval_v2["project_version_id"] == str(v2_id)
        assert eval_v2["has_legal_alert"] is False
        assert eval_v2["status"] == "verified"
        assert eval_v2["requires_human_review"] is False

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM legal_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_legal_findings WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))
