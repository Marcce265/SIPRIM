import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ExpedienteCodeBadge } from '../../components/proyecto/ExpedienteCodeBadge'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import {
  evaluateSocialAccessibility,
  getEvaluation,
  getHumanApproval,
  getProject,
  getSocialAccessibility,
  requestEvaluation,
  validateProject,
  zoningPrecheck,
} from '../../api/pmv1.api'
import { useAuth } from '../auth/AuthContext'
import type {
  EvaluationResponse,
  HumanApprovalStatusResponse,
  PMV1ProjectResponse,
  PMV1ValidationResponse,
  SocialAccessibilityResponse,
  ZoningPrecheckResponse,
} from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'
import { formatDate, formatFileSize } from '../../utils/format'
import { getPhysicalExpediente } from '../../utils/physicalExpedienteStorage'
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
  const [zoning, setZoning] = useState<ZoningPrecheckResponse | null>(null)
  const [approval, setApproval] = useState<HumanApprovalStatusResponse | null>(null)
  const [socialAssessment, setSocialAssessment] = useState<SocialAccessibilityResponse | null>(null)
  const [socialError, setSocialError] = useState<string | null>(null)
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

  const loadSocialAssessment = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await getSocialAccessibility(projectId)
      setSocialAssessment(data)
    } catch {
      /* opcional hasta evaluación o consulta */
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
    void loadApproval()
    void loadSocialAssessment()
  }, [loadProject, loadApproval, loadSocialAssessment])

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

  const runSocialAssessment = async () => {
    if (!projectId) return
    setBusy('social')
    setSocialError(null)
    try {
      const data = await evaluateSocialAccessibility(projectId, newIdempotencyKey('social'))
      setSocialAssessment(data)
      setInfo('Evaluación de accesibilidad social territorial registrada exitosamente.')
    } catch (err) {
      setSocialError(err instanceof Error ? err.message : 'Error al evaluar accesibilidad social.')
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
  const physicalExpediente = projectId ? getPhysicalExpediente(projectId) : null

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

          {project?.code && (
            <ExpedienteCodeBadge code={project.code} projectId={project.project_id} />
          )}

          {physicalExpediente && (
            <section className="flow-panel expediente-physical-panel">
              <h2>Expediente físico adjunto</h2>
              <p className="flow-hint">
                {physicalExpediente.fileName} · {formatFileSize(physicalExpediente.size)} · subido{' '}
                {formatDate(physicalExpediente.uploadedAt)}
              </p>
              <a
                className="btn btn-secondary"
                href={physicalExpediente.dataUrl}
                download={physicalExpediente.fileName}
              >
                Descargar documento
              </a>
            </section>
          )}

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

          <section className="flow-panel social-flow-panel">
            <div className="flow-panel-heading">
              <div>
                <span className="story-label">PMV 2 · HU1.4</span>
                <h2>Accesibilidad a salud, educación y transporte</h2>
              </div>
              <span className="review-badge">Análisis territorial social</span>
            </div>
            <p className="flow-hint">
              Evaluación multidimensional de accesibilidad territorial para priorizar zonas desatendidas (El Tambo, Huancayo).
            </p>

            {hasRole('PLANNER') && (
              <div style={{ marginBottom: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy !== null}
                  onClick={() => void runSocialAssessment()}
                >
                  {busy === 'social'
                    ? 'Evaluando accesibilidad…'
                    : socialAssessment
                    ? 'Actualizar evaluación de accesibilidad'
                    : 'Evaluar accesibilidad social'}
                </button>
              </div>
            )}

            {socialError && <Alert variant="error">{socialError}</Alert>}

            {socialAssessment && (
              <>
                <Alert variant={socialAssessment.status === 'complete' ? 'success' : 'error'}>
                  <strong>{socialAssessment.summary}</strong>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.82rem' }}>
                    Evaluado el: {formatDate(socialAssessment.evaluated_at)}
                  </div>
                </Alert>

                <div className="social-cards-grid">
                  {socialAssessment.categories.map((cat) => (
                    <div
                      key={cat.category}
                      className={`social-card ${cat.has_sufficient_data ? 'is-sufficient' : 'is-insufficient'}`}
                    >
                      <div className="social-card-header">
                        <h3 className="social-card-title">{cat.category_label}</h3>
                        <span className={`social-badge-status ${cat.has_sufficient_data ? 'sufficient' : 'insufficient'}`}>
                          {cat.has_sufficient_data ? 'Dato disponible' : 'Insuficiente'}
                        </span>
                      </div>

                      <div className="social-indicator-label">{cat.indicator}</div>

                      {cat.has_sufficient_data && cat.value !== null ? (
                        <div className="social-metric-box">
                          <span className="social-metric-value">{cat.value}</span>
                          <span className="social-metric-unit">{cat.unit}</span>
                        </div>
                      ) : (
                        <div className="social-insufficient-callout">
                          Información insuficiente
                        </div>
                      )}

                      <p style={{ margin: '0.35rem 0', fontSize: '0.82rem', color: '#334155', lineHeight: 1.45 }}>
                        {cat.message}
                      </p>

                      <div className="social-card-meta">
                        <div>
                          <strong>Fuente:</strong>
                          <div className="social-source-tag">
                            {cat.source}
                            {cat.is_simulated && <span className="social-simulated-pill">Simulado</span>}
                          </div>
                        </div>
                        <div style={{ marginTop: '0.35rem' }}>
                          <strong>Origen del dato:</strong> {cat.data_origin}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <TechnicalDetails data={socialAssessment} />
              </>
            )}
          </section>

          <section className="flow-panel legal-flow-panel">
            <div className="flow-panel-heading">
              <div>
                <span className="story-label">PMV1 · HU1.10</span>
                <h2>3. Conformidad con contratación pública</h2>
              </div>
              <span className="review-badge">Revisión jurídica</span>
            </div>
            <p className="flow-hint">
              Abra la vista dedicada para ejecutar el análisis y consultar faltantes,
              observaciones y trazabilidad normativa.
            </p>
            <Link
              to={`/proyectos/${projectId}/revision-juridica`}
              className="btn btn-primary"
            >
              Abrir detalle de revisión jurídica
            </Link>
          </section>

          <section className="flow-panel">
            <h2>4. Compatibilidad urbanística (HU1.11)</h2>
            <p className="flow-hint">
              Revisa de forma preliminar el uso de suelo declarado frente al PDU/PDM.
            </p>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy !== null}
              onClick={() => void runZoning()}
            >
              {busy === 'zoning' ? 'Analizando…' : 'Analizar compatibilidad urbanística'}
            </button>
            {zoning && <TechnicalDetails data={zoning} />}
          </section>

          <section className="flow-panel">
            <h2>5. Normativa y dictamen final</h2>
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
