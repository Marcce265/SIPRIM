import psycopg
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.application.services.pmv1_services import (
    LegalAssessmentEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import (
    AccesoDenegadoError,
    ConfiguracionPMV1Error,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PROJECT_D_ID = UUID("a0000000-0000-4000-a000-00000000000d")

LEGAL_ADVISOR_ID = UUID("10000000-0000-4000-a000-000000000003")
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
    # 1. Asegurar que PRY-D esté evaluado jurídicamente y tiene alerta
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

        # 2. Asesor legal levanta la alerta formalmente con acción válida y evidencia
        resolve_key = f"resolve-pry-{uuid4()}"
        res = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Se adjunta Resolución Directoral ANA que aprueba la delimitación definitiva de la faja marginal.",
            evidence_reference="RD-ANA-045-2026",
            idempotency_key=resolve_key,
        )
        assert res["project_id"] == proj_id
        assert res["resolution_action"] == "subsanado_en_expediente"
        assert res["evidence_reference"] == "RD-ANA-045-2026"
        assert res["duplicated"] is False

        # 3. Idempotencia: repetir la misma clave devuelve el registro existente sin duplicar
        res_dup = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Se adjunta Resolución Directoral ANA que aprueba la delimitación definitiva de la faja marginal.",
            evidence_reference="RD-ANA-045-2026",
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


def test_hu2_3_resolution_does_not_mutate_findings_to_complies_true(service):
    """
    CORRECCIÓN DEFECTO HU2.3: La resolución de una alerta legal NO debe modificar silenciosamente
    hallazgos históricos de project_legal_findings desde complies=FALSE a complies=TRUE.
    La decisión humana se registra por separado y los hallazgos originales se conservan intactos.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-AUDIT-{uuid4().hex[:6]}"
    finding_id = uuid4()

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
                VALUES (%s, %s, 1, 'Proyecto para verificar no mutación de hallazgos', 'Desc', 'Faja', 'Parque', 'public', 150000, 600, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'faja_marginal', 'Invasión de faja', 'Afecta faja marginal',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (finding_id, proj_id, v1_id, code),
            )

        # 1. Evaluar
        service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)

        # 2. Asesor legal resuelve como falso positivo con sustento
        service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="falso_positivo",
            justification="Inspección ocular y levantamiento topográfico demuestran que las coordenadas no tocan la faja.",
            evidence_reference="INFORME-TOPOGRAFICO-012-2026",
            idempotency_key=f"res-audit-{uuid4()}",
        )

        # 3. Comprobar en base de datos que project_legal_findings conserva complies=FALSE
        with psycopg.connect(db_url) as conn:
            f_row = conn.execute(
                "SELECT complies, requires_human_review FROM project_legal_findings WHERE id = %s",
                (finding_id,),
            ).fetchone()
            assert f_row is not None
            # Hallazgo original DEBE seguir siendo FALSE (no mutar a TRUE)
            assert f_row[0] is False, "Defecto detectado: una resolución no debe mutar complies=FALSE a TRUE"

            # La resolución se guardó por separado en legal_alert_resolutions
            res_row = conn.execute(
                "SELECT resolution_action, evidence_reference, justification FROM legal_alert_resolutions WHERE project_id = %s",
                (proj_id,),
            ).fetchone()
            assert res_row is not None
            assert res_row[0] == "falso_positivo"
            assert res_row[1] == "INFORME-TOPOGRAFICO-012-2026"

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM legal_alert_resolutions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM legal_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_legal_findings WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu2_3_resolution_fails_without_active_alert(service):
    """
    HU2.3: Solo permite resolver una alerta activa de la versión vigente.
    Si no existe alerta activa, rechaza la operación de forma clara.
    """
    # PRY-A no tiene alerta legal
    service.evaluate_legal_assessment(PROJECT_A_ID, LEGAL_ADVISOR_ID)

    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.resolve_legal_alert(
            project_id=PROJECT_A_ID,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Intento de resolver una alerta inexistente",
            idempotency_key=f"no-alert-{uuid4()}",
        )
    assert "No existe una Alerta Legal activa" in str(exc_info.value)


def test_hu2_3_resolution_rejected_for_unauthorized_user(service):
    """
    HU2.3: Exige usuario con el rol autorizado (LEGAL_ADVISOR o ADMIN).
    Rechaza usuarios no autorizados (ej. PLANNER).
    """
    # PRY-D tiene alerta activa
    service.evaluate_legal_assessment(PROJECT_D_ID, LEGAL_ADVISOR_ID)

    with pytest.raises(AccesoDenegadoError) as exc_info:
        service.resolve_legal_alert(
            project_id=PROJECT_D_ID,
            actor_id=PLANNER_ID,  # Planificador NO tiene rol de Asesor Jurídico
            resolution_action="subsanado_en_expediente",
            justification="Planificador intentando levantar alerta legal",
            idempotency_key=f"unauth-{uuid4()}",
        )
    assert "no cuenta con perfil de Asesor Jurídico o Administrador autorizado" in str(exc_info.value)


def test_hu2_3_resolution_rejected_for_invalid_action(service):
    """
    HU2.3: Valida el tipo de decisión; no acepta cualquier cadena como resolution_action.
    """
    service.evaluate_legal_assessment(PROJECT_D_ID, LEGAL_ADVISOR_ID)

    with pytest.raises(ConfiguracionPMV1Error) as exc_info:
        service.resolve_legal_alert(
            project_id=PROJECT_D_ID,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="cadena_invalida_no_reconocida",
            justification="Justificación con acción arbitraria",
            idempotency_key=f"invalid-action-{uuid4()}",
        )
    assert "no válida" in str(exc_info.value)


def test_hu2_3_idempotency_prevents_duplicates_and_mismatch(service):
    """
    HU2.3: Asegura que los reintentos no creen decisiones duplicadas y que una clave
    de idempotencia no pueda reutilizarse con otra versión o con datos distintos.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    proj_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-IDEM-{uuid4().hex[:6]}"

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
                VALUES (%s, %s, 1, 'Proyecto para idempotencia', 'Desc', 'Faja', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'faja', 'Faja', 'Afecta faja',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (uuid4(), proj_id, v1_id, code),
            )

        service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)

        key = f"key-test-{uuid4()}"
        res1 = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Justificación original primera vez",
            idempotency_key=key,
        )
        assert res1["duplicated"] is False

        # Reintento exacto: devuelve duplicated=True
        res2 = service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Justificación original primera vez",
            idempotency_key=key,
        )
        assert res2["duplicated"] is True

        # Reintento con datos distintos: falla por uso inconsistente de idempotency key
        with pytest.raises(ConfiguracionPMV1Error) as exc_info:
            service.resolve_legal_alert(
                project_id=proj_id,
                actor_id=LEGAL_ADVISOR_ID,
                resolution_action="falso_positivo",  # Acción diferente
                justification="Justificación modificada fraudulenta",
                idempotency_key=key,
            )
        assert "datos de resolución distintos" in str(exc_info.value)

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM legal_alert_resolutions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM legal_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_legal_findings WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu2_3_version_isolation_prevents_modifying_other_versions(service):
    """
    HU2.3: Limita cualquier actualización de estado a la versión correcta.
    La resolución de una versión no puede alterar evaluaciones previas del mismo proyecto.
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
            # Versión 1
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 1, 'V1 con alerta', 'Desc', 'Faja', 'Parque', 'public', 100000, 500, %s)
                """,
                (v1_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'riesgo_faja_v1', 'Afectacion faja', 'Vulnera faja en v1',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (uuid4(), proj_id, v1_id, code),
            )

        # Evaluar versión 1
        service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)

        # Crear Versión 2 (replanteada)
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute(
                """
                INSERT INTO project_versions
                (id, project_id, version_number, title, description, location_description, proposed_land_use,
                 territorial_data_origin, estimated_budget_pen, beneficiaries_count, created_by_user_id)
                VALUES (%s, %s, 2, 'V2 replanteada', 'Desc', 'Fuera de faja', 'Parque', 'public', 120000, 550, %s)
                """,
                (v2_id, proj_id, PLANNER_ID),
            )
            conn.execute(
                """
                INSERT INTO project_legal_findings
                (id, project_id, project_version_id, project_code, finding_key, title, description,
                 normative_chunk_id, has_precise_reference, custom_article_or_section, complies, requires_human_review)
                VALUES (%s, %s, %s, %s, 'riesgo_faja_v2', 'Afectacion faja v2', 'Vulnera faja en v2',
                        'PDUPDM-04', TRUE, 'SINAGERD - Ley 29664', FALSE, TRUE)
                """,
                (uuid4(), proj_id, v2_id, code),
            )

        # Evaluar versión 2 (ahora vigente)
        eval_v2 = service.evaluate_legal_assessment(proj_id, LEGAL_ADVISOR_ID)
        assert eval_v2["project_version_id"] == str(v2_id)
        assert eval_v2["has_legal_alert"] is True

        # Resolver la alerta para la versión 2
        service.resolve_legal_alert(
            project_id=proj_id,
            actor_id=LEGAL_ADVISOR_ID,
            resolution_action="subsanado_en_expediente",
            justification="Levantamiento formal exclusivamente para la versión 2",
            idempotency_key=f"res-v2-{uuid4()}",
        )

        # Comprobar que Versión 1 SIGUE con has_legal_alert=True y is_resolved=False en base de datos
        with psycopg.connect(db_url) as conn:
            v1_eval = conn.execute(
                "SELECT has_legal_alert, is_resolved FROM legal_assessments WHERE project_id = %s AND project_version_id = %s",
                (proj_id, v1_id),
            ).fetchone()
            assert v1_eval is not None
            assert v1_eval[0] is True, "La evaluación de versión 1 no debió haber sido modificada"
            assert v1_eval[1] is False, "La evaluación de versión 1 no debe figurar como resuelta"

            v2_eval = conn.execute(
                "SELECT has_legal_alert, is_resolved FROM legal_assessments WHERE project_id = %s AND project_version_id = %s",
                (proj_id, v2_id),
            ).fetchone()
            assert v2_eval is not None
            assert v2_eval[0] is False
            assert v2_eval[1] is True

    finally:
        with psycopg.connect(db_url) as conn, conn.transaction():
            conn.execute("DELETE FROM legal_alert_resolutions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM legal_assessments WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_legal_findings WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM project_versions WHERE project_id = %s", (proj_id,))
            conn.execute("DELETE FROM projects WHERE id = %s", (proj_id,))


def test_hu2_3_prioritization_control(service):
    """
    HU2.3: Verifica el control de precondiciones para la futura priorización definitiva.
    Identifica el bloqueo mientras exista una alerta activa y su liberación tras la resolución.
    """
    # 1. PRY-D con alerta activa
    service.evaluate_legal_assessment(PROJECT_D_ID, LEGAL_ADVISOR_ID)
    prio_check = service.verify_prioritization_allowed(PROJECT_D_ID)
    assert prio_check["allows_prioritization"] is False
    assert any("Alerta Legal activa" in r for r in prio_check["blocking_reasons"])

    # 2. PRY-A sin alerta legal
    service.evaluate_legal_assessment(PROJECT_A_ID, LEGAL_ADVISOR_ID)
    prio_a = service.verify_prioritization_allowed(PROJECT_A_ID)
    assert prio_a["allows_prioritization"] is True
    assert len(prio_a["blocking_reasons"]) == 0
