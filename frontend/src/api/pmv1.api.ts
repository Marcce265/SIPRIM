import type {
  CheckpointResponse,
  CheckpointResumeRequest,
  CheckpointResumeResponse,
  EvaluationAccepted,
  EvaluationResponse,
  HumanApprovalStatusResponse,
  LegalAlertResolveRequest,
  LegalAlertResolutionResponse,
  LegalAssessmentResponse,
  LegalPrecheckResponse,
  NormativeSearchResponse,
  PertEstimateCreate,
  PertEstimateResponse,
  TechnicalFeasibilityResponse,
  UnifiedAssessmentSummaryResponse,
  PMV1ProjectCreate,
  PMV1ProjectResponse,
  PMV1ValidationResponse,
  EnvironmentalAssessmentResponse,
  SocialAccessibilityResponse,
  ZoningPrecheckResponse,
} from '../types/pmv1'
import { isExpedienteUuid } from '../utils/expedienteRef'
import { apiFetch } from './client'

export function createProject(payload: PMV1ProjectCreate): Promise<PMV1ProjectResponse> {
  return apiFetch<PMV1ProjectResponse>('/api/v1/projects', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function resumeProjectCheckpoint(
  projectId: string,
  payload: CheckpointResumeRequest,
  idempotencyKey?: string,
): Promise<CheckpointResumeResponse> {
  return apiFetch<CheckpointResumeResponse>(`/api/v1/projects/${projectId}/checkpoint/resume`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
    body: JSON.stringify(payload),
  })
}

export function getProjectCheckpoint(projectId: string): Promise<CheckpointResponse | null> {
  return apiFetch<CheckpointResponse | null>(`/api/v1/projects/${projectId}/checkpoint`, {
    auth: true,
  })
}

export function getProject(projectId: string): Promise<PMV1ProjectResponse> {
  return apiFetch<PMV1ProjectResponse>(`/api/v1/projects/${projectId}`, { auth: true })
}

export function getProjectByCode(code: string): Promise<PMV1ProjectResponse> {
  const encoded = encodeURIComponent(code.trim())
  return apiFetch<PMV1ProjectResponse>(`/api/v1/projects/by-code/${encoded}`, {
    auth: true,
  })
}

export async function resolveProject(ref: string): Promise<PMV1ProjectResponse> {
  const query = ref.trim()
  if (isExpedienteUuid(query)) {
    return getProject(query)
  }
  return getProjectByCode(query)
}

export function evaluateProjectWithIA(projectId: string): Promise<{
  puntaje: number
  viabilidad: 'ALTA' | 'MEDIA' | 'BAJA'
  justificacion: string
  observaciones: string[]
  recomendaciones: string[]
}> {
  return apiFetch(`/api/v1/projects/${projectId}/evaluacion-ia`, {
    method: 'POST',
    auth: true,
    timeoutMs: 60_000,
  })
}

export function validateProject(projectId: string): Promise<PMV1ValidationResponse> {
  return apiFetch<PMV1ValidationResponse>(`/api/v1/projects/${projectId}/validate`, {
    method: 'POST',
    auth: true,
  })
}

export function requestEvaluation(
  projectVersionId: string,
  idempotencyKey: string,
): Promise<EvaluationAccepted> {
  return apiFetch<EvaluationAccepted>('/api/v1/evaluations', {
    method: 'POST',
    auth: true,
    idempotencyKey,
    body: JSON.stringify({ project_version_id: projectVersionId }),
  })
}

export function getEvaluation(evaluationId: string): Promise<EvaluationResponse> {
  return apiFetch<EvaluationResponse>(`/api/v1/evaluations/${evaluationId}`, { auth: true })
}

export function legalPrecheck(projectId: string): Promise<LegalPrecheckResponse> {
  return apiFetch<LegalPrecheckResponse>(`/api/v1/projects/${projectId}/legal-precheck`, {
    method: 'POST',
    auth: true,
  })
}

export function zoningPrecheck(
  projectId: string,
  idempotencyKey: string,
): Promise<ZoningPrecheckResponse> {
  return apiFetch<ZoningPrecheckResponse>(`/api/v1/projects/${projectId}/zoning-precheck`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
  })
}

