from __future__ import annotations

from uuid import uuid4
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.infrastructure.config.dependencies import get_current_user


def _build_client(roles: list[str]) -> TestClient:
    app = create_app()
    actor = uuid4()
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": str(actor),
        "roles": roles,
    }
    return TestClient(app)


def test_carga_masiva_750_transacciones_exitosa():
    client = _build_client(["PLANNER"])
    resp = client.post(
        "/api/v1/pruebas/data-masiva",
        json={"cantidad": 750, "incluir_ml": True, "incluir_pert": True, "seed": 42},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requested_count"] == 750
    assert body["processed_count"] == 750
    assert body["failed_count"] == 0
    assert body["success_rate_pct"] == 100.0
    assert body["elapsed_ms"] > 0
    assert body["throughput_tps"] > 0
    assert len(body["sample_records"]) == 15
    assert (
        body["distribution"]["alto_riesgo"]
        + body["distribution"]["riesgo_moderado"]
        + body["distribution"]["bajo_riesgo"]
        == 750
    )


def test_carga_masiva_rechaza_cantidad_fuera_de_rango():
    client = _build_client(["ADMIN"])
    resp = client.post(
        "/api/v1/pruebas/data-masiva",
        json={"cantidad": 10, "incluir_ml": True, "incluir_pert": True},
    )
    assert resp.status_code == 422


def test_metricas_sistema_retorna_benchmarks_ml_y_cobertura():
    client = _build_client(["LEGAL_ADVISOR"])
    resp = client.get("/api/v1/pruebas/metricas")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["performance_benchmarks"]) == 3
    for item in body["performance_benchmarks"]:
        assert item["iterations"] == 100
        assert item["avg_ms"] >= 0
        assert item["estimated_tps"] > 0

    ml_q = body["ml_quality_metrics"]
    assert ml_q["eligible_rows"] == 19654
    assert ml_q["cost_roc_auc"] > 0.5
    assert ml_q["duration_mae_improvement_days"] > 0

    cov = body["functional_coverage"]
    assert cov["total_pmv1_pmv2_stories"] == 18
    assert cov["total_pmv1_pmv2_criteria"] == 45


def test_pruebas_requieren_autenticacion():
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/pruebas/metricas").status_code == 401
        assert (
            client.post("/api/v1/pruebas/data-masiva", json={"cantidad": 500}).status_code
            == 401
        )
