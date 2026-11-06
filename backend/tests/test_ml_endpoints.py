from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_metricas_modelos_ml(client: TestClient) -> None:
    response = client.get("/api/v1/ml/metricas-modelos")
    assert response.status_code == 200
    data = response.json()
    assert "modelo_1_sobrecosto" in data
    assert "modelo_2_viabilidad_plazo" in data
    assert data["modelo_1_sobrecosto"]["accuracy"] >= 0.85
    assert data["modelo_2_viabilidad_plazo"]["accuracy"] >= 0.70


def test_prediccion_sobrecosto_caso1(client: TestClient) -> None:
    payload = {
        "monto_inversion": 3_500_000.0,
        "beneficiarios": 12000,
        "plazo_dias_programado": 240,
        "tipo_proyecto": "Transporte y Vías Urbanas",
        "zona_intervencion": "Periurbana",
        "complejidad_tecnica": 3,
        "variacion_diseno_pct": 14.5,
    }
    response = client.post("/api/v1/ml/predecir-sobrecosto", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["nivel_riesgo"] in ["BAJO", "MEDIO", "ALTO"]
    assert 0.0 <= data["probabilidad"] <= 1.0
    assert len(data["factores_clave"]) > 0


def test_prediccion_retraso_caso2(client: TestClient) -> None:
    payload = {
        "monto_inversion": 450_000.0,
        "beneficiarios": 1500,
        "plazo_dias_programado": 90,
        "tipo_proyecto": "Espacio Público y Parques",
        "zona_intervencion": "Urbana consolidada",
        "complejidad_tecnica": 1,
        "variacion_diseno_pct": 2.0,
    }
    response = client.post("/api/v1/ml/predecir-retraso", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["clase_viabilidad"] in ["VIABLE", "RIESGO_MODERADO", "CRITICO"]
    assert data["retraso_estimado_dias"] >= 0
    assert len(data["alertas_programacion"]) > 0


def test_evaluar_proyecto_ml_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/ml/evaluar-proyecto/EXP-TEST-001")
    assert response.status_code == 200
    data = response.json()
    assert data["expediente_code"] == "EXP-TEST-001"
    assert "sobrecosto" in data
    assert "viabilidad_plazo" in data
    assert "resumen_ejecutivo" in data
