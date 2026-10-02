import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import {
  getEvaluation,
  getHumanApproval,
  getProject,
  legalPrecheck,
  requestEvaluation,
  validateProject,
  zoningPrecheck,
} from '../../api/pmv1.api'
import { useAuth } from '../auth/AuthContext'
import type {
  EvaluationResponse,
  HumanApprovalStatusResponse,
  LegalPrecheckResponse,
  PMV1ProjectResponse,
  PMV1ValidationResponse,
  ZoningPrecheckResponse,
} from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'
import { rememberProject } from '../../utils/recentProjects'

const POLL_MS = 2000
const POLL_MAX = 45

export function ProyectoDetallePage() {
  const { projectId = '' } = useParams()
  const location = useLocation()
  const flash = (location.state as { mensaje?: string } | null)?.mensaje
  const { hasRole } = useAuth()

  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [validation, setValidation] = useState<PMV1ValidationResponse | null>(null)
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null)
  const [legal, setLegal] = useState<LegalPrecheckResponse | null>(null)
  const [zoning, setZoning] = useState<ZoningPrecheckResponse | null>(null)
  const [approval, setApproval] = useState<HumanApprovalStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(flash ?? null)
  const [busy, setBusy] = useState<string | null>(null)

  const loadProject = useCallback(async () => {
    if (!projectId) return
    setError(null)
    try {
      const data = await getProject(projectId)
      setProject(data)
      rememberProject(mapPmV1ToProyecto(data))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el proyecto.')
    }
  }, [projectId])

  const loadApproval = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await getHumanApproval(projectId)
      setApproval(data)
    } catch {
      /* opcional hasta evaluación completada */
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
    void loadApproval()
  }, [loadProject, loadApproval])

  const runValidate = async () => {
    if (!projectId) return
    setBusy('validate')
    setError(null)
    try {
      const result = await validateProject(projectId)
      setValidation(result)
      await loadProject()
      setInfo(result.complete ? 'Expediente completo — puede solicitar evaluación económica.' : result.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validación fallida.')
    } finally {
      setBusy(null)
    }
  }

  const pollEvaluation = async (evaluationId: string) => {
    for (let attempt = 0; attempt < POLL_MAX; attempt += 1) {
      const ev = await getEvaluation(evaluationId)
      setEvaluation(ev)
      if (ev.status === 'completed' || ev.status === 'failed') {
        await loadProject()
        await loadApproval()
        return ev
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_MS))
    }
    throw new Error('La evaluación sigue en cola. Actualice la página en unos segundos.')
  }

  const runEvaluation = async () => {
    if (!project?.project_version_id) return
    setBusy('evaluation')
    setError(null)
    try {
      const accepted = await requestEvaluation(
        project.project_version_id,
        newIdempotencyKey('eval'),
      )
      setInfo(
        accepted.duplicated
          ? 'Ya existe una evaluación en curso para este expediente.'
          : 'Evaluación económica iniciada. Espere unos segundos.',
      )
      await pollEvaluation(accepted.evaluation_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo evaluar.')
    } finally {
      setBusy(null)
    }
  }

  const runLegal = async () => {
    if (!projectId) return
    setBusy('legal')
    setError(null)
    try {
      setLegal(await legalPrecheck(projectId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Precheck jurídico fallido.')
    } finally {
      setBusy(null)
    }
  }

  const runZoning = async () => {
    if (!projectId) return
    setBusy('zoning')
    setError(null)
    try {
      setZoning(await zoningPrecheck(projectId, newIdempotencyKey('zone')))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Precheck de zonificación fallido.')
    } finally {
      setBusy(null)
    }
  }

  const proyectoView = project ? mapPmV1ToProyecto(project) : null

  return (
    <div className="form-page pmv1-flow">
      <PageHeader
        title="Evaluación del expediente"
        description="Revise datos, solicite la evaluación preliminar y complete las revisiones según su rol."
      />

      {info && <Alert variant="success">{info}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      {!project && !error && <p className="muted">Cargando expediente…</p>}

      {proyectoView && (
        <>
          <ProyectoCard proyecto={proyectoView} />

          <section className="flow-panel">
            <h2>1. Validación del expediente</h2>
            <p className="flow-hint">Verifica presupuesto, beneficiarios y datos territoriales antes de evaluar.</p>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy !== null}
              onClick={() => void runValidate()}
            >
              {busy === 'validate' ? 'Validando…' : 'Validar expediente'}
            </button>
            {validation && (
              <>
                <Alert variant={validation.complete ? 'success' : 'error'}>
                  {validation.message}
                </Alert>
                <TechnicalDetails data={validation} />
              </>
            )}
          </section>

          <section className="flow-panel">
            <h2>2. Evaluación económica preliminar</h2>
            <p className="flow-hint">Disponible cuando el expediente esté completo.</p>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy !== null || !project?.project_version_id}
              onClick={() => void runEvaluation()}
            >
              {busy === 'evaluation' ? 'Procesando…' : 'Solicitar evaluación'}
            </button>
            {evaluation?.result && (
              <Alert variant="success">
                Puntaje {evaluation.result.score_0_100.toFixed(1)}/100 ·{' '}
                {evaluation.result.explanation}
              </Alert>
            )}
            {evaluation && <TechnicalDetails data={evaluation} />}
          </section>

          <section className="flow-panel">
            <h2>3. Revisión jurídica y de zonificación</h2>
            <div className="flow-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy !== null}
                onClick={() => void runLegal()}
              >
                {busy === 'legal' ? '…' : 'Revisión jurídica inicial'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy !== null}
                onClick={() => void runZoning()}
              >
                {busy === 'zoning' ? '…' : 'Compatibilidad urbanística (PDU)'}
              </button>
            </div>
            {legal && <TechnicalDetails data={legal} />}
            {zoning && <TechnicalDetails data={zoning} />}
          </section>

          <section className="flow-panel">
            <h2>4. Normativa y dictamen final</h2>
            <ul className="flow-links">
              {hasRole('LEGAL_ADVISOR') && (
                <li>
                  <Link to="/normativa">Consultar normativa aplicable</Link>
                </li>
              )}
              {hasRole('ADMIN') && (
                <li>
                  <Link to={`/proyectos/${projectId}/aprobacion`}>
                    Emitir dictamen de aprobación
                  </Link>
                </li>
              )}
              {!hasRole('LEGAL_ADVISOR') && !hasRole('ADMIN') && (
                <li className="muted">
                  La consulta normativa y el dictamen final las realiza personal autorizado.
                </li>
              )}
            </ul>
            {approval && <TechnicalDetails data={approval} />}
          </section>
        </>
      )}
    </div>
  )
}
