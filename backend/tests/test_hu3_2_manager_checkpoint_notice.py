from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from backend.application.services.pmv1_services import (
    CompletionProcessor,
    PlatformService,
    RiskCheckpointEngine,
)
from backend.domain.exceptions.pmv1_exceptions import (
    ConfiguracionPMV1Error,
    CredencialesInvalidasError,
)
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_platform_service,
)
from backend.infrastructure.config.settings import get_settings
from backend.main import create_app

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_C_ID = UUID("a0000000-0000-4000-a000-00000000000c")
ADMIN_USER_ID = UUID("10000000-0000-4000-a000-000000000001")
PLANNER_USER_ID = UUID("10000000-0000-4000-a000-000000000002")
CITIZEN_USER_ID = UUID("10000000-0000-4000-a000-000000000099")


def get_test_db_url() -> str:
    settings = get_settings()
    return settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)


class ManagerMockAuth:
    """Mock de autenticación que soporta el rol ADMIN (Gerente) y roles no autorizados."""

    def decode(self, token: str) -> dict[str, Any]:
        if token == "token-gerente-admin":
            return {
                "sub": str(ADMIN_USER_ID),
                "roles": ["ADMIN"],
            }
        if token == "token-planner":
            return {
                "sub": str(PLANNER_USER_ID),
                "roles": ["PLANNER"],
            }
        if token == "token-ciudadano":
            return {
                "sub": str(CITIZEN_USER_ID),
                "roles": ["CITIZEN"],
            }
        raise CredencialesInvalidasError("Token no válido o expirado")


@pytest.fixture
def api_client() -> TestClient:
    db_url = get_test_db_url()
    platform_svc = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)
    auth_svc = ManagerMockAuth()

    app = create_app()
    app.dependency_overrides[get_platform_service] = lambda: platform_svc
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    return TestClient(app)


def test_manager_authorized_queries_paused_project_checkpoint_details(api_client: TestClient):
    """CA-HU3.2-01: Un gerente autorizado (ADMIN) abre el expediente pausado y ve
    un aviso claro con el proyecto afectado, el estado 'Pendiente de revisión',
    la causa específica de la pausa y la observación concreta que debe revisar."""
    headers = {"Authorization": "Bearer token-gerente-admin"}

    # 1. Consulta el punto de control directo del expediente pausado (PRY-C)
    resp = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}/checkpoint", headers=headers)
    assert resp.status_code == 200, resp.text
    checkpoint = resp.json()
    assert checkpoint is not None
    assert checkpoint["status"] == "pending_review"
    assert checkpoint["status_label"] == "Pendiente de revisión"
    assert checkpoint["risk_level"] == "high"
    assert checkpoint["risk_level_label"] == "Riesgo Alto"
    assert checkpoint["requires_human_review"] is True
    assert checkpoint["allows_final_approval"] is False

    # CA-HU3.2-01: Causa específica de la pausa
    cause = checkpoint.get("cause") or checkpoint.get("reason")
    assert cause is not None
    assert len(cause.strip()) > 0
    assert "shullcas" in cause.lower() or "faja marginal" in cause.lower() or "cuerpo de agua" in cause.lower()

    # CA-HU3.2-01: Observación concreta que necesita revisión humana
    observation = checkpoint.get("observation")
    assert observation is not None
    assert len(observation.strip()) > 0

    # REGLA HU3.2: La causa técnica y la observación para el gerente deben estar distinguidas
    assert cause != observation or "Causa" in cause

    # Fecha persistida del punto de control
    assert checkpoint["created_at"] is not None
    parsed_date = datetime.fromisoformat(checkpoint["created_at"])
    assert parsed_date.year >= 2026

    # 2. Consulta el expediente pausado completo: incluye el proyecto y el checkpoint vigente
    proj_resp = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}", headers=headers)
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    assert proj_data["code"] == "PRY-C"
    assert proj_data["status"] == "pending_review"
    assert proj_data["checkpoint"] is not None
    assert proj_data["checkpoint"]["status"] == "pending_review"
    assert proj_data["checkpoint"]["observation"] is not None


