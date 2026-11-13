"""Script ejecutable para demostración en terminal de Episodio 3 y Episodio 4."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.application.services.pruebas_masivas_service import PruebasMasivasService


def main() -> None:
    svc = PruebasMasivasService()

    print("=== EPISODIO 3: PRUEBA CON DATA MASIVA (750 EXPEDIENTES) ===")
    masiva = svc.ejecutar_carga_masiva(cantidad=750, incluir_ml=True, incluir_pert=True)
    print(f"Modo: {masiva['execution_mode']}")
    print(f"Procesados: {masiva['processed_count']} / {masiva['requested_count']} (Éxito: {masiva['success_rate_pct']}%)")
    print(f"Tiempo total: {masiva['elapsed_ms']} ms | Rendimiento: {masiva['throughput_tps']} TPS")
    print(f"Latencia: avg={masiva['latency_ms']['avg']} ms | p95={masiva['latency_ms']['p95']} ms | p99={masiva['latency_ms']['p99']} ms")
    print(f"Memoria pico: {masiva['memory_peak_kb']} KB")
    print(f"Distribución de riesgo: {json.dumps(masiva['distribution'])}")

    print("\n=== EPISODIO 4: PRUEBA CON MÉTRICAS (RENDIMIENTO, ML Y PMV1/2) ===")
    metricas = svc.ejecutar_benchmark_metricas()
    for b in metricas["performance_benchmarks"]:
        print(
            f" - [{b['hu_ref']}] {b['component']}: avg={b['avg_ms']} ms, p95={b['p95_ms']} ms, "
            f"TPS={b['estimated_tps']}, SLA={b['meets_sla']}"
        )
    ml_q = metricas["ml_quality_metrics"]
    print(
        f"ML-MEF ({ml_q['eligible_rows']} filas reales): Exactitud={ml_q['cost_accuracy']*100:.2f}%, "
        f"ROC-AUC={ml_q['cost_roc_auc']}, MAE Duración={ml_q['duration_mae_days']} d "
        f"(mejora {ml_q['duration_mae_improvement_days']} d / {ml_q['duration_mae_improvement_pct']}% vs baseline)"
    )


if __name__ == "__main__":
    main()
