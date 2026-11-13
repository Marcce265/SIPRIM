import { apiFetch } from './client'

export interface CargaMasivaRequest {
  cantidad: number
  incluir_ml: boolean
  incluir_pert: boolean
  seed?: number
}

export interface CargaMasivaSampleRecord {
  codigo: string
  sector: string
  funcion: string
  modalidad: string
  presupuesto_pen: number
  beneficiarios: number
  costo_por_beneficiario_pen: number
  plazo_programado_dias: number
  pert_esperado_meses: number | null
  ml_prob_liquidacion_10pct: number | null
  ml_duracion_estimada_dias: number | null
  nivel_riesgo: string
}

export interface CargaMasivaResponse {
  executed_at: string
  execution_mode: string
  synthetic_batch: boolean
  model_version: string
  requested_count: number
  processed_count: number
  failed_count: number
  success_rate_pct: number
  elapsed_ms: number
  throughput_tps: number
  latency_ms: {
    avg: number
    p50: number
    p95: number
    p99: number
  }
  memory_peak_kb: number
  distribution: {
    alto_riesgo: number
    riesgo_moderado: number
    bajo_riesgo: number
  }
  portfolio_summary: {
    total_budget_pen: number
    avg_budget_pen: number
    total_beneficiaries: number
  }
  sample_records: CargaMasivaSampleRecord[]
}

export interface PerformanceBenchmarkItem {
  component: string
  hu_ref: string
  iterations: number
  avg_ms: number
  p95_ms: number
  estimated_tps: number
  sla_target_ms: number
  meets_sla: boolean
}

export interface MetricasSistemaResponse {
  measured_at: string
  performance_benchmarks: PerformanceBenchmarkItem[]
  ml_quality_metrics: {
    model_version: string
    trained_at: string
    source_url: string
    source_sha256: string
    source_rows: number
    eligible_rows: number
    train_rows: number
    test_rows: number
    test_from_year: number
    cost_accuracy: number
    cost_baseline_accuracy: number
    cost_roc_auc: number
    cost_brier_score: number
    duration_mae_days: number
    duration_baseline_mae_days: number
    duration_mae_improvement_days: number
    duration_mae_improvement_pct: number
  }
  functional_coverage: {
    scope_note: string
    deliverables: Array<{
      name: string
      stories_count: number
      criteria_count: number
      stories: string[]
      status: string
    }>
    total_pmv1_pmv2_stories: number
    total_pmv1_pmv2_criteria: number
  }
}

export function runCargaMasiva(payload: CargaMasivaRequest): Promise<CargaMasivaResponse> {
  return apiFetch<CargaMasivaResponse>('/api/v1/pruebas/data-masiva', {
    method: 'POST',
    auth: true,
    timeoutMs: 60_000,
    body: JSON.stringify(payload),
  })
}

export function getMetricasSistema(): Promise<MetricasSistemaResponse> {
  return apiFetch<MetricasSistemaResponse>('/api/v1/pruebas/metricas', {
    auth: true,
  })
}
