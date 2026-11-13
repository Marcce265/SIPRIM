"""Puerto del dominio para pruebas de carga masiva y medición de métricas."""
from __future__ import annotations

from typing import Any, Protocol


class PruebasMasivasPort(Protocol):
    """Contrato hexagonal para ejecutar simulaciones masivas y diagnósticos de métricas."""

    def ejecutar_carga_masiva(
        self,
        cantidad: int = 750,
        incluir_ml: bool = True,
        incluir_pert: bool = True,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Procesa un lote masivo de expedientes y retorna tiempos, TPS y muestra."""
        ...

    def ejecutar_benchmark_metricas(self) -> dict[str, Any]:
        """Ejecuta pruebas de latencia, calidad ML (MEF) y cobertura PMV1/PMV2."""
        ...
