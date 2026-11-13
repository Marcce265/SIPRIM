"""Controlador REST para pruebas con data masiva y suite de métricas."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.application.services.pruebas_masivas_service import PruebasMasivasService
from backend.infrastructure.config.dependencies import require_legal_or_planner

router = APIRouter(prefix="/api/v1/pruebas", tags=["Pruebas y Métricas"])

_service = PruebasMasivasService()


class CargaMasivaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(default=750, ge=50, le=2000)
    incluir_ml: bool = Field(default=True)
    incluir_pert: bool = Field(default=True)
    seed: int = Field(default=42, ge=1, le=99999)


@router.post("/data-masiva")
def ejecutar_carga_masiva(
    payload: CargaMasivaRequest,
    _: Annotated[dict, Depends(require_legal_or_planner)],
) -> dict:
    try:
        return _service.ejecutar_carga_masiva(
            cantidad=payload.cantidad,
            incluir_ml=payload.incluir_ml,
            incluir_pert=payload.incluir_pert,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/metricas")
def obtener_metricas_sistema(
    _: Annotated[dict, Depends(require_legal_or_planner)],
) -> dict:
    return _service.ejecutar_benchmark_metricas()