def test_unauthorized_user_cannot_access_checkpoint_info(api_client: TestClient):
    """Verifica que un usuario no autenticado o sin rol facultado no pueda consultar
    el punto de control ni los datos del expediente pausado."""
    # 1. Sin encabezado de autorización
    resp_no_auth = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}/checkpoint")
    assert resp_no_auth.status_code == 401

    # 2. Con rol no facultado (CITIZEN)
    headers_citizen = {"Authorization": "Bearer token-ciudadano"}
    resp_citizen = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}/checkpoint", headers=headers_citizen)
    assert resp_citizen.status_code == 403

    proj_citizen = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}", headers=headers_citizen)
    assert proj_citizen.status_code == 403


def test_repeated_queries_do_not_alter_state_or_regenerate_evaluations(api_client: TestClient):
    """CA-HU3.2-02: Consultar repetidamente el aviso o el expediente no altera el estado,
    no ejecuta nuevas evaluaciones y no crea puntos de control duplicados."""
    headers = {"Authorization": "Bearer token-gerente-admin"}
    db_url = get_test_db_url()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        eval_count_before = conn.execute("SELECT COUNT(*) AS total FROM evaluations").fetchone()["total"]
        checkpoint_count_before = conn.execute("SELECT COUNT(*) AS total FROM evaluation_checkpoints").fetchone()["total"]

    # Consultar 4 veces seguidas (simulando recargas de página o consultas reiteradas)
    for _ in range(4):
        resp = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}/checkpoint", headers=headers)
        assert resp.status_code == 200
        cp = resp.json()
        assert cp["status"] == "pending_review"

        proj_resp = api_client.get(f"/api/v1/projects/{PROJECT_C_ID}", headers=headers)
        assert proj_resp.status_code == 200
        assert proj_resp.json()["status"] == "pending_review"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        eval_count_after = conn.execute("SELECT COUNT(*) AS total FROM evaluations").fetchone()["total"]
        checkpoint_count_after = conn.execute("SELECT COUNT(*) AS total FROM evaluation_checkpoints").fetchone()["total"]

    # No se crearon nuevas evaluaciones ni nuevos puntos de control
    assert eval_count_after == eval_count_before
    assert checkpoint_count_after == checkpoint_count_before


def test_unpaused_project_does_not_return_checkpoint(api_client: TestClient):
    """Verifica que un expediente no pausado (PRY-A) no retorne punto de control
    y su estado no sea 'pending_review'."""
    headers = {"Authorization": "Bearer token-gerente-admin"}

    # PRY-A es un expediente con impacto bajo/mitigable, sin pausa de riesgo alto
    resp = api_client.get(f"/api/v1/projects/{PROJECT_A_ID}/checkpoint", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None

    proj_resp = api_client.get(f"/api/v1/projects/{PROJECT_A_ID}", headers=headers)
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    assert proj_data["code"] == "PRY-A"
    assert proj_data["status"] != "pending_review"
    assert proj_data["checkpoint"] is None


def test_checkpoint_observation_missing_shows_clarification_notice_and_pending_state():
    """HU3.2: Cuando la causa está presente pero falta la observación, el sistema no copia
    la causa a la observación, sino que muestra 'Observación pendiente de aclaración'
    y conserva estrictamente el estado pendiente."""
    db_url = get_test_db_url()
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-OBS-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Sin Observacion Detallada', 'Riesgo con causa pero sin observacion',
                    'Faja marginal', 'equipamiento', 95000.0, 400, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        # Checkpoint con causa técnica explícita pero details sin observación
        causa_tecnica = "Causa técnica: Proximidad crítica de 20 m al cauce hídrico sin muro de contención"
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    %s, 'environmental', 'high', '{"cause": "Causa técnica: Proximidad crítica de 20 m al cauce hídrico sin muro de contención"}'::jsonb, now(), now())""",
            (uuid4(), project_id, v1_id, causa_tecnica),
        )

        cp = RiskCheckpointEngine.get_active_checkpoint(conn, v1_id)
        assert cp is not None
        assert cp["status"] == "pending_review"
        assert cp["status_label"] == "Pendiente de revisión"

        # Verificar que NO se copió la causa técnica a la observación
        assert cp["cause"] == causa_tecnica
        assert cp["observation"] == "Observación pendiente de aclaración"
        assert cp["observation"] != cp["cause"]
        assert cp["requires_human_review"] is True


def test_checkpoint_cause_and_observation_stored_separately_when_backed():
    """HU3.2: Verifica que cuando existe sustento real, causa y observación se guardan
    y exponen por separado sin duplicar cause en observation ni inventar detalles."""
    db_url = get_test_db_url()
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-SEP-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Causa y Observacion Separadas', 'Expediente con sustento formal',
                    'Zona ribereña Shullcas', 'recreacion', 120000.0, 500, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        causa_real = "Causa técnica de pausa: Distancia crítica a cuerpo de agua (15.0 m < 50 m reglamentarios)."
        observacion_real = "Comprobación técnica requerida: Inspección de campo de delimitación de faja marginal del Río Shullcas y autorización de ANA."

        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    %s, 'environmental', 'high',
                    %s::jsonb, now(), now())""",
            (
                uuid4(),
                project_id,
                v1_id,
                causa_real,
                f'{{"cause": "{causa_real}", "observation": "{observacion_real}", "risk_observation": "{observacion_real}"}}',
            ),
        )

        cp = RiskCheckpointEngine.get_active_checkpoint(conn, v1_id)
        assert cp is not None
        assert cp["cause"] == causa_real
        assert cp["observation"] == observacion_real
        assert cp["cause"] != cp["observation"]
        assert "Distancia crítica" in cp["cause"]
        assert "Inspección de campo" in cp["observation"]


