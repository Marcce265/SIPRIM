export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string
  full_name: string
  roles: string[]
}

export interface PMV1ProjectCreate {
  code?: string
  title?: string
  description?: string
  location?: string
  proposed_land_use?: string
  estimated_budget_pen?: number
  beneficiaries_count?: number
}

export interface PMV1ProjectResponse {
  project_id: string
  project_version_id: string
  code: string
  version_number: number
  status: string
  title: string
  description: string
  location: string | null
  proposed_land_use: string | null
  territorial_data_origin: string
  estimated_budget_pen: number
  beneficiaries_count: number
}

export interface PMV1ValidationResponse {
  complete: boolean
  status: string
  missing_fields: string[]
  message: string
}

export interface EvaluationAccepted {
  evaluation_id: string
  event_id: string
  status: string
  duplicated: boolean
  publication_pending: boolean
}

export interface EconomicResult {
  economic_assessment_id: string
  cost_per_beneficiary_pen: number
  score_0_100: number
  explanation: string
  algorithm_version: string
  socioeconomic_return: null
  warnings: string[]
}

export interface EvaluationResponse {
  evaluation_id: string
  project_version_id: string
  criteria_version_id: string
  status: string
  result: EconomicResult | null
}

export interface LegalPrecheckResponse {
  project_id: string
  status: string
  complies: null
  sources: string[]
  requires_review: boolean
  observations: string[]
}

export interface ZoningPrecheckResponse {
  review_id: string
  project_id: string
  status: string
  compatible: boolean | null
  requires_human_review: boolean
  alerts: string[]
  limitations: string
}

export interface NormativeChunkItem {
  id: string
  document_name: string
  short_code: string
  version: string
  topic: string
  content: string
  relevance_score: number
  has_alert: boolean
  location?: string | null
}

export interface NormativeSearchResponse {
  query: string
  total_results: number
  results: NormativeChunkItem[]
  alerts_found: string[]
  disclaimer: string
  requires_human_review: boolean
}

export interface HumanApprovalStatusResponse {
  project_id: string
  project_status: string
  is_evaluated: boolean
  requires_human_approval: boolean
  current_approval: {
    decision: string
    justification: string
    conditions: string | null
  } | null
}

export interface SocialAccessibilityCategoryItem {
  category: string
  category_label: string
  status: 'sufficient' | 'insufficient'
  has_sufficient_data: boolean
  indicator?: string | null
  value?: number | null
  unit?: string | null
  source: string
  data_origin: string
  is_simulated: boolean
  message: string
}

export interface SocialAccessibilityResponse {
  project_id: string
  project_code: string
  project_version_id?: string | null
  status: 'complete' | 'partial' | 'insufficient'
  summary: string
  categories: SocialAccessibilityCategoryItem[]
  evaluated_at: string
  duplicated?: boolean
}
export interface EnvironmentalImpactItem {
  component: string
  component_label: string
  description: string
  severity: 'baja' | 'moderada' | 'alta' | 'indeterminada'
  substantiation: string
  mitigations: string[]
}

export interface EnvironmentalMitigationItem {
  component: string
  measure: string
  type: string
  origin: string
}

export interface EnvironmentalDeclaredVsEvidence {
  declared_by_applicant: string | null
  declared_measures: string | null
  verifiable_evidence: string | null
  evidence_source: string
  is_simulated: boolean
  proximity_to_water_meters?: number | null
  is_in_protected_or_risk_area: boolean
}

export interface EnvironmentalAssessmentResponse {
  project_id: string
  project_code: string
  project_version_id?: string | null
  status: 'sufficient' | 'insufficient'
  risk_level: 'low' | 'moderate' | 'high' | 'insufficient'
  risk_level_label: string
  risk_observation?: string | null
  requires_human_review: boolean
  favorable: boolean | null
  favorable_label: string
  summary: string
  declared_vs_evidence: EnvironmentalDeclaredVsEvidence
  impacts: EnvironmentalImpactItem[]
  mitigations: EnvironmentalMitigationItem[]
  evaluated_at: string
  duplicated?: boolean
}

