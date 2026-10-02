import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getHumanApproval, getProject, submitHumanApproval } from '../../api/pmv1.api'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import type { HumanApprovalStatusResponse, PMV1ProjectResponse } from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'

type Decision = 'approved' | 'rejected' | 'observed'

export function AprobacionPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [status, setStatus] = useState<HumanApprovalStatusResponse | null>(null)
  const [decision, setDecision] = useState<Decision>('approved')
  const [justification, setJustification] = useState('Dictamen de cierre PMV1 conforme a evaluación técnica.')
  const [conditions, setConditions] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!projectId) return
    const [proj, appr] = await Promise.all([getProject(projectId), getHumanApproval(projectId)])
    setProject(proj)
    setStatus(appr)
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
            <option value="approved">Aprobado</option>
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

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Registrando…' : 'Emitir dictamen'}
        </button>
      </form>
    </div>
  )
}