def test_full_journey_v1_paused_followed_by_v2_mitigated_api_and_approval_gate(api_client: TestClient):
    """HU3.2 punto 2: Recorrido completo de una versión 2 mitigada cuando la versión 1
    sigue teniendo un checkpoint pendiente.
    Comprueba:
    1. v1 tiene checkpoint activo y estado pending_review.
    2. El checkpoint histórico de v1 se conserva intacto en la base de datos (no se resuelve artificialmente).
    3. v2 mitigada vista por API y servicio NO tiene checkpoint activo y su estado efectivo para la versión vigente NO es pending_review.
    4. El aviso no bloquea al gerente en v2.
    5. La compuerta de aprobación (human_approvals) evalúa la versión vigente: rechaza aprobar v1 pausada pero permite aprobar v2 una vez evaluada."""
    db_url = get_test_db_url()
    headers_mgr = {"Authorization": "Bearer token-gerente-admin"}
    project_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-MIG-{uuid4().hex[:4].upper()}"

    # Paso 1: Crear proyecto y versión 1 con riesgo alto
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Puente V1', 'Versión inicial con trazo en faja marginal',
                    'Río Shullcas faja marginal', 'equipamiento', 180000.0, 700, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        v1_cp_id = uuid4()
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    'Causa técnica v1: Proximidad de 18m a faja marginal', 'environmental', 'high',
                    '{"cause": "Causa técnica v1: Proximidad de 18m a faja marginal", "observation": "Observación v1: Requiere autorización expresa de ANA"}'::jsonb,
                    now(), now())""",
            (v1_cp_id, project_id, v1_id),
        )

        # Paso 2: Crear versión 2 replanteada/mitigada (fuera de faja marginal, 75m)
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 2, 'Proyecto Puente V2 Mitigado', 'Versión replanteada con retiro reglamentario a 75m',
                    'Zona segura alta El Tambo', 'equipamiento', 195000.0, 750, %s)""",
            (v2_id, project_id, ADMIN_USER_ID),
        )

    # Paso 3: Consultar el proyecto por API con sesión de gerente
    proj_resp = api_client.get(f"/api/v1/projects/{project_id}", headers=headers_mgr)
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    assert proj_data["version_number"] == 2
    assert proj_data["project_version_id"] == str(v2_id)

    # Comprobar que v2 NO tiene checkpoint activo y su estado efectivo para v2 NO es pending_review
    assert proj_data["checkpoint"] is None
    assert proj_data["status"] != "pending_review"

    # Paso 4: Consultar el endpoint de checkpoint para el proyecto vigente
    cp_resp = api_client.get(f"/api/v1/projects/{project_id}/checkpoint", headers=headers_mgr)
    assert cp_resp.status_code == 200
    assert cp_resp.json() is None

    # Paso 5: Consultar la compuerta de aprobación del proyecto vigente
    appr_status_resp = api_client.get(f"/api/v1/projects/{project_id}/approval", headers={"Authorization": "Bearer token-planner"})
    assert appr_status_resp.status_code == 200
    appr_status_data = appr_status_resp.json()
    assert appr_status_data["is_paused"] is False
    assert appr_status_data["checkpoint"] is None

    # Paso 6: Verificar que el checkpoint histórico de v1 sigue conservado intacto en base de datos
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        v1_cp_row = conn.execute(
            "SELECT id, status, project_version_id FROM evaluation_checkpoints WHERE id = %s",
            (v1_cp_id,),
        ).fetchone()
        assert v1_cp_row is not None
        assert v1_cp_row["status"] == "pending_review"
        assert v1_cp_row["project_version_id"] == v1_id

    # Paso 7: Evaluar técnicamente v2 y verificar que pasa a evaluated
    service = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)
    req_v2 = service.request_evaluation(v2_id, PLANNER_USER_ID, f"req-v2-{uuid4()}")
    assert req_v2["status"] == "queued"
    assert req_v2["checkpoint"] is None

    processor = CompletionProcessor(db_url=db_url)
    completion_payload = {
        "event_id": str(uuid4()),
        "evaluation_id": str(req_v2["evaluation_id"]),
        "economic_assessment_id": str(uuid4()),
        "cost_per_beneficiary_pen": "260.00",
        "score_0_100": "90.00",
        "explanation": "Evaluación económica favorable para v2",
        "algorithm_version": "v1.0",
    }
    processor.process(completion_payload)

    v2_state = service.get_project(project_id)
    assert v2_state["status"] == "evaluated"
    assert v2_state["checkpoint"] is None

    # Paso 8: El gerente emite aprobación formal sobre la versión 2 completada -> debe ser exitosa
    approval_resp = api_client.post(
        f"/api/v1/projects/{project_id}/approval",
        json={
            "decision": "approved",
            "justification": "Proyecto v2 cumple con retiro reglamentario y evaluación técnica favorable",
            "conditions": None,
        },
        headers={**headers_mgr, "Idempotency-Key": f"appr-v2-{uuid4()}"},
    )
    assert approval_resp.status_code == 200
    approval_data = approval_resp.json()
    assert approval_data["decision"] == "approved"
    assert approval_data["project_version_id"] == str(v2_id)

    # Paso 9: Comprobar que para un expediente que sí tiene punto de control activo (como PRY-C), la compuerta de aprobación lo bloquea
    with pytest.raises(ConfiguracionPMV1Error, match="Pendiente de revisión"):
        service.submit_human_approval(
            project_id=PROJECT_C_ID,
            actor_id=ADMIN_USER_ID,
            decision="approved",
            justification="Intento ilegal de aprobar expediente con revisión pendiente",
            conditions=None,
            idempotency_key=f"illegal-appr-{uuid4()}",
        )

    # También por API: el intento de aprobar un proyecto pausado es rechazado con 400
    api_paused_resp = api_client.post(
        f"/api/v1/projects/{PROJECT_C_ID}/approval",
        json={
            "decision": "approved",
            "justification": "Intento de saltarse la pausa de riesgo alto",
            "conditions": None,
        },
        headers={**headers_mgr, "Idempotency-Key": f"api-illegal-appr-{uuid4()}"},
    )
    assert api_paused_resp.status_code == 409
    assert "Pendiente de revisión" in api_paused_resp.json()["detail"]


