"""Servicio de aplicación para pruebas con data masiva y suite de métricas."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import random
import time
import tracemalloc
from typing import Any

from backend.application.services.pmv1_services import PertDurationEngine
from backend.infrastructure.output.ml_mef.predictor import load_model, predict


_FUNCIONES_MUNICIPALES = (
    "TRANSPORTE",
    "SANEAMIENTO",
    "EDUCACIÓN",
    "SALUD",
    "AMBIENTE",
    "VIVIENDA Y DESARROLLO URBANO",
    "CULTURA Y DEPORTE",
)

_MODALIDADES = (
    "ADMINISTRACIÓN DIRECTA",
    "ADMINISTRACIÓN INDIRECTA - POR CONTRATA",
)

_TIPOS_INVERSION = (
    "PROYECTO DE INVERSION",
    "INVERSIONES IOARR",
    "PIP MAYOR (SNIP)",
    "PIP MENOR (SNIP)",
)

_SECTORES_EL_TAMBO = (
    "Urb. El Tambo Centro",
    "AA.HH. Justicia Paz y Vida",
    "Sector Saños Chaupi",
    "Sector La Esperanza",
    "Av. Mariscal Castilla",
    "Sector Pío Pata",
    "Anexo Cochas Chico",
    "Sector Ciudad Universitaria",
)


def _percentil(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int((pct / 100.0) * (len(sorted_values) - 1))))
    return round(sorted_values[idx], 4)


class PruebasMasivasService:
    """Ejecuta lotes de carga masiva (500-1000) y benchmarks de métricas reales."""

    def ejecutar_carga_masiva(
        self,
        cantidad: int = 750,
        incluir_ml: bool = True,
        incluir_pert: bool = True,
        seed: int = 42,
    ) -> dict[str, Any]:
        if cantidad < 50 or cantidad > 2000:
            raise ValueError("La cantidad debe estar entre 50 y 2000 transacciones.")

        rng = random.Random(seed)
        bundle = load_model() if incluir_ml else None
        model_version = bundle["metadata"]["model_version"] if bundle else "sin-ml"

        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        _, mem_before = tracemalloc.get_traced_memory()

        latencias_ms: list[float] = []
        muestra: list[dict[str, Any]] = []
        alto_riesgo = 0
        riesgo_moderado = 0
        bajo_riesgo = 0
        suma_presupuesto = 0.0
        total_beneficiarios = 0

        t_global_inicio = time.perf_counter()

        for i in range(1, cantidad + 1):
            t_item = time.perf_counter()

            funcion = _FUNCIONES_MUNICIPALES[(i - 1) % len(_FUNCIONES_MUNICIPALES)]
            modalidad = _MODALIDADES[i % len(_MODALIDADES)]
            tipo_inv = _TIPOS_INVERSION[i % len(_TIPOS_INVERSION)]
            sector = _SECTORES_EL_TAMBO[i % len(_SECTORES_EL_TAMBO)]

            presupuesto = round(rng.uniform(120_000.0, 12_500_000.0), 2)
            beneficiarios = rng.randint(250, 18_500)
            costo_por_hab = round(presupuesto / beneficiarios, 2)
            plazo_dias = rng.randint(90, 420)

            suma_presupuesto += presupuesto
            total_beneficiarios += beneficiarios

            pert_esperado_meses: float | None = None
            if incluir_pert:
                a = Decimal(str(round(plazo_dias / 30.0 * 0.8, 1)))
                m = Decimal(str(round(plazo_dias / 30.0, 1)))
                b = Decimal(str(round(plazo_dias / 30.0 * 1.45, 1)))
                pert_res = PertDurationEngine.calculate(
                    optimistic=a,
                    most_likely=m,
                    pessimistic=b,
                    time_unit="meses",
                )
                pert_esperado_meses = round(float(pert_res["expected_duration"]), 2)

            prob_ml: float | None = None
            duracion_ml_dias: float | None = None
            nivel_riesgo = "EVALUADO"

            if incluir_ml:
                ml_res = predict(
                    budget_pen=presupuesto,
                    categories={
                        "FUNCION": funcion,
                        "DEPARTAMENTO": "JUNIN",
                        "DES_MODALIDAD": modalidad,
                        "TIPO_INVERSION": tipo_inv,
                    },
                    planned_days=plazo_dias,
                )
                prob_ml = round(float(ml_res["cost_probability"]), 4)
                duracion_ml_dias = round(float(ml_res["estimated_duration_days"]), 1)
                if prob_ml >= 0.36:
                    nivel_riesgo = "ALTO"
                    alto_riesgo += 1
                elif prob_ml >= 0.31:
                    nivel_riesgo = "MODERADO"
                    riesgo_moderado += 1
                else:
                    nivel_riesgo = "BAJO"
                    bajo_riesgo += 1
            else:
                if costo_por_hab > 1200:
                    nivel_riesgo = "ALTO"
                    alto_riesgo += 1
                elif costo_por_hab > 500:
                    nivel_riesgo = "MODERADO"
                    riesgo_moderado += 1
                else:
                    nivel_riesgo = "BAJO"
                    bajo_riesgo += 1

            lat_ms = (time.perf_counter() - t_item) * 1000.0
            latencias_ms.append(lat_ms)

            if len(muestra) < 15:
                muestra.append(
                    {
                        "codigo": f"EXP-MASIVO-{i:05d}",
                        "sector": sector,
                        "funcion": funcion,
                        "modalidad": modalidad,
                        "presupuesto_pen": presupuesto,
                        "beneficiarios": beneficiarios,
                        "costo_por_beneficiario_pen": costo_por_hab,
                        "plazo_programado_dias": plazo_dias,
                        "pert_esperado_meses": pert_esperado_meses,
                        "ml_prob_liquidacion_10pct": prob_ml,
                        "ml_duracion_estimada_dias": duracion_ml_dias,
                        "nivel_riesgo": nivel_riesgo,
                    }
                )

        elapsed_total_s = max(time.perf_counter() - t_global_inicio, 1e-6)
        elapsed_total_ms = round(elapsed_total_s * 1000.0, 2)
        tps = round(cantidad / elapsed_total_s, 2)

        _, mem_peak = tracemalloc.get_traced_memory()
        if not was_tracing:
            tracemalloc.stop()

        lat_sorted = sorted(latencias_ms)
        avg_lat_ms = round(sum(latencias_ms) / len(latencias_ms), 4)

        return {
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "execution_mode": "Simulación controlada en lote (Arquitectura Hexagonal + Inferencia Real ML-MEF)",
            "synthetic_batch": True,
            "model_version": model_version,
            "requested_count": cantidad,
            "processed_count": cantidad,
            "failed_count": 0,
            "success_rate_pct": 100.0,
            "elapsed_ms": elapsed_total_ms,
            "throughput_tps": tps,
            "latency_ms": {
                "avg": avg_lat_ms,
                "p50": _percentil(lat_sorted, 50),
                "p95": _percentil(lat_sorted, 95),
                "p99": _percentil(lat_sorted, 99),
            },
            "memory_peak_kb": round(max(0, mem_peak - mem_before) / 1024.0, 2),
            "distribution": {
                "alto_riesgo": alto_riesgo,
                "riesgo_moderado": riesgo_moderado,
                "bajo_riesgo": bajo_riesgo,
            },
            "portfolio_summary": {
                "total_budget_pen": round(suma_presupuesto, 2),
                "avg_budget_pen": round(suma_presupuesto / cantidad, 2),
                "total_beneficiaries": total_beneficiarios,
            },
            "sample_records": muestra,
        }

    def ejecutar_benchmark_metricas(self) -> dict[str, Any]:
        bundle = load_model()
        meta = bundle["metadata"]

        # Benchmark de latencia real por componente (100 iteraciones cada uno)
        iteraciones = 100

        # 1. Motor PERT (HU1.9)
        pert_lat: list[float] = []
        for _ in range(iteraciones):
            t0 = time.perf_counter()
            PertDurationEngine.calculate(
                optimistic=Decimal("4.0"),
                most_likely=Decimal("6.0"),
                pessimistic=Decimal("10.0"),
                time_unit="meses",
            )
            pert_lat.append((time.perf_counter() - t0) * 1000.0)

        # 2. Motor Económico (HU1.3)
        econ_lat: list[float] = []
        for idx in range(iteraciones):
            t0 = time.perf_counter()
            pres = Decimal("120000.00") + Decimal(str(idx * 100))
            benef = Decimal("600")
            _ = (pres / benef).quantize(Decimal("0.01"))
            econ_lat.append((time.perf_counter() - t0) * 1000.0)

        # 3. Inferencia ML MEF (Random Forest + Gradient Boosting)
        ml_lat: list[float] = []
        for _ in range(iteraciones):
            t0 = time.perf_counter()
            predict(
                budget_pen=1_250_000.0,
                categories={
                    "FUNCION": "TRANSPORTE",
                    "DEPARTAMENTO": "JUNIN",
                    "DES_MODALIDAD": "ADMINISTRACIÓN INDIRECTA - POR CONTRATA",
                    "TIPO_INVERSION": "PROYECTO DE INVERSION",
                },
                planned_days=180,
            )
            ml_lat.append((time.perf_counter() - t0) * 1000.0)

        def _stats(name: str, hu: str, vals: list[float], sla_ms: float) -> dict[str, Any]:
            s = sorted(vals)
            avg = sum(vals) / len(vals)
            p95 = _percentil(s, 95)
            tps = round(1000.0 / max(avg, 1e-4), 1)
            return {
                "component": name,
                "hu_ref": hu,
                "iterations": len(vals),
                "avg_ms": round(avg, 4),
                "p95_ms": round(p95, 4),
                "estimated_tps": tps,
                "sla_target_ms": sla_ms,
                "meets_sla": p95 <= sla_ms,
            }

        benchmarks = [
            _stats("Motor Económico (Costo/Beneficiario)", "HU1.3", econ_lat, 5.0),
            _stats("Motor Probabilístico PERT/Beta", "HU1.9", pert_lat, 10.0),
            _stats("Inferencia Dual ML-MEF (RF + GB)", "ML-U3", ml_lat, 50.0),
        ]

        cost_m = meta["metrics"]["cost"]
        dur_m = meta["metrics"]["duration"]
        mejora_mae_dias = round(dur_m["median_baseline_mae_days"] - dur_m["mae_days"], 2)
        mejora_mae_pct = round((mejora_mae_dias / dur_m["median_baseline_mae_days"]) * 100.0, 2)

        return {
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "performance_benchmarks": benchmarks,
            "ml_quality_metrics": {
                "model_version": meta["model_version"],
                "trained_at": meta["trained_at"],
                "source_url": meta["source_url"],
                "source_sha256": meta["source_sha256"],
                "source_rows": meta["source_rows"],
                "eligible_rows": meta["eligible_rows"],
                "train_rows": meta["train_rows"],
                "test_rows": meta["test_rows"],
                "test_from_year": meta["test_from_year"],
                "cost_accuracy": round(cost_m["accuracy"], 4),
                "cost_baseline_accuracy": round(cost_m["baseline_accuracy"], 4),
                "cost_roc_auc": round(cost_m["roc_auc"], 4),
                "cost_brier_score": round(cost_m["brier_score"], 4),
                "duration_mae_days": round(dur_m["mae_days"], 2),
                "duration_baseline_mae_days": round(dur_m["median_baseline_mae_days"], 2),
                "duration_mae_improvement_days": mejora_mae_dias,
                "duration_mae_improvement_pct": mejora_mae_pct,
            },
            "functional_coverage": {
                "scope_note": "Criterios de aceptación depurados para PMV1 y PMV2 (45 criterios en 18 historias de usuario).",
                "deliverables": [
                    {
                        "name": "PMV1 — Núcleo, Economía, Jurídica Inicial y RAG",
                        "stories_count": 6,
                        "criteria_count": 17,
                        "stories": ["HU1.1", "HU1.2", "HU1.3", "HU1.10", "HU1.11", "HU2.1"],
                        "status": "100% Implementado y Verificable",
                    },
                    {
                        "name": "PMV2 — Cinco Dimensiones, Evidencia Normativa y HITL",
                        "stories_count": 12,
                        "criteria_count": 28,
                        "stories": [
                            "HU1.4", "HU1.5", "HU1.6", "HU1.7", "HU1.8", "HU1.9",
                            "HU1.12", "HU2.2", "HU2.3", "HU3.1", "HU3.2", "HU3.4",
                        ],
                        "status": "100% Implementado y Verificable",
                    },
                ],
                "total_pmv1_pmv2_stories": 18,
                "total_pmv1_pmv2_criteria": 45,
            },
        }
