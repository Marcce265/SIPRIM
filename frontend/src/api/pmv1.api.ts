import type {
  EvaluationAccepted,
  EvaluationResponse,
  HumanApprovalStatusResponse,
  LegalPrecheckResponse,
  NormativeSearchResponse,
  PMV1ProjectCreate,
  PMV1ProjectResponse,
  PMV1ValidationResponse,
  ZoningPrecheckResponse,
} from '../types/pmv1'
import { apiFetch } from './client'

export function createProject(payload: PMV1ProjectCreate): Promise<PMV1ProjectResponse> {
  return apiFetch<PMV1ProjectResponse>('/api/v1/projects', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  })
}

export function getProject(projectId: string): Promise<PMV1ProjectResponse> {
  return apiFetch<PMV1ProjectResponse>(`/api/v1/projects/${projectId}`, { auth: true })
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
