from decimal import Decimal
import math
from uuid import UUID, uuid4
import psycopg
from psycopg.rows import dict_row
import pytest

from backend.application.services.pmv1_services import (
    PertDurationEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import (
    VersionNoPertenecienteError,
    EstimacionPERTInvalidaError,
    RecursoPMV1NoEncontradoError,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
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


# 1. Ejemplo calculado a mano
def test_pert_formula_hand_calculated_example():
    """Ejemplo calculado a mano:
    a = 4.0 meses, m = 6.0 meses, b = 10.0 meses.
    μ = (4 + 4*6 + 10) / 6 = 38 / 6 = 6.333333... meses
    σ = (10 - 4) / 6 = 6 / 6 = 1.0 meses
    σ² = 1.0² = 1.0 meses²
    Intervalo referencial [5.3333, 7.3333] meses.
    """
    a, m, b, unit = PertDurationEngine.validate_inputs("4.0", "6.0", "10.0", "meses")
    res = PertDurationEngine.calculate(a, m, b, unit)

    assert res["time_unit"] == "meses"
    assert res["optimistic_duration"] == Decimal("4.0000")
    assert res["most_likely_duration"] == Decimal("6.0000")
    assert res["pessimistic_duration"] == Decimal("10.0000")
    assert float(res["expected_duration"]) == pytest.approx(38.0 / 6.0, abs=0.0001)
    assert float(res["standard_deviation"]) == pytest.approx(1.0, abs=0.0001)
    assert float(res["variance"]) == pytest.approx(1.0, abs=0.0001)
    assert float(res["confidence_interval_low"]) == pytest.approx(6.3333 - 1.0, abs=0.001)
    assert float(res["confidence_interval_high"]) == pytest.approx(6.3333 + 1.0, abs=0.001)
    assert "compromiso contractual ni plazo garantizado" in res["disclaimer"]
    assert "μ = (a + 4m + b) / 6" in res["formula_applied"]


# 2. Límites a=m=b y a=0
def test_pert_boundary_identical_values_zero_variance():
    """Límite a = m = b = 8.0:
    μ = (8 + 32 + 8) / 6 = 8.0
    σ = (8 - 8) / 6 = 0.0
    σ² = 0.0
    Intervalo [8.0, 8.0]
    """
    a, m, b, unit = PertDurationEngine.validate_inputs(8, 8, 8, "meses")
    res = PertDurationEngine.calculate(a, m, b, unit)
    assert res["expected_duration"] == Decimal("8.0000")
    assert res["standard_deviation"] == Decimal("0.0000")
    assert res["variance"] == Decimal("0.0000")
    assert res["confidence_interval_low"] == Decimal("8.0000")
    assert res["confidence_interval_high"] == Decimal("8.0000")


def test_pert_boundary_a_zero():
    """Límite a = 0:
    a = 0, m = 3.0, b = 12.0
    μ = (0 + 12 + 12) / 6 = 4.0
    σ = (12 - 0) / 6 = 2.0
    σ² = 4.0
    """
    a, m, b, unit = PertDurationEngine.validate_inputs(0, 3, 12, "meses")
    res = PertDurationEngine.calculate(a, m, b, unit)
    assert res["expected_duration"] == Decimal("4.0000")
    assert res["standard_deviation"] == Decimal("2.0000")
    assert res["variance"] == Decimal("4.0000")


# 3. Decimales
def test_pert_decimals_precision():
    """Prueba con decimales: a = 2.5, m = 4.75, b = 8.2:
    μ = (2.5 + 4*4.75 + 8.2) / 6 = 29.7 / 6 = 4.95
    σ = (8.2 - 2.5) / 6 = 5.7 / 6 = 0.95
    σ² = 0.95² = 0.9025
    """
    a, m, b, unit = PertDurationEngine.validate_inputs("2.5", "4.75", "8.2", "meses")
    res = PertDurationEngine.calculate(a, m, b, unit)
    assert float(res["expected_duration"]) == pytest.approx(4.95, abs=0.0001)
    assert float(res["standard_deviation"]) == pytest.approx(0.95, abs=0.0001)
    assert float(res["variance"]) == pytest.approx(0.9025, abs=0.0001)


# 4. Datos faltantes o inválidos
def test_pert_missing_values_raise_error():
    with pytest.raises(EstimacionPERTInvalidaError) as exc1:
        PertDurationEngine.validate_inputs(None, 5, 8)
    assert exc1.value.campo == "optimistic_duration"
    assert "optimista" in str(exc1.value)

    with pytest.raises(EstimacionPERTInvalidaError) as exc2:
        PertDurationEngine.validate_inputs(3, None, 8)
    assert exc2.value.campo == "most_likely_duration"
    assert "más probable" in str(exc2.value)

    with pytest.raises(EstimacionPERTInvalidaError) as exc3:
        PertDurationEngine.validate_inputs(3, 5, None)
    assert exc3.value.campo == "pessimistic_duration"
    assert "pesimista" in str(exc3.value)


def test_pert_non_finite_values_raise_error():
    with pytest.raises(EstimacionPERTInvalidaError) as exc_nan:
        PertDurationEngine.validate_inputs(float("nan"), 5, 8)
    assert exc_nan.value.campo == "optimistic_duration"
    assert "número finito" in str(exc_nan.value)

    with pytest.raises(EstimacionPERTInvalidaError) as exc_inf:
        PertDurationEngine.validate_inputs(3, float("inf"), 8)
    assert exc_inf.value.campo == "most_likely_duration"
    assert "número finito" in str(exc_inf.value)


# 5. Valores negativos
def test_pert_negative_values_raise_error():
    with pytest.raises(EstimacionPERTInvalidaError) as exc_neg:
        PertDurationEngine.validate_inputs(-1, 5, 8)
    assert exc_neg.value.campo == "optimistic_duration"
    assert "no puede ser negativa" in str(exc_neg.value)

    with pytest.raises(EstimacionPERTInvalidaError) as exc_neg_m:
        PertDurationEngine.validate_inputs(2, -3, 8)
    assert exc_neg_m.value.campo == "most_likely_duration"
    assert "no puede ser negativa" in str(exc_neg_m.value)

    with pytest.raises(EstimacionPERTInvalidaError) as exc_neg_b:
        PertDurationEngine.validate_inputs(2, 4, -5)
    assert exc_neg_b.value.campo == "pessimistic_duration"
    assert "no puede ser negativa" in str(exc_neg_b.value)


# 6. Orden incorrecto
def test_pert_incorrect_order_raise_error():
    # a > m
    with pytest.raises(EstimacionPERTInvalidaError) as exc_am:
        PertDurationEngine.validate_inputs(6, 4, 10)
    assert exc_am.value.campo == "optimistic_duration"
    assert "no puede ser mayor que la duración más probable" in str(exc_am.value)

    # m > b
    with pytest.raises(EstimacionPERTInvalidaError) as exc_mb:
        PertDurationEngine.validate_inputs(4, 12, 10)
    assert exc_mb.value.campo == "most_likely_duration"
    assert "no puede ser mayor que la duración pesimista" in str(exc_mb.value)

    # a > b
    with pytest.raises(EstimacionPERTInvalidaError) as exc_ab:
        PertDurationEngine.validate_inputs(11, 11, 10)
    assert "no puede ser mayor que la duración" in str(exc_ab.value)


# 7. Persistencia en Base de Datos Real
def test_pert_persistence_and_retrieval():
    service = get_test_platform_service()
    project = service.get_project(PROJECT_B_ID)
    v_id = project["project_version_id"]

    registered = service.register_pert_estimate(
        project_id=PROJECT_B_ID,
        actor_id=PLANNER_ID,
        data={
            "optimistic_duration": "5.0",
            "most_likely_duration": "7.5",
            "pessimistic_duration": "12.0",
            "time_unit": "meses",
        },
    )
    assert registered["id"] is not None
    assert registered["project_id"] == PROJECT_B_ID
    assert registered["project_version_id"] == v_id
    assert float(registered["expected_duration"]) == pytest.approx((5.0 + 4 * 7.5 + 12.0) / 6.0, abs=0.001)
    assert float(registered["standard_deviation"]) == pytest.approx((12.0 - 5.0) / 6.0, abs=0.001)

    # Recuperar directamente
    fetched = service.get_pert_estimate(PROJECT_B_ID)
    assert fetched is not None
    assert fetched["id"] == registered["id"]
    assert float(fetched["expected_duration"]) == pytest.approx((5.0 + 4 * 7.5 + 12.0) / 6.0, abs=0.001)

    # Recuperar a través de get_project
    proj_updated = service.get_project(PROJECT_B_ID)
    assert proj_updated["pert_estimate"] is not None
    assert proj_updated["pert_estimate"]["id"] == registered["id"]


# 8. Aislamiento por Versión
def test_pert_version_isolation():
    db_url = get_test_db_url()
    service = get_test_platform_service()
    test_proj_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO projects (id, code, created_by_user_id, status)
            VALUES (%s, %s, %s, 'ready')""",
            (test_proj_id, f"PRY-PERT-ISO-{uuid4().hex[:6]}", PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto Versión 1', 'Prueba PERT v1', 'El Tambo', 'recreacion', 100000, 500, %s)""",
            (v1_id, test_proj_id, PLANNER_ID),
        )

    # Registrar estimación para v1: a=3, m=6, b=9 -> μ=6
    reg_v1 = service.register_pert_estimate(
        project_id=test_proj_id,
        actor_id=PLANNER_ID,
        data={
            "project_version_id": v1_id,
            "optimistic_duration": "3.0",
            "most_likely_duration": "6.0",
            "pessimistic_duration": "9.0",
            "time_unit": "meses",
        },
    )
    assert float(reg_v1["expected_duration"]) == 6.0

    # Crear versión 2
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 2, 'Proyecto Versión 2', 'Prueba PERT v2', 'El Tambo', 'recreacion', 120000, 600, %s)""",
            (v2_id, test_proj_id, PLANNER_ID),
        )

    # Versión 2 al inicio NO tiene estimación PERT (no hereda de v1)
    pert_v2 = service.get_pert_estimate(test_proj_id, project_version_id=v2_id)
    assert pert_v2 is None

    # Registrar estimación para v2 con otros datos: a=5, m=10, b=15 -> μ=10
    reg_v2 = service.register_pert_estimate(
        project_id=test_proj_id,
        actor_id=PLANNER_ID,
        data={
            "project_version_id": v2_id,
            "optimistic_duration": "5.0",
            "most_likely_duration": "10.0",
            "pessimistic_duration": "15.0",
            "time_unit": "meses",
        },
    )
    assert float(reg_v2["expected_duration"]) == 10.0

    # Verificar que v1 permanece intacta en μ=6 y v2 en μ=10
    v1_check = service.get_pert_estimate(test_proj_id, project_version_id=v1_id)
    assert v1_check is not None
    assert float(v1_check["expected_duration"]) == 6.0

    v2_check = service.get_pert_estimate(test_proj_id, project_version_id=v2_id)
    assert v2_check is not None
    assert float(v2_check["expected_duration"]) == 10.0


# 9. Que un error no devuelva un resultado válido anterior
def test_pert_invalid_submission_does_not_return_valid_previous():
    service = get_test_platform_service()
    # Intento de registrar con orden inválido en un proyecto existente
    with pytest.raises(EstimacionPERTInvalidaError):
        service.register_pert_estimate(
            project_id=PROJECT_A_ID,
            actor_id=PLANNER_ID,
            data={
                "optimistic_duration": "12.0",
                "most_likely_duration": "6.0",
                "pessimistic_duration": "8.0",
                "time_unit": "meses",
            },
        )

# 10. Rechazo estricto de versión ajena sin mutar ninguno de los expedientes
def test_pert_alien_version_rejected_without_modifications():
    """Comprueba que pasar un project_version_id que pertenece a otro proyecto
    es rechazado con VersionNoPertenecienteError, y ninguna tabla/estimación de
    ninguno de los dos proyectos es insertada ni modificada."""
    db_url = get_test_db_url()
    service = get_test_platform_service()

    proj1_id = uuid4()
    v1_id = uuid4()
    proj2_id = uuid4()
    v2_id = uuid4()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # Proyecto 1 y versión 1
        conn.execute(
            """INSERT INTO projects (id, code, created_by_user_id, status)
            VALUES (%s, %s, %s, 'ready')""",
            (proj1_id, f"PRY-P1-{uuid4().hex[:6]}", PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto 1 v1', 'Desc 1', 'El Tambo', 'recreacion', 100000, 500, %s)""",
            (v1_id, proj1_id, PLANNER_ID),
        )

        # Proyecto 2 y versión 2
        conn.execute(
            """INSERT INTO projects (id, code, created_by_user_id, status)
            VALUES (%s, %s, %s, 'ready')""",
            (proj2_id, f"PRY-P2-{uuid4().hex[:6]}", PLANNER_ID),
        )
        conn.execute(
            """INSERT INTO project_versions (id, project_id, version_number, title,
            description, location_description, proposed_land_use, estimated_budget_pen,
            beneficiaries_count, created_by_user_id)
            VALUES (%s, %s, 1, 'Proyecto 2 v2', 'Desc 2', 'El Tambo', 'recreacion', 200000, 800, %s)""",
            (v2_id, proj2_id, PLANNER_ID),
        )

    # Registrar estimación legítima en Proyecto 1: a=4, m=6, b=10 (μ=6.3333)
    reg_p1 = service.register_pert_estimate(
        project_id=proj1_id,
        actor_id=PLANNER_ID,
        data={
            "project_version_id": v1_id,
            "optimistic_duration": "4.0",
            "most_likely_duration": "6.0",
            "pessimistic_duration": "10.0",
            "time_unit": "meses",
        },
    )
    assert float(reg_p1["expected_duration"]) == pytest.approx(6.3333, abs=0.001)

    # Registrar estimación legítima en Proyecto 2: a=5, m=10, b=15 (μ=10.0)
    reg_p2 = service.register_pert_estimate(
        project_id=proj2_id,
        actor_id=PLANNER_ID,
        data={
            "project_version_id": v2_id,
            "optimistic_duration": "5.0",
            "most_likely_duration": "10.0",
            "pessimistic_duration": "15.0",
            "time_unit": "meses",
        },
    )
    assert float(reg_p2["expected_duration"]) == 10.0

    # INTENTO FRAUDULENTO: Registrar en Proyecto 1 pero pasando la versión 2 (de Proyecto 2)
    with pytest.raises(VersionNoPertenecienteError) as exc_info:
        service.register_pert_estimate(
            project_id=proj1_id,
            actor_id=PLANNER_ID,
            data={
                "project_version_id": v2_id,  # Pertenece a Proyecto 2!
                "optimistic_duration": "1.0",
                "most_likely_duration": "2.0",
                "pessimistic_duration": "3.0",
                "time_unit": "meses",
            },
        )
    assert str(v2_id) in str(exc_info.value)
    assert str(proj1_id) in str(exc_info.value)

    # COMPROBAR AUSENCIA DE CAMBIOS:
    # 1. Proyecto 1 sigue teniendo exactamente su estimación v1 intacta
    check_p1 = service.get_pert_estimate(proj1_id, project_version_id=v1_id)
    assert check_p1 is not None
    assert float(check_p1["expected_duration"]) == pytest.approx(6.3333, abs=0.001)
    assert float(check_p1["optimistic_duration"]) == 4.0

    # 2. Proyecto 2 sigue teniendo exactamente su estimación v2 intacta (no fue sobreescrita ni alterada)
    check_p2 = service.get_pert_estimate(proj2_id, project_version_id=v2_id)
    assert check_p2 is not None
    assert float(check_p2["expected_duration"]) == 10.0
    assert float(check_p2["optimistic_duration"]) == 5.0

    # 3. No existe ninguna estimación huérfana o cruzada en la base de datos
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """SELECT project_id, project_version_id, expected_duration
            FROM project_pert_estimates
            WHERE project_id IN (%s, %s)""",
            (proj1_id, proj2_id),
        ).fetchall()
        assert len(rows) == 2
        for r in rows:
            if r["project_id"] == proj1_id:
                assert r["project_version_id"] == v1_id
            elif r["project_id"] == proj2_id:
                assert r["project_version_id"] == v2_id


# 11. get_pert_estimate con versión ajena es rechazado
def test_pert_get_alien_version_rejected():
    service = get_test_platform_service()
    alien_version = uuid4()
    with pytest.raises(VersionNoPertenecienteError) as exc_info:
        service.get_pert_estimate(PROJECT_A_ID, project_version_id=alien_version)
    assert str(alien_version) in str(exc_info.value)
