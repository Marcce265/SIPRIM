from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.application.dto.ml_dto import (
    DictamenMLResponseDTO,
    InputMLProyectoDTO,
    MetricasModelosMLDTO,
    PrediccionSobrecostoDTO,
    PrediccionViabilidadPlazoDTO,
)
from backend.application.use_cases.predecir_metricas_ml import PredecirMetricasMLUseCase
from backend.infrastructure.config.dependencies import get_platform_service
from backend.infrastructure.output.ml.scikit_learn_adapter import ScikitLearnMLAdapter


router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])

# Instancia singleton del adaptador Scikit-Learn
_adapter = ScikitLearnMLAdapter()
_use_case = PredecirMetricasMLUseCase(_adapter)


def get_ml_use_case() -> PredecirMetricasMLUseCase:
    return _use_case


@router.post(
    "/predecir-sobrecosto",
    response_model=PrediccionSobrecostoDTO,
    summary="Caso 1: Predecir riesgo de sobrecosto con Random Forest",
)
def predecir_sobrecosto(
    datos: InputMLProyectoDTO,
    use_case: Annotated[PredecirMetricasMLUseCase, Depends(get_ml_use_case)],
) -> PrediccionSobrecostoDTO:
    return use_case.predecir_sobrecosto(datos.model_dump())


@router.post(
    "/predecir-retraso",
    response_model=PrediccionViabilidadPlazoDTO,
    summary="Caso 2: Predecir viabilidad y retraso con Gradient Boosting",
)
def predecir_retraso(
    datos: InputMLProyectoDTO,
    use_case: Annotated[PredecirMetricasMLUseCase, Depends(get_ml_use_case)],
) -> PrediccionViabilidadPlazoDTO:
    return use_case.predecir_viabilidad_plazo(datos.model_dump())


@router.get(
    "/metricas-modelos",
    response_model=MetricasModelosMLDTO,
    summary="Consultar métricas de validación de los modelos (Accuracy, F1, ROC-AUC)",
)
def obtener_metricas(
    use_case: Annotated[PredecirMetricasMLUseCase, Depends(get_ml_use_case)],
) -> MetricasModelosMLDTO:
    return use_case.obtener_metricas()


@router.post(
    "/evaluar-proyecto/{identificador}",
    response_model=DictamenMLResponseDTO,
    summary="Evaluar un expediente existente con los 2 casos de predicción ML",
)
def evaluar_proyecto_ml(
    identificador: str,
    use_case: Annotated[PredecirMetricasMLUseCase, Depends(get_ml_use_case)],
    platform_service=Depends(get_platform_service),
) -> DictamenMLResponseDTO:
    # Intentar resolver desde platform_db
    try:
        from uuid import UUID
        is_uuid = False
        try:
            p_uuid = UUID(identificador)
            is_uuid = True
        except ValueError:
            is_uuid = False

        if is_uuid:
            proj = platform_service.get_project(p_uuid)
        else:
            proj = platform_service.get_project_by_code(identificador)

        datos = {
            "monto_inversion": float(proj.get("total_budget") or 250_000.0),
            "beneficiarios": int(proj.get("target_beneficiaries") or 1200),
            "tipo_proyecto": proj.get("name") or "Infraestructura urbana",
            "zona_intervencion": "Urbana consolidada",
            "plazo_dias_programado": 180,
            "complejidad_tecnica": 2,
            "variacion_diseno_pct": 6.5,
        }
        return use_case.evaluar_proyecto_completo(
            project_id=proj.get("id"),
            expediente_code=proj.get("code") or identificador,
            datos=datos,
        )
    except Exception:
        # Fallback de demostración con datos sintéticos basados en el código
        datos_demo = {
            "monto_inversion": 1_250_000.0,
            "beneficiarios": 3500,
            "tipo_proyecto": "Transporte y Vías Urbanas",
            "zona_intervencion": "Urbana consolidada",
            "plazo_dias_programado": 180,
            "complejidad_tecnica": 2,
            "variacion_diseno_pct": 8.0,
        }
        return use_case.evaluar_proyecto_completo(
            project_id=None,
            expediente_code=identificador,
            datos=datos_demo,
        )
