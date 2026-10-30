# backend/tests/test_social_accessibility_service.py
from datetime import datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.errors import CheckViolation

from backend.application.services.pmv1_services import (
    PlatformService,
    SocialAccessibilityEngine,
)
from backend.domain.exceptions.pmv1_exceptions import ConfiguracionPMV1Error
from backend.infrastructure.config.settings import get_settings


PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


def test_social_accessibility_engine_complete():
    """CA-HU1.4-01: Evaluación con datos completos para salud, educación y transporte."""
    sample_rows = [
        {
            "category": "salud",
            "indicator_name": "Distancia al centro de salud",
            "metric_value": 450.0,
            "metric_unit": "metros",
            "has_sufficient_data": True,
            "source_name": "RENAES MINSA (Simulado)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Centro a 450m",
        },
        {
            "category": "educacion",
            "indicator_name": "Distancia a colegio público",
            "metric_value": 320.0,
            "metric_unit": "metros",
            "has_sufficient_data": True,
            "source_name": "Censo Educativo MINEDU (Simulado)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Colegio a 320m",
        },
        {
            "category": "transporte",
            "indicator_name": "Tiempo al paradero",
            "metric_value": 6.0,
            "metric_unit": "minutos",
            "has_sufficient_data": True,
            "source_name": "Sistema Vial Metropolitano (Simulado)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Paradero a 6 min",
        },
    ]

    result = SocialAccessibilityEngine.evaluate(
        project_id=PROJECT_A_ID,
        project_code="PRY-A",
        project_version_id=uuid4(),
        indicator_rows=sample_rows,
    )

    assert result["status"] == "complete"
    assert len(result["categories"]) == 3

    categories = {c["category"]: c for c in result["categories"]}
    assert set(categories.keys()) == {"salud", "educacion", "transporte"}

    # Salud
    salud = categories["salud"]
    assert salud["status"] == "sufficient"
    assert salud["has_sufficient_data"] is True
    assert salud["value"] == 450.0
    assert salud["unit"] == "metros"
    assert "RENAES" in salud["source"]
    assert salud["is_simulated"] is True

    # Educación
    educacion = categories["educacion"]
    assert educacion["status"] == "sufficient"
    assert educacion["has_sufficient_data"] is True
    assert educacion["value"] == 320.0
    assert educacion["unit"] == "metros"
    assert "MINEDU" in educacion["source"]

    # Transporte
    transporte = categories["transporte"]
    assert transporte["status"] == "sufficient"
    assert transporte["has_sufficient_data"] is True
    assert transporte["value"] == 6.0
    assert transporte["unit"] == "minutos"


def test_social_accessibility_engine_insufficient_no_invented_numbers():
    """CA-HU1.4-02: Información insuficiente sin distancias ni números inventados."""
    sample_rows = [
        {
            "category": "salud",
            "indicator_name": "Distancia al centro de salud",
            "metric_value": 680.0,
            "metric_unit": "metros",
            "has_sufficient_data": True,
            "source_name": "RENAES MINSA (Simulado)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Centro a 680m",
        },
        {
            "category": "educacion",
            "indicator_name": "Distancia a colegio público",
            "metric_value": None,
            "metric_unit": None,
            "has_sufficient_data": False,
            "source_name": "Catastro Municipal (Sin cobertura de padrón escolar)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Información insuficiente",
        },
        {
            "category": "transporte",
            "indicator_name": "Tiempo al paradero",
            "metric_value": None,
            "metric_unit": None,
            "has_sufficient_data": False,
            "source_name": "Catastro Municipal (Sin cobertura de rutas autorizadas)",
            "data_origin": "simulated",
            "is_simulated": True,
            "description": "Información insuficiente",
        },
    ]

    result = SocialAccessibilityEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        indicator_rows=sample_rows,
    )

    assert result["status"] == "partial"
    assert len(result["categories"]) == 3

    categories = {c["category"]: c for c in result["categories"]}

    # Educación: Información insuficiente
    educacion = categories["educacion"]
    assert educacion["status"] == "insufficient"
    assert educacion["has_sufficient_data"] is False
    assert educacion["message"] == "Información insuficiente"
    assert educacion["value"] is None  # NINGÚN NÚMERO INVENTADO
    assert educacion["unit"] is None   # NINGUNA UNIDAD INVENTADA
    assert educacion["source"] != ""

    # Transporte: Información insuficiente
    transporte = categories["transporte"]
    assert transporte["status"] == "insufficient"
    assert transporte["has_sufficient_data"] is False
    assert transporte["message"] == "Información insuficiente"
    assert transporte["value"] is None  # NINGÚN NÚMERO INVENTADO
    assert transporte["unit"] is None   # NINGUNA UNIDAD INVENTADA
    assert transporte["source"] != ""


def test_social_accessibility_engine_missing_all():
    """Si no hay ningún indicador registrado, todas las categorías muestran 'Información insuficiente'."""
    result = SocialAccessibilityEngine.evaluate(
        project_id=uuid4(),
        project_code="EXP-EMPTY",
        project_version_id=None,
        indicator_rows=[],
    )

    assert result["status"] == "insufficient"
    assert len(result["categories"]) == 3
    for cat in result["categories"]:
        assert cat["status"] == "insufficient"
        assert cat["has_sufficient_data"] is False
        assert cat["message"] == "Información insuficiente"
        assert cat["value"] is None
        assert cat["unit"] is None


def test_db_check_constraint_prevents_invented_values():
    """Comprueba que la base de datos rechace filas con has_sufficient_data=FALSE pero con valores numéricos."""
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(db_url) as conn:
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO territorial_social_indicators
                    (id, project_id, project_code, category, indicator_name, metric_value, metric_unit, has_sufficient_data, source_name)
                    VALUES (%s, %s, 'PRY-TEST', 'salud', 'Indicador invalido', 150.0, 'metros', FALSE, 'Fuente de prueba')
                    """,
                    (uuid4(), PROJECT_A_ID),
                )


def test_platform_service_evaluate_and_get():
    """Verifica la ejecución de evaluate_social_accessibility y get_social_accessibility en base de datos."""
    settings = get_settings()
    service = PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )

    # 1. Caso completo: PRY-A
    res_a = service.evaluate_social_accessibility(
        project_id=PROJECT_A_ID,
        actor_id=PLANNER_ID,
        idempotency_key=f"test-eval-pry-a-{uuid4().hex[:8]}",
    )
    assert res_a["status"] == "complete"
    assert len(res_a["categories"]) == 3
    assert all(c["has_sufficient_data"] for c in res_a["categories"])

    # 2. Caso incompleto: PRY-B
    res_b = service.evaluate_social_accessibility(
        project_id=PROJECT_B_ID,
        actor_id=PLANNER_ID,
        idempotency_key=f"test-eval-pry-b-{uuid4().hex[:8]}",
    )
    assert res_b["status"] == "partial"
    cats_b = {c["category"]: c for c in res_b["categories"]}
    assert cats_b["salud"]["has_sufficient_data"] is True
    assert cats_b["educacion"]["has_sufficient_data"] is False
    assert cats_b["educacion"]["message"] == "Información insuficiente"
    assert cats_b["educacion"]["value"] is None
    assert cats_b["transporte"]["has_sufficient_data"] is False
    assert cats_b["transporte"]["message"] == "Información insuficiente"
    assert cats_b["transporte"]["value"] is None

    # 3. get_social_accessibility recupera la evaluación guardada
    fetched_b = service.get_social_accessibility(PROJECT_B_ID)
    assert fetched_b["status"] == "partial"
    assert len(fetched_b["categories"]) == 3
