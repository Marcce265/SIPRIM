from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID

from backend.application.dto.ml_dto import (
    DictamenMLResponseDTO,
    MetricasModelosMLDTO,
    PrediccionSobrecostoDTO,
    PrediccionViabilidadPlazoDTO,
)
from backend.domain.ports.ml_prediction_port import MLPredictionPort
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class PredecirMetricasMLUseCase:
    """Caso de uso de aplicación para orquestar las predicciones de Machine Learning."""

    def __init__(self, ml_service: MLPredictionPort) -> None:
        self._ml_service = ml_service

    def predecir_sobrecosto(self, datos: Mapping[str, Any]) -> PrediccionSobrecostoDTO:
        res = self._ml_service.predecir_sobrecosto(datos)
        return PrediccionSobrecostoDTO(
            probabilidad=res.probabilidad,
            nivel_riesgo=res.nivel_riesgo,
            sobrecosto_estimado_pct=res.sobrecosto_estimado_pct,
            factores_clave=res.factores_clave,
        )

    def predecir_viabilidad_plazo(self, datos: Mapping[str, Any]) -> PrediccionViabilidadPlazoDTO:
        res = self._ml_service.predecir_viabilidad_plazo(datos)
        return PrediccionViabilidadPlazoDTO(
            clase_viabilidad=res.clase_viabilidad,
            retraso_estimado_dias=res.retraso_estimado_dias,
            probabilidad_desviacion=res.probabilidad_desviacion,
            alertas_programacion=res.alertas_programacion,
        )

    def evaluar_proyecto_completo(
        self, project_id: Any, expediente_code: str, datos: Mapping[str, Any]
    ) -> DictamenMLResponseDTO:
        dictamen = self._ml_service.evaluar_proyecto_ml(project_id, expediente_code, datos)
        return DictamenMLResponseDTO(
            project_id=str(dictamen.project_id),
            expediente_code=dictamen.expediente_code,
            sobrecosto=PrediccionSobrecostoDTO(
                probabilidad=dictamen.sobrecosto.probabilidad,
                nivel_riesgo=dictamen.sobrecosto.nivel_riesgo,
                sobrecosto_estimado_pct=dictamen.sobrecosto.sobrecosto_estimado_pct,
                factores_clave=dictamen.sobrecosto.factores_clave,
            ),
            viabilidad_plazo=PrediccionViabilidadPlazoDTO(
                clase_viabilidad=dictamen.viabilidad_plazo.clase_viabilidad,
                retraso_estimado_dias=dictamen.viabilidad_plazo.retraso_estimado_dias,
                probabilidad_desviacion=dictamen.viabilidad_plazo.probabilidad_desviacion,
                alertas_programacion=dictamen.viabilidad_plazo.alertas_programacion,
            ),
            resumen_ejecutivo=dictamen.resumen_ejecutivo,
            timestamp=dictamen.timestamp.isoformat(),
        )

    def obtener_metricas(self) -> MetricasModelosMLDTO:
        metricas = self._ml_service.obtener_metricas_modelos()
        return MetricasModelosMLDTO.model_validate(metricas)