def test_checkpoint_incomplete_data_handling():
    """Verifica que cuando falten datos en el punto de control (causa vacía, observación ausente),
    el sistema lo indique con claridad sin inventar explicaciones y conserve el estado pendiente."""
    db_url = get_test_db_url()
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-INC-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Incompleto', 'Expediente con checkpoint sin observación',
                    'Sector El Tambo', 'recreacion', 80000.0, 300, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        # Checkpoint con reason vacío y details vacío (sin cause ni observation)
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    '   ', 'environmental', 'high', '{}'::jsonb, now(), now())""",
            (uuid4(), project_id, v1_id),
        )

        cp = RiskCheckpointEngine.get_active_checkpoint(conn, v1_id)
        assert cp is not None
        assert cp["status"] == "pending_review"
        assert cp["status_label"] == "Pendiente de revisión"

        # CA-HU3.2: Si falta la causa o la observación, no inventar explicaciones
        assert cp["cause"] is None
        assert cp["observation"] == "Observación pendiente de aclaración"
        assert "Información incompleta" in cp["reason"]
        assert cp["requires_human_review"] is True
        assert cp["allows_final_approval"] is False



def test_case_1_v1_paused_and_v2_mitigated_queries_are_strictly_read_only(api_client: TestClient):
    """Caso 1: Versión 1 pausada y Versión 2 mitigada.
    Múltiples consultas GET devuelven el estado efectivo de v2 sin aviso de pausa y
    dejan projects.status, updated_at y el checkpoint histórico de v1 estrictamente sin cambios."""
    db_url = get_test_db_url()
    headers_mgr = {"Authorization": "Bearer token-gerente-admin"}
    project_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-RO1-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id, created_at, updated_at)
            VALUES (%s, %s, 'pending_review', %s, '2026-11-01 10:00:00+00', '2026-11-01 10:00:00+00')""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id, created_at)
            VALUES (%s, %s, 1, 'Puente V1 Riesgoso', 'Trazo original en faja marginal',
                    'Cauce Shullcas', 'equipamiento', 150000.0, 500, %s, '2026-11-01 10:00:00+00')""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        v1_cp_id = uuid4()
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    'Causa técnica v1: Proximidad de 20m a cauce', 'environmental', 'high',
                    '{"cause": "Causa técnica v1: Proximidad de 20m a cauce", "observation": "Verificar faja marginal"}'::jsonb,
                    '2026-11-01 10:05:00+00', '2026-11-01 10:05:00+00')""",
            (v1_cp_id, project_id, v1_id),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id, created_at)
            VALUES (%s, %s, 2, 'Puente V2 Mitigado', 'Trazo retirado a 80m de la ribera',
                    'Zona alta El Tambo', 'equipamiento', 160000.0, 550, %s, '2026-11-02 12:00:00+00')""",
            (v2_id, project_id, ADMIN_USER_ID),
        )

        # Snapshot inicial en base de datos
        p_before = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
        cp_before = conn.execute("SELECT status, updated_at FROM evaluation_checkpoints WHERE id = %s", (v1_cp_id,)).fetchone()
        eval_count_before = conn.execute("SELECT COUNT(*) AS total FROM evaluations").fetchone()["total"]
        checkpoint_count_before = conn.execute("SELECT COUNT(*) AS total FROM evaluation_checkpoints").fetchone()["total"]
        audit_count_before = conn.execute("SELECT COUNT(*) AS total FROM audit_events").fetchone()["total"]

    service = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)

    # Ejecutar múltiples consultas de lectura vía servicio y API
    for _ in range(3):
        # 1. Consulta directa al servicio
        proj = service.get_project(project_id)
        assert proj["version_number"] == 2
        assert proj["project_version_id"] == v2_id
        assert proj["status"] == "ready"  # Estado efectivo calculado en memoria
        assert proj["checkpoint"] is None  # Sin aviso de pausa para v2

        # 2. Consulta al endpoint de checkpoint
        cp_val = service.get_project_checkpoint(project_id)
        assert cp_val is None

        # 3. Consulta vía API GET /projects/{id}
        resp = api_client.get(f"/api/v1/projects/{project_id}", headers=headers_mgr)
        assert resp.status_code == 200
        data = resp.json()
        assert data["version_number"] == 2
        assert data["status"] == "ready"
        assert data["checkpoint"] is None

        # 4. Consulta vía API GET /projects/{id}/checkpoint
        cp_resp = api_client.get(f"/api/v1/projects/{project_id}/checkpoint", headers=headers_mgr)
        assert cp_resp.status_code == 200
        assert cp_resp.json() is None

        # 5. Consulta vía API GET /projects/{id}/approval
        appr_resp = api_client.get(f"/api/v1/projects/{project_id}/approval", headers={"Authorization": "Bearer token-planner"})
        assert appr_resp.status_code == 200
        assert appr_resp.json()["is_paused"] is False

    # Verificar que la base de datos permaneció 100% INTACTA
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        p_after = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
        cp_after = conn.execute("SELECT status, updated_at FROM evaluation_checkpoints WHERE id = %s", (v1_cp_id,)).fetchone()
        eval_count_after = conn.execute("SELECT COUNT(*) AS total FROM evaluations").fetchone()["total"]
        checkpoint_count_after = conn.execute("SELECT COUNT(*) AS total FROM evaluation_checkpoints").fetchone()["total"]
        audit_count_after = conn.execute("SELECT COUNT(*) AS total FROM audit_events").fetchone()["total"]

    # projects.status en base de datos NO fue sobreescrito por el GET
    assert p_after["status"] == p_before["status"] == "pending_review"
    assert p_after["updated_at"] == p_before["updated_at"]

    # Checkpoint histórico de v1 permanece idéntico
    assert cp_after["status"] == cp_before["status"] == "pending_review"
    assert cp_after["updated_at"] == cp_before["updated_at"]

    # Cero inserciones secundarias
    assert eval_count_after == eval_count_before
    assert checkpoint_count_after == checkpoint_count_before
    assert audit_count_after == audit_count_before


def test_case_2_current_version_really_paused_queries_are_strictly_read_only(api_client: TestClient):
    """Caso 2: Versión vigente realmente pausada.
    Múltiples consultas GET conservan el aviso y el estado 'pending_review' sin mutar la BD."""
    db_url = get_test_db_url()
    headers_mgr = {"Authorization": "Bearer token-gerente-admin"}
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-RO2-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id, created_at, updated_at)
            VALUES (%s, %s, 'pending_review', %s, '2026-11-03 08:00:00+00', '2026-11-03 08:00:00+00')""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id, created_at)
            VALUES (%s, %s, 1, 'Hospital de Campaña V1', 'Emplazamiento en zona de alto riesgo',
                    'Quebrada Shullcas', 'salud', 220000.0, 900, %s, '2026-11-03 08:00:00+00')""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        cp_id = uuid4()
        causa = "Causa técnica de pausa: Inundabilidad alta detectada por CENEPRED"
        observacion = "Comprobación técnica requerida: Inspección presencial y certificación de drenaje"
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    %s, 'environmental', 'high',
                    %s::jsonb, '2026-11-03 08:15:00+00', '2026-11-03 08:15:00+00')""",
            (
                cp_id, project_id, v1_id, causa,
                f'{{"cause": "{causa}", "observation": "{observacion}"}}',
            ),
        )

        p_before = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
        cp_before = conn.execute("SELECT * FROM evaluation_checkpoints WHERE id = %s", (cp_id,)).fetchone()

    service = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)

    for _ in range(3):
        proj = service.get_project(project_id)
        assert proj["status"] == "pending_review"
        assert proj["checkpoint"] is not None
        assert proj["checkpoint"]["cause"] == causa
        assert proj["checkpoint"]["observation"] == observacion

        resp = api_client.get(f"/api/v1/projects/{project_id}", headers=headers_mgr)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_review"
        assert data["checkpoint"]["cause"] == causa

        cp_resp = api_client.get(f"/api/v1/projects/{project_id}/checkpoint", headers=headers_mgr)
        assert cp_resp.status_code == 200
        assert cp_resp.json()["cause"] == causa

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        p_after = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
        cp_after = conn.execute("SELECT * FROM evaluation_checkpoints WHERE id = %s", (cp_id,)).fetchone()

    assert p_after["status"] == p_before["status"] == "pending_review"
    assert p_after["updated_at"] == p_before["updated_at"]
    assert cp_after["updated_at"] == cp_before["updated_at"]


