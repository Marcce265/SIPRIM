import { apiFetch } from './client'

export interface PrediccionSobrecosto {
  probabilidad: number
  nivel_riesgo: 'BAJO' | 'MEDIO' | 'ALTO'
  sobrecosto_estimado_pct: number
  factores_clave: string[]
}

export interface PrediccionViabilidadPlazo {
  clase_viabilidad: 'VIABLE' | 'RIESGO_MODERADO' | 'CRITICO'
  retraso_estimado_dias: number
  probabilidad_desviacion: number
  alertas_programacion: string[]
}

export interface DictamenMLResponse {
  project_id: string
  expediente_code: string
  sobrecosto: PrediccionSobrecosto
  viabilidad_plazo: PrediccionViabilidadPlazo
  resumen_ejecutivo: string
  timestamp: string
}

export interface MetricasModelosML {
  dataset_size: number
  train_size: number
  test_size: number
  features: string[]
  modelo_1_sobrecosto: {
    nombre: string
    algoritmo: string
    accuracy: number
    precision: number
    recall: number
    f1_score: number
    roc_auc: number
  }
  modelo_2_viabilidad_plazo: {
    nombre: string
    algoritmo: string
    accuracy: number
    precision: number
    recall: number
    f1_score: number
  }
}

export async function getMetricasML(): Promise<MetricasModelosML> {
  return apiFetch<MetricasModelosML>('/api/v1/ml/metricas-modelos')
}

export async function evaluateProjectWithML(expedienteCodeOrUuid: string): Promise<DictamenMLResponse> {
  return apiFetch<DictamenMLResponse>(`/api/v1/ml/evaluar-proyecto/${encodeURIComponent(expedienteCodeOrUuid)}`, {
    method: 'POST',
  })
}
