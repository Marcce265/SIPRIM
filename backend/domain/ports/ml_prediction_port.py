from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from backend.domain.entities.prediccion_ml import (
    DictamenMLUnificado,
    PrediccionSobrecosto,
    PrediccionViabilidadPlazo,
)


class MLPredictionPort(ABC):
    """Puerto de dominio hexagonal para inferencia y analítica predictiva con Machine Learning."""

    @abstractmethod
    def predecir_sobrecosto(self, datos_proyecto: Mapping[str, Any]) -> PrediccionSobrecosto:
        raise NotImplementedError

    @abstractmethod
    def predecir_viabilidad_plazo(self, datos_proyecto: Mapping[str, Any]) -> PrediccionViabilidadPlazo:
        raise NotImplementedError

    @abstractmethod
    def evaluar_proyecto_ml(
        self, project_id: Any, expediente_code: str, datos_proyecto: Mapping[str, Any]
    ) -> DictamenMLUnificado:
        raise NotImplementedError

    @abstractmethod
    def obtener_metricas_modelos(self) -> dict[str, Any]:
        raise NotImplementedError