def test_case_3_inconsistent_pending_review_without_checkpoint_is_controlled_and_blocks_approval(api_client: TestClient):
    """Caso 3: Estado pending_review sin checkpoint de la versión vigente por datos inconsistentes.
    El sistema NO convierte automáticamente el proyecto a 'ready' ni habilita aprobación sin revisión;
    informa la inconsistencia de forma controlada y la compuerta de aprobación lo bloquea."""
    db_url = get_test_db_url()
    headers_mgr = {"Authorization": "Bearer token-gerente-admin"}
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-INC3-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # Proyecto en pending_review pero CERO checkpoints en evaluation_checkpoints
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id, created_at, updated_at)
            VALUES (%s, %s, 'pending_review', %s, '2026-11-04 09:00:00+00', '2026-11-04 09:00:00+00')""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id, created_at)
            VALUES (%s, %s, 1, 'Proyecto Huérfano de Checkpoint', 'Expediente con estado inconsistente',
                    'Sector Centro', 'comercial', 130000.0, 300, %s, '2026-11-04 09:00:00+00')""",
            (v1_id, project_id, ADMIN_USER_ID),
        )

        p_before = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()

    service = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)

    # 1. Consultar el proyecto por servicio: NO debe convertirse a 'ready'
    proj = service.get_project(project_id)
    assert proj["status"] == "pending_review"  # Se conserva estrictamente pending_review
    assert proj["checkpoint"] is not None  # Retorna el objeto de control de inconsistencia
    assert "Inconsistencia de control" in proj["checkpoint"]["reason"]
    assert proj["checkpoint"]["requires_human_review"] is True
    assert proj["checkpoint"]["allows_final_approval"] is False

    # 2. Consultar vía API GET /projects/{id}
    api_resp = api_client.get(f"/api/v1/projects/{project_id}", headers=headers_mgr)
    assert api_resp.status_code == 200
    api_data = api_resp.json()
    assert api_data["status"] == "pending_review"
    assert "Inconsistencia de control" in api_data["checkpoint"]["reason"]

    # 3. Consultar vía API GET /projects/{id}/checkpoint
    cp_resp = api_client.get(f"/api/v1/projects/{project_id}/checkpoint", headers=headers_mgr)
    assert cp_resp.status_code == 200
    cp_data = cp_resp.json()
    assert cp_data["status"] == "pending_review"
    assert "Inconsistencia de control" in cp_data["reason"]

    # 4. Consultar la compuerta de aprobación: debe estar pausada y NO habilitada
    appr_status = service.get_human_approval(project_id)
    assert appr_status["is_paused"] is True
    assert appr_status["is_evaluated"] is False
    assert appr_status["requires_human_approval"] is False

    appr_resp = api_client.get(f"/api/v1/projects/{project_id}/approval", headers={"Authorization": "Bearer token-planner"})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["is_paused"] is True
    assert appr_resp.json()["requires_human_approval"] is False

    # 5. Intento de emitir aprobación formal por servicio: debe ser RECHAZADO
    with pytest.raises(ConfiguracionPMV1Error, match="Pendiente de revisión"):
        service.submit_human_approval(
            project_id=project_id,
            actor_id=ADMIN_USER_ID,
            decision="approved",
            justification="Intento ilegal de aprobar expediente en inconsistencia",
            conditions=None,
            idempotency_key=f"illegal-inc-{uuid4()}",
        )

    # 6. Intento de emitir aprobación por API: debe devolver 409 Conflict
    api_appr_resp = api_client.post(
        f"/api/v1/projects/{project_id}/approval",
        json={
            "decision": "approved",
            "justification": "Intento de saltarse la revisión de expediente inconsistente",
            "conditions": None,
        },
        headers={**headers_mgr, "Idempotency-Key": f"api-illegal-inc-{uuid4()}"},
    )
    assert api_appr_resp.status_code == 409
    assert "Pendiente de revisión" in api_appr_resp.json()["detail"]

    # 7. La base de datos permaneció 100% de solo lectura
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        p_after = conn.execute("SELECT status, updated_at FROM projects WHERE id = %s", (project_id,)).fetchone()
        assert p_after["status"] == p_before["status"] == "pending_review"
        assert p_after["updated_at"] == p_before["updated_at"]


def test_create_project_version_write_operation_updates_stored_status():
    """Verifica que la creación de una nueva versión (v2) como operación de escritura
    actualiza el estado almacenado en projects a 'ready' de forma explícita."""
    db_url = get_test_db_url()
    project_id = uuid4()
    v1_id = uuid4()
    code = f"PRY-WR1-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Obra v1', 'Versión inicial pausada',
                    'Ribera', 'salud', 100000.0, 400, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    'Pausa v1', 'environmental', 'high', '{}'::jsonb, now(), now())""",
            (uuid4(), project_id, v1_id),
        )

    service = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)

    # Operación de escritura explícita: crear versión 2
    v2_proj = service.create_project_version(
        project_id=project_id,
        title="Obra v2 Mitigada",
        description="Versión con mitigaciones",
        location_description="Zona segura",
        proposed_land_use="salud",
        estimated_budget_pen=110000.0,
        beneficiaries_count=450,
        actor_id=ADMIN_USER_ID,
    )
    assert v2_proj["version_number"] == 2
    assert v2_proj["status"] == "ready"

    # En la base de datos física, la tabla projects fue actualizada a 'ready' por la operación de escritura
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        p_row = conn.execute("SELECT status FROM projects WHERE id = %s", (project_id,)).fetchone()
        assert p_row["status"] == "ready"
