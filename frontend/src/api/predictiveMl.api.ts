import { apiFetch } from './client'

export interface MLMetadata {
  model_version: string
  trained_at: string
  source_url: string
  source_sha256: string
  eligible_rows: number
  train_rows: number
  test_rows: number
  test_from_year: number
  synthetic_data: boolean
  categories: Record<string, string[]>
  budget_range: [number, number]
  metrics: { cost: { accuracy: number; balanced_accuracy: number; roc_auc: number; baseline_accuracy: number }; duration: { mae_days: number; median_baseline_mae_days: number } }
  limitations: string[]
}

export interface MLPrediction {
  prediction_id: string
  project_id: string
  project_version_id: string
  project_code: string
  created_at: string
  model_version: string
  budget_pen: number
  categories: Record<string, string>
  cost_probability: number
  estimated_duration_days: number
  planned_days: number | null
  difference_days: number | null
}

export interface MLPredictionInput {
  project_version_id: string
  function: string
  department: string
  execution_mode: string
  investment_type: string
  planned_days: number | null
}

export const getMLMetadata = () => apiFetch<MLMetadata>('/api/v1/ml/model', { auth: true })
export const getLatestML = (id: string) => apiFetch<MLPrediction | null>(`/api/v1/ml/projects/${encodeURIComponent(id)}/latest`, { auth: true })
export const predictWithML = (id: string, payload: MLPredictionInput) => apiFetch<MLPrediction>(`/api/v1/ml/projects/${encodeURIComponent(id)}/predict`, { method: 'POST', auth: true, body: JSON.stringify(payload) })