export function searchNormative(
  query: string,
  idempotencyKey?: string,
): Promise<NormativeSearchResponse> {
  return apiFetch<NormativeSearchResponse>('/api/v1/normative/search', {
    method: 'POST',
    auth: true,
    idempotencyKey,
    body: JSON.stringify({ query, only_in_force: true, limit: 8 }),
  })
}

export function getHumanApproval(projectId: string): Promise<HumanApprovalStatusResponse> {
  return apiFetch<HumanApprovalStatusResponse>(`/api/v1/projects/${projectId}/approval`, {
    auth: true,
  })
}

export function submitHumanApproval(
  projectId: string,
  payload: { decision: 'approved' | 'rejected' | 'observed'; justification: string; conditions?: string },
  idempotencyKey: string,
): Promise<unknown> {
  return apiFetch(`/api/v1/projects/${projectId}/approval`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
    body: JSON.stringify(payload),
  })
}

export function getSocialAccessibility(projectId: string): Promise<SocialAccessibilityResponse> {
  return apiFetch<SocialAccessibilityResponse>(`/api/v1/projects/${projectId}/social-assessment`, {
    auth: true,
  })
}

export function evaluateSocialAccessibility(
  projectId: string,
  idempotencyKey?: string,
): Promise<SocialAccessibilityResponse> {
  return apiFetch<SocialAccessibilityResponse>(`/api/v1/projects/${projectId}/social-assessment`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
  })
}

export function getEnvironmentalAssessment(projectId: string): Promise<EnvironmentalAssessmentResponse> {
  return apiFetch<EnvironmentalAssessmentResponse>(`/api/v1/projects/${projectId}/environmental-assessment`, {
    auth: true,
  })
}

export function evaluateEnvironmentalAssessment(
  projectId: string,
  idempotencyKey?: string,
): Promise<EnvironmentalAssessmentResponse> {
  return apiFetch<EnvironmentalAssessmentResponse>(`/api/v1/projects/${projectId}/environmental-assessment`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
  })
}
export function getLegalAssessment(projectId: string): Promise<LegalAssessmentResponse> {
  return apiFetch<LegalAssessmentResponse>(`/api/v1/projects/${projectId}/legal-assessment`, {
    auth: true,
  })
}

export function evaluateLegalAssessment(
  projectId: string,
  idempotencyKey?: string,
): Promise<LegalAssessmentResponse> {
  return apiFetch<LegalAssessmentResponse>(`/api/v1/projects/${projectId}/legal-assessment`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
  })
}

export function resolveLegalAlert(
  projectId: string,
  payload: LegalAlertResolveRequest,
  idempotencyKey?: string,
): Promise<LegalAlertResolutionResponse> {
  return apiFetch<LegalAlertResolutionResponse>(`/api/v1/projects/${projectId}/legal-alert/resolve`, {
    method: 'POST',
    auth: true,
    idempotencyKey,
    body: JSON.stringify(payload),
  })
}

export function getPertEstimate(projectId: string): Promise<PertEstimateResponse | null> {
  return apiFetch<PertEstimateResponse | null>(`/api/v1/projects/${projectId}/pert-estimate`, {
    auth: true,
  })
}

export function registerPertEstimate(
  projectId: string,
  payload: PertEstimateCreate,
): Promise<PertEstimateResponse> {
  return apiFetch<PertEstimateResponse>(`/api/v1/projects/${projectId}/pert-estimate`, {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function getTechnicalFeasibility(
  projectId: string,
  versionId?: string,
): Promise<TechnicalFeasibilityResponse | null> {
  const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : ''
  return apiFetch<TechnicalFeasibilityResponse | null>(
    `/api/v1/projects/${projectId}/technical-assessment${query}`,
    {
      auth: true,
    },
  )
}

export function evaluateTechnicalFeasibility(
  projectId: string,
  idempotencyKey?: string,
): Promise<TechnicalFeasibilityResponse> {
  return apiFetch<TechnicalFeasibilityResponse>(
    `/api/v1/projects/${projectId}/technical-assessment`,
    {
      method: 'POST',
      auth: true,
      idempotencyKey,
    },
  )
}

export function getUnifiedAssessmentSummary(
  projectId: string,
  versionId?: string,
): Promise<UnifiedAssessmentSummaryResponse> {
  const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : ''
  return apiFetch<UnifiedAssessmentSummaryResponse>(
    `/api/v1/projects/${projectId}/unified-summary${query}`,
    {
      auth: true,
    },
  )
}

