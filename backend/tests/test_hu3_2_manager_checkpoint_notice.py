from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from backend.application.services.pmv1_services import (
    PlatformService,
    RiskCheckpointEngine,
)
from backend.domain.exceptions.pmv1_exceptions import CredencialesInvalidasError
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


def test_version_isolation_checkpoint_from_obsolete_version_not_active():
    """Garantiza que un punto de control registrado para la versión 1 de un proyecto
    no aparezca como activo en una versión 2 no pausada."""
    db_url = get_test_db_url()
    project_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    code = f"PRY-ISO-{uuid4().hex[:4].upper()}"

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, status, created_by_user_id)
            VALUES (%s, %s, 'pending_review', %s)""",
            (project_id, code, ADMIN_USER_ID),
        )
        # Versión 1: contiene riesgo alto y checkpoint
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Aislamiento V1', 'Version inicial en zona de riesgo',
                    'Faja marginal', 'equipamiento', 100000.0, 500, %s)""",
            (v1_id, project_id, ADMIN_USER_ID),
        )
        conn.execute(
            """INSERT INTO evaluation_checkpoints
            (id, project_id, project_version_id, checkpoint_type, status,
             reason, risk_source, risk_level, details, created_at, updated_at)
            VALUES (%s, %s, %s, 'high_risk_pause', 'pending_review',
                    'Riesgo crítico en versión 1', 'environmental', 'high',
                    '{"risk_observation": "Observación técnica v1", "cause": "Causa v1"}'::jsonb,
                    now(), now())""",
            (uuid4(), project_id, v1_id),
        )

        # Verificar que get_active_checkpoint en v1 encuentra el checkpoint
        cp_v1 = RiskCheckpointEngine.get_active_checkpoint(conn, v1_id)
        assert cp_v1 is not None
        assert cp_v1["project_version_id"] == v1_id
        assert cp_v1["status"] == "pending_review"

        # Versión 2: creada posteriormente sin riesgo alto
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 2, 'Proyecto Aislamiento V2', 'Version subsanada fuera de riesgo',
                    'Zona segura urbana', 'equipamiento', 110000.0, 550, %s)""",
            (v2_id, project_id, ADMIN_USER_ID),
        )

        # El punto de control de v1 NO debe ser recuperado para la versión 2
        cp_v2 = RiskCheckpointEngine.get_active_checkpoint(conn, v2_id)
        assert cp_v2 is None
        assert RiskCheckpointEngine.has_pending_checkpoint(conn, v2_id) is False

    # A través de PlatformService
    svc = PlatformService(db_url=db_url, dispatcher=None, enable_demo_fallback=False)
    proj_v2 = svc.get_project(project_id)
    assert proj_v2["version_number"] == 2
    # El checkpoint de la versión obsoleta no se asocia a la versión vigente
    assert proj_v2["checkpoint"] is None


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
        assert cp["observation"] is None
        assert "Información incompleta" in cp["reason"]
        assert cp["requires_human_review"] is True
        assert cp["allows_final_approval"] is False
