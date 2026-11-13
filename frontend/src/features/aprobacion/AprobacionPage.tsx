import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getHumanApproval,
  getProject,
  getUnifiedAssessmentSummary,
  submitHumanApproval,
} from '../../api/pmv1.api'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import type {
  HumanApprovalStatusResponse,
  PMV1ProjectResponse,
  UnifiedAssessmentSummaryResponse,
} from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'

type Decision = 'approved' | 'rejected' | 'observed'

export function AprobacionPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [status, setStatus] = useState<HumanApprovalStatusResponse | null>(null)
  const [summary, setSummary] = useState<UnifiedAssessmentSummaryResponse | null>(null)
  const [decision, setDecision] = useState<Decision>('approved')
  const [justification, setJustification] = useState('Dictamen de cierre PMV1 conforme a evaluación técnica.')
  const [conditions, setConditions] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const isPaused = Boolean(status?.is_paused) || project?.status === 'pending_review'
  const hasLegalAlert = Boolean(status?.has_legal_alert)
  const summaryBlocksApproval = decision === 'approved' && !summary?.allows_final_approval
  const isApprovalBlocked =
    isPaused || (hasLegalAlert && decision === 'approved') || summaryBlocksApproval

  const refresh = useCallback(async () => {
    if (!projectId) return
    const [proj, appr, unified] = await Promise.all([
      getProject(projectId),
      getHumanApproval(projectId),
      getUnifiedAssessmentSummary(projectId),
    ])
    setProject(proj)
    setStatus(appr)
    setSummary(unified)
    if (!unified.allows_final_approval) {
      setDecision((current) => (current === 'approved' ? 'observed' : current))
      setJustification((current) =>
        current === 'Dictamen de cierre PMV1 conforme a evaluación técnica.'
          ? 'Expediente observado: debe completar y subsanar las dimensiones pendientes.'
          : current,
      )
    }
  }, [projectId])

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el estado.')
    })
  }, [refresh])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!projectId) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await submitHumanApproval(
        projectId,
        {
          decision,
          justification: justification.trim(),
          conditions: decision === 'observed' ? conditions.trim() : undefined,
        },
        newIdempotencyKey('approval'),
      )
      setSuccess('Dictamen registrado en human_approvals.')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el dictamen.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="form-page pmv1-flow">
      <PageHeader
        title="Dictamen de aprobación"
        description="Registro formal de la decisión de la autoridad municipal sobre el expediente."
      />

      {project && (
        <p className="flow-hint">
          Proyecto <strong>{project.title}</strong> · estado {project.status}.{' '}
          <Link to={`/proyectos/${projectId}`}>Volver al flujo</Link>
        </p>
      )}

      {status && <TechnicalDetails data={status} />}

      {isPaused && (
        <Alert variant="error">
          <strong>Aprobación final bloqueada (HU3.1):</strong> El expediente se encuentra en estado{' '}
          <strong>Pendiente de revisión</strong> por punto de control persistente ante riesgo alto.
          Conforme a las reglas de control, no es posible emitir un dictamen final de aprobación hasta que la revisión humana sea resuelta.
        </Alert>
      )}
      {hasLegalAlert && (
        <Alert variant="error">
          <strong>Aprobación final y priorización bloqueadas por Alerta Legal activa (HU2.3):</strong>{' '}
          {status?.legal_alert_motive} [{status?.legal_alert_norm}].
          Conforme a las reglas de control, no es posible emitir un dictamen final de aprobación definitiva ni avanzar a priorización hasta que la alerta sea resuelta o levantada formalmente por personal autorizado de Asesoría Jurídica.
        </Alert>
      )}
      {summary && !summary.allows_final_approval && (
        <Alert variant="error">
          <strong>Aprobación definitiva deshabilitada (HU1.12):</strong>{' '}
          {summary.blocking_reasons.length > 0
            ? summary.blocking_reasons.join(' ')
            : `Faltan por completar o subsanar: ${summary.missing_dimensions.join(', ')}.`}
          {' '}Todavía puede registrar el expediente como observado o rechazado.
        </Alert>
      )}
      {error && <Alert variant="error">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}

      <form className="expediente-form" onSubmit={(e) => void onSubmit(e)}>
        <label className="form-field span-2">
          <span className="form-field-label">Decisión</span>
          <select
            className="form-field-input"
            value={decision}
            onChange={(e) => setDecision(e.target.value as Decision)}
          >
            <option value="approved" disabled={!summary?.allows_final_approval}>
              Aprobado
            </option>
            <option value="observed">Observado (exige condiciones)</option>
            <option value="rejected">Rechazado</option>
          </select>
        </label>

        <label className="form-field span-2">
          <span className="form-field-label">Justificación</span>
          <textarea
            className="form-field-input"
            rows={4}
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            required
          />
        </label>

        {decision === 'observed' && (
          <label className="form-field span-2">
            <span className="form-field-label">Condiciones</span>
            <textarea
              className="form-field-input"
              rows={3}
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              required
            />
          </label>
        )}

        <button type="submit" className="btn btn-primary" disabled={loading || isApprovalBlocked}>
          {loading ? 'Registrando…' : 'Emitir dictamen'}
        </button>
      </form>
    </div>
  )
}
