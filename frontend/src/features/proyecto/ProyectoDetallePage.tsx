import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ExpedienteCodeBadge } from '../../components/proyecto/ExpedienteCodeBadge'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import {
  evaluateEnvironmentalAssessment,
  evaluateSocialAccessibility,
  getEnvironmentalAssessment,
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
  EnvironmentalAssessmentResponse,
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
  const [environmentalAssessment, setEnvironmentalAssessment] = useState<EnvironmentalAssessmentResponse | null>(null)
  const [environmentalError, setEnvironmentalError] = useState<string | null>(null)
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

  const loadEnvironmentalAssessment = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await getEnvironmentalAssessment(projectId)
      setEnvironmentalAssessment(data)
    } catch {
      /* opcional hasta evaluación o consulta */
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
    void loadApproval()
    void loadSocialAssessment()
    void loadEnvironmentalAssessment()
  }, [loadProject, loadApproval, loadSocialAssessment, loadEnvironmentalAssessment])

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

  const runEnvironmentalAssessment = async () => {
    if (!projectId) return
    setBusy('environmental')
    setEnvironmentalError(null)
    try {
      const data = await evaluateEnvironmentalAssessment(projectId, newIdempotencyKey('env'))
      setEnvironmentalAssessment(data)
      setInfo('Evaluación de impacto ambiental territorial registrada exitosamente.')
    } catch (err) {
      setEnvironmentalError(err instanceof Error ? err.message : 'Error al evaluar impacto ambiental.')
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
                <span className="story-label">PMV 2 · HU1.4 / HU1.5</span>
                <h2>Accesibilidad territorial y equidad demográfica</h2>
              </div>
              <span className="review-badge">Análisis territorial social</span>
            </div>
            <p className="flow-hint">
              Evaluación social integrada de accesibilidad a servicios esenciales (salud, educación, transporte) y equidad demográfica por género y grupos de edad con datos agregados y delimitación territorial (El Tambo, Huancayo).
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
                    ? 'Evaluando accesibilidad y equidad…'
                    : socialAssessment
                    ? 'Actualizar evaluación social'
                    : 'Evaluar accesibilidad y equidad social'}
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

                {/* Panel de Puntuación Social Ponderada HU1.4 + HU1.5 */}
                <div className="social-score-card">
                  <div className="social-score-header">
                    <div>
                      <span className="social-score-tag">HU1.4 + HU1.5 · Puntuación Social Integrada</span>
                      <h3 style={{ margin: '0.2rem 0', fontSize: '1.15rem', color: '#0f172a' }}>
                        Puntaje Social:{' '}
                        {socialAssessment.social_score !== null && socialAssessment.social_score !== undefined
                          ? `${socialAssessment.social_score.toFixed(1)} / 100`
                          : 'No determinado'}
                      </h3>
                    </div>
                    {socialAssessment.social_score !== null && socialAssessment.social_score !== undefined ? (
                      <span
                        className={`social-score-badge ${
                          socialAssessment.social_score >= 70 ? 'score-good' : 'score-low'
                        }`}
                      >
                        {socialAssessment.social_score >= 70 ? 'Favorable' : 'Bajo'}
                      </span>
                    ) : (
                      <span className="social-score-badge score-neutral">
                        Sin ventaja automática
                      </span>
                    )}
                  </div>

                  <div className="social-score-breakdown">
                    <div className="social-score-item">
                      <span className="social-score-label">Base Accesibilidad (HU1.4):</span>
                      <span className="social-score-val">
                        {socialAssessment.status === 'complete'
                          ? '70.0 pts (Integral)'
                          : socialAssessment.status === 'partial'
                          ? '50.0 pts (Parcial)'
                          : 'No determinado (Insuficiente)'}
                      </span>
                    </div>
                    <div className="social-score-item">
                      <span className="social-score-label">Efecto Género (HU1.5):</span>
                      <span className="social-score-val">
                        {socialAssessment.equity?.gender?.score_effect_pts !== null &&
                        socialAssessment.equity?.gender?.score_effect_pts !== undefined
                          ? socialAssessment.equity.gender.score_effect_pts > 0
                            ? `+${socialAssessment.equity.gender.score_effect_pts.toFixed(1)} pts (${socialAssessment.equity.gender.effect_type})`
                            : socialAssessment.equity.gender.score_effect_pts < 0
                            ? `${socialAssessment.equity.gender.score_effect_pts.toFixed(1)} pts (${socialAssessment.equity.gender.effect_type})`
                            : '0.0 pts (Neutro)'
                          : 'No determinado · Sin ventaja automática'}
                      </span>
                    </div>
                    <div className="social-score-item">
                      <span className="social-score-label">Efecto Grupos de Edad (HU1.5):</span>
                      <span className="social-score-val">
                        {socialAssessment.equity?.age?.score_effect_pts !== null &&
                        socialAssessment.equity?.age?.score_effect_pts !== undefined
                          ? socialAssessment.equity.age.score_effect_pts > 0
                            ? `+${socialAssessment.equity.age.score_effect_pts.toFixed(1)} pts (${socialAssessment.equity.age.effect_type})`
                            : socialAssessment.equity.age.score_effect_pts < 0
                            ? `${socialAssessment.equity.age.score_effect_pts.toFixed(1)} pts (${socialAssessment.equity.age.effect_type})`
                            : '0.0 pts (Neutro)'
                          : 'No determinado · Sin ventaja automática'}
                      </span>
                    </div>
                  </div>

                  {socialAssessment.score_explanation && (
                    <p className="social-score-explanation">
                      <strong>Explicación del resultado:</strong> {socialAssessment.score_explanation}
                    </p>
                  )}
                </div>

                {/* Panel de Equidad Demográfica HU1.5 */}
                {socialAssessment.equity && (
                  <div className="equity-panel">
                    <div className="equity-header">
                      <div>
                        <span className="story-label" style={{ fontSize: '0.75rem' }}>PMV 2 · HU1.5</span>
                        <h3 style={{ margin: '0.15rem 0', fontSize: '1rem', color: '#0f172a' }}>
                          Equidad Demográfica: Género y Grupos de Edad
                        </h3>
                      </div>
                      <span
                        className={`green-status-badge ${
                          socialAssessment.equity.has_sufficient_data ? 'status-ok' : 'status-warn'
                        }`}
                      >
                        {socialAssessment.equity.has_sufficient_data
                          ? socialAssessment.equity.effect_summary
                          : 'Información insuficiente'}
                      </span>
                    </div>

                    <p className="equity-subtitle">
                      Datos demográficos agregados a nivel territorial sin información personal identificable. Fuente oficial censal INEI CPV de demostración para el distrito de El Tambo.
                    </p>

                    <div className="equity-grid">
                      {/* Dimensión Género */}
                      <div
                        className={`equity-card ${
                          socialAssessment.equity.gender.has_sufficient_data ? 'is-sufficient' : 'is-insufficient'
                        }`}
                      >
                        <div className="equity-card-header">
                          <h4 className="equity-card-title">{socialAssessment.equity.gender.dimension_label}</h4>
                          <span
                            className={`social-badge-status ${
                              socialAssessment.equity.gender.has_sufficient_data ? 'sufficient' : 'insufficient'
                            }`}
                          >
                            {socialAssessment.equity.gender.has_sufficient_data
                              ? 'Dato disponible'
                              : 'Información insuficiente'}
                          </span>
                        </div>

                        <div className="equity-target-group">
                          <strong>Grupo objetivo:</strong> {socialAssessment.equity.gender.target_group}
                        </div>

                        {socialAssessment.equity.gender.has_sufficient_data ? (
                          <div className="equity-metrics-box">
                            <div className="equity-metric-row">
                              <span className="equity-metric-label">Población agregada:</span>
                              <span className="equity-metric-value">
                                {socialAssessment.equity.gender.aggregated_population?.toLocaleString()} hab.
                              </span>
                            </div>
                            <div className="equity-metric-row">
                              <span className="equity-metric-label">Proporción poblacional:</span>
                              <span className="equity-metric-value">
                                {socialAssessment.equity.gender.aggregated_percentage}%
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="equity-insufficient-callout">
                            <strong>⚠️ Limitación metodológica (CA-HU1.5-02):</strong>
                            <p style={{ margin: '0.25rem 0 0' }}>
                              No existen datos demográficos fiables ni medidas específicas en el expediente. No se infieren proporciones sin evidencia ni se asigna conclusión favorable por presunción.
                            </p>
                          </div>
                        )}

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Criterio de Equidad:</span>
                          <div>{socialAssessment.equity.gender.equity_criterion}</div>
                        </div>

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Medidas Declaradas en Expediente:</span>
                          <div>
                            {socialAssessment.equity.gender.declared_benefit ||
                              'No se declaran medidas específicas de género en el expediente técnico'}
                          </div>
                        </div>

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Evidencia Territorial / Sustento:</span>
                          <div>
                            {socialAssessment.equity.gender.verifiable_data ||
                              'Sin evidencia territorial verificable'}
                          </div>
                        </div>

                        <div className="equity-effect-box">
                          <div style={{ marginBottom: '0.35rem', fontSize: '0.8rem', color: '#64748b' }}>
                            <strong>Efecto en la evaluación social:</strong>
                          </div>
                          <div>
                            <span
                              className={`equity-effect-pill ${socialAssessment.equity.gender.effect_type}`}
                            >
                              {socialAssessment.equity.gender.score_effect_pts !== null &&
                              socialAssessment.equity.gender.score_effect_pts !== undefined
                                ? `${socialAssessment.equity.gender.effect_type} (${socialAssessment.equity.gender.score_effect_pts >= 0 ? '+' : ''}${socialAssessment.equity.gender.score_effect_pts.toFixed(1)} pts)`
                                : 'No determinado · Sin ventaja automática'}
                            </span>
                          </div>
                        </div>

                        <div className="social-card-meta">
                          <div>
                            <strong>Fuente:</strong>
                            <div className="social-source-tag">
                              {socialAssessment.equity.gender.source_name}
                              {socialAssessment.equity.gender.is_simulated && (
                                <span className="social-simulated-pill">Simulado</span>
                              )}
                            </div>
                          </div>
                          <div style={{ marginTop: '0.35rem' }}>
                            <strong>Origen del dato:</strong> {socialAssessment.equity.gender.data_origin}
                          </div>
                        </div>
                      </div>

                      {/* Dimensión Grupos de Edad */}
                      <div
                        className={`equity-card ${
                          socialAssessment.equity.age.has_sufficient_data ? 'is-sufficient' : 'is-insufficient'
                        }`}
                      >
                        <div className="equity-card-header">
                          <h4 className="equity-card-title">{socialAssessment.equity.age.dimension_label}</h4>
                          <span
                            className={`social-badge-status ${
                              socialAssessment.equity.age.has_sufficient_data ? 'sufficient' : 'insufficient'
                            }`}
                          >
                            {socialAssessment.equity.age.has_sufficient_data
                              ? 'Dato disponible'
                              : 'Información insuficiente'}
                          </span>
                        </div>

                        <div className="equity-target-group">
                          <strong>Grupo objetivo:</strong> {socialAssessment.equity.age.target_group}
                        </div>

                        {socialAssessment.equity.age.has_sufficient_data ? (
                          <div className="equity-metrics-box">
                            <div className="equity-metric-row">
                              <span className="equity-metric-label">Población agregada:</span>
                              <span className="equity-metric-value">
                                {socialAssessment.equity.age.aggregated_population?.toLocaleString()} hab.
                              </span>
                            </div>
                            <div className="equity-metric-row">
                              <span className="equity-metric-label">Proporción poblacional:</span>
                              <span className="equity-metric-value">
                                {socialAssessment.equity.age.aggregated_percentage}%
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="equity-insufficient-callout">
                            <strong>⚠️ Limitación metodológica (CA-HU1.5-02):</strong>
                            <p style={{ margin: '0.25rem 0 0' }}>
                              No existen datos de grupos de edad fiables ni adecuaciones de accesibilidad universal verificables. No se infieren proporciones sin evidencia ni se asigna conclusión favorable por presunción.
                            </p>
                          </div>
                        )}

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Criterio de Equidad:</span>
                          <div>{socialAssessment.equity.age.equity_criterion}</div>
                        </div>

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Medidas Declaradas en Expediente:</span>
                          <div>
                            {socialAssessment.equity.age.declared_benefit ||
                              'No se declaran medidas de accesibilidad por edad en el expediente técnico'}
                          </div>
                        </div>

                        <div className="equity-detail-item">
                          <span className="equity-detail-label">Evidencia Territorial / Sustento:</span>
                          <div>
                            {socialAssessment.equity.age.verifiable_data ||
                              'Sin evidencia territorial verificable'}
                          </div>
                        </div>

                        <div className="equity-effect-box">
                          <div style={{ marginBottom: '0.35rem', fontSize: '0.8rem', color: '#64748b' }}>
                            <strong>Efecto en la evaluación social:</strong>
                          </div>
                          <div>
                            <span
                              className={`equity-effect-pill ${socialAssessment.equity.age.effect_type}`}
                            >
                              {socialAssessment.equity.age.score_effect_pts !== null &&
                              socialAssessment.equity.age.score_effect_pts !== undefined
                                ? `${socialAssessment.equity.age.effect_type} (${socialAssessment.equity.age.score_effect_pts >= 0 ? '+' : ''}${socialAssessment.equity.age.score_effect_pts.toFixed(1)} pts)`
                                : 'No determinado · Sin ventaja automática'}
                            </span>
                          </div>
                        </div>

                        <div className="social-card-meta">
                          <div>
                            <strong>Fuente:</strong>
                            <div className="social-source-tag">
                              {socialAssessment.equity.age.source_name}
                              {socialAssessment.equity.age.is_simulated && (
                                <span className="social-simulated-pill">Simulado</span>
                              )}
                            </div>
                          </div>
                          <div style={{ marginTop: '0.35rem' }}>
                            <strong>Origen del dato:</strong> {socialAssessment.equity.age.data_origin}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <TechnicalDetails data={socialAssessment} />
              </>
            )}
          </section>

          <section className="flow-panel environmental-flow-panel">
            <div className="flow-panel-heading">
              <div>
                <span className="story-label">PMV 2 · HU1.6 / HU1.7</span>
                <h2>Evaluación ambiental y conservación de áreas verdes</h2>
              </div>
              <span className="review-badge">Análisis ambiental territorial</span>
            </div>
            <p className="flow-hint">
              Evaluación del impacto ambiental y conservación de áreas verdes de la obra, con ponderación y desglose de puntaje ambiental, distinguiendo declaraciones en el expediente de la evidencia territorial de demostración (El Tambo, Huancayo).
            </p>

            {hasRole('PLANNER') && (
              <div style={{ marginBottom: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy !== null}
                  onClick={() => void runEnvironmentalAssessment()}
                >
                  {busy === 'environmental'
                    ? 'Evaluando impacto ambiental…'
                    : environmentalAssessment
                    ? 'Actualizar evaluación ambiental'
                    : 'Evaluar impacto ambiental'}
                </button>
              </div>
            )}

            {environmentalError && <Alert variant="error">{environmentalError}</Alert>}

            {environmentalAssessment && (
              <>
                <Alert
                  variant={
                    environmentalAssessment.status === 'sufficient' && environmentalAssessment.risk_level !== 'high'
                      ? 'success'
                      : 'error'
                  }
                >
                  <div>
                    <strong>
                      Nivel de riesgo: {environmentalAssessment.risk_level_label} ·{' '}
                      {environmentalAssessment.favorable_label}
                    </strong>
                  </div>
                  <div style={{ marginTop: '0.35rem', lineHeight: 1.45 }}>
                    {environmentalAssessment.summary}
                  </div>
                  {environmentalAssessment.risk_observation && (
                    <div className="env-risk-observation-box">
                      <strong>⚠️ Observación de riesgo ambiental relevante:</strong>
                      <p style={{ margin: '0.25rem 0 0' }}>{environmentalAssessment.risk_observation}</p>
                    </div>
                  )}
                  <div style={{ marginTop: '0.35rem', fontSize: '0.8rem', opacity: 0.9 }}>
                    Evaluado el: {formatDate(environmentalAssessment.evaluated_at)}
                  </div>
                </Alert>

                {/* Panel de Puntaje Ambiental y Áreas Verdes HU1.7 */}
                <div className="env-score-card">
                  <div className="env-score-header">
                    <div>
                      <span className="env-score-tag">HU1.7 · Puntuación Ambiental Ponderada</span>
                      <h3 style={{ margin: '0.2rem 0', fontSize: '1.15rem', color: '#0f172a' }}>
                        Puntaje Ambiental: {environmentalAssessment.environmental_score !== null && environmentalAssessment.environmental_score !== undefined
                          ? `${environmentalAssessment.environmental_score.toFixed(1)} / 100`
                          : 'No determinado'}
                      </h3>
                    </div>
                    {environmentalAssessment.environmental_score !== null && environmentalAssessment.environmental_score !== undefined && (
                      <span className={`env-score-badge ${environmentalAssessment.environmental_score >= 70 ? 'score-good' : 'score-low'}`}>
                        {environmentalAssessment.environmental_score >= 70 ? 'Aceptable' : 'Bajo'}
                      </span>
                    )}
                  </div>

                  <div className="env-score-breakdown">
                    <div className="env-score-item">
                      <span className="env-score-label">Puntaje Base (HU1.6):</span>
                      <span className="env-score-val">
                        {environmentalAssessment.risk_level === 'low'
                          ? '85.0 pts (Riesgo Bajo)'
                          : environmentalAssessment.risk_level === 'moderate'
                          ? '70.0 pts (Riesgo Moderado)'
                          : environmentalAssessment.risk_level === 'high'
                          ? '25.0 pts (Riesgo Alto)'
                          : 'No determinado (Datos insuficientes)'}
                      </span>
                    </div>
                    <div className="env-score-item">
                      <span className="env-score-label">Efecto Áreas Verdes (HU1.7):</span>
                      <span className="env-score-val">
                        {environmentalAssessment.green_area?.score_effect_pts !== null && environmentalAssessment.green_area?.score_effect_pts !== undefined
                          ? environmentalAssessment.green_area.score_effect_pts > 0
                            ? `+${environmentalAssessment.green_area.score_effect_pts.toFixed(1)} pts (${environmentalAssessment.green_area.effect_type})`
                            : environmentalAssessment.green_area.score_effect_pts < 0
                            ? `${environmentalAssessment.green_area.score_effect_pts.toFixed(1)} pts (${environmentalAssessment.green_area.effect_type})`
                            : '0.0 pts (Neutro)'
                          : 'No determinado · Sin ventaja ambiental automática'}
                      </span>
                    </div>
                  </div>

                  {environmentalAssessment.score_explanation && (
                    <p className="env-score-explanation">
                      <strong>Explicación del cálculo:</strong> {environmentalAssessment.score_explanation}
                    </p>
                  )}
                </div>

                {/* Detalle de Áreas Verdes HU1.7 */}
                {environmentalAssessment.green_area && (
                  <div className="green-area-panel">
                    <div className="green-area-header">
                      <div>
                        <span className="story-label" style={{ fontSize: '0.75rem' }}>PMV 2 · HU1.7</span>
                        <h3 style={{ margin: '0.15rem 0', fontSize: '1rem', color: '#0f172a' }}>
                          Conservación y Protección de Áreas Verdes
                        </h3>
                      </div>
                      <span className={`green-status-badge ${environmentalAssessment.green_area.has_sufficient_data ? 'status-ok' : 'status-warn'}`}>
                        {environmentalAssessment.green_area.has_sufficient_data
                          ? environmentalAssessment.green_area.affectation_type_label || 'Evaluado'
                          : 'Información insuficiente'}
                      </span>
                    </div>

                    {!environmentalAssessment.green_area.has_sufficient_data ? (
                      <div className="green-insufficient-banner">
                        <div style={{ fontWeight: 700, color: '#b45309', marginBottom: '0.25rem' }}>
                          ⚠️ Información insuficiente sobre áreas verdes (Sin ventaja ambiental automática)
                        </div>
                        <p style={{ margin: '0.35rem 0', fontSize: '0.85rem', color: '#92400e', lineHeight: 1.45 }}>
                          <strong>Efecto en el puntaje:</strong>{' '}
                          {environmentalAssessment.green_area.score_effect_pts !== null && environmentalAssessment.green_area.score_effect_pts !== undefined
                            ? `${environmentalAssessment.green_area.score_effect_pts.toFixed(1)} pts`
                            : 'No determinado · Sin ventaja ambiental automática'}
                        </p>
                        <p style={{ margin: 0, fontSize: '0.85rem', color: '#92400e', lineHeight: 1.45 }}>
                          El expediente no cuenta con superficie delimitada ni medidas de protección verificables. De conformidad con el criterio de aceptación <strong>CA-HU1.7-02</strong>, no se asigna bonificación ni ventaja ambiental automática.
                        </p>
                        <div className="social-source-tag" style={{ marginTop: '0.5rem' }}>
                          {environmentalAssessment.green_area.source_name}
                          {environmentalAssessment.green_area.is_simulated && (
                            <span className="social-simulated-pill">Simulado</span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="green-details-grid">
                        <div className="green-detail-card">
                          <span className="green-detail-label">Superficie de Áreas Verdes</span>
                          <div className="green-metric-value">
                            {environmentalAssessment.green_area.green_area_m2 !== null && environmentalAssessment.green_area.green_area_m2 !== undefined
                              ? `${environmentalAssessment.green_area.green_area_m2.toLocaleString()} m²`
                              : 'No determinada'}
                            {environmentalAssessment.green_area.green_area_percentage !== null && environmentalAssessment.green_area.green_area_percentage !== undefined && (
                              <span className="green-metric-percent">
                                ({environmentalAssessment.green_area.green_area_percentage}% del predio)
                              </span>
                            )}
                          </div>
                          <span className="green-detail-sub">
                            Total predio: {environmentalAssessment.green_area.total_project_area_m2?.toLocaleString() || 'N/A'} m²
                          </span>
                        </div>

                        <div className="green-detail-card">
                          <span className="green-detail-label">Delimitación Cartográfica</span>
                          <p className="green-detail-text">
                            {environmentalAssessment.green_area.delimitation_description || 'No delimitado'}
                          </p>
                        </div>

                        <div className="green-detail-card">
                          <span className="green-detail-label">Afectación y Medidas de Protección</span>
                          <p className="green-detail-text">
                            <strong>Declarado:</strong> {environmentalAssessment.green_area.declared_affectation || 'No especificado'}
                          </p>
                          <p className="green-detail-text">
                            <strong>Verificable:</strong> {environmentalAssessment.green_area.verifiable_affectation || 'No verificado'}
                          </p>
                          <p className="green-detail-text">
                            <strong>Medidas:</strong> {environmentalAssessment.green_area.protection_measures || 'Ninguna'}
                          </p>
                          <div style={{ marginTop: '0.4rem' }}>
                            <span className={`green-measures-pill ${environmentalAssessment.green_area.has_sufficient_measures ? 'pill-ok' : 'pill-warn'}`}>
                              {environmentalAssessment.green_area.has_sufficient_measures
                                ? '✓ Medidas suficientes y acreditadas'
                                : '⚠️ Medidas insuficientes o no acreditadas'}
                            </span>
                          </div>
                        </div>

                        <div className="green-detail-card">
                          <span className="green-detail-label">Efecto en el Puntaje y Sustento</span>
                          <div className="green-metric-value" style={{ fontSize: '1.1rem' }}>
                            {environmentalAssessment.green_area.score_effect_pts !== null && environmentalAssessment.green_area.score_effect_pts !== undefined
                              ? environmentalAssessment.green_area.score_effect_pts > 0
                                ? `+${environmentalAssessment.green_area.score_effect_pts.toFixed(1)} pts (Bonificación)`
                                : environmentalAssessment.green_area.score_effect_pts < 0
                                ? `${environmentalAssessment.green_area.score_effect_pts.toFixed(1)} pts (Penalización)`
                                : '0.0 pts (Neutro)'
                              : 'No determinado · Sin ventaja ambiental automática'}
                          </div>
                          <p className="green-detail-text" style={{ marginTop: '0.25rem' }}>
                            {environmentalAssessment.green_area.calculation_explanation}
                          </p>
                          <div className="social-source-tag" style={{ marginTop: '0.5rem' }}>
                            {environmentalAssessment.green_area.source_name}
                            {environmentalAssessment.green_area.is_simulated && (
                              <span className="social-simulated-pill">Simulado</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="env-contrast-panel">
                  <h3>Contraste: Declaración en expediente vs. Evidencia territorial de demostración</h3>
                  <div className="env-contrast-grid">
                    <div className="env-contrast-col env-col-declared">
                      <h4>Declarado en el expediente</h4>
                      <p>
                        <strong>Impactos declarados:</strong>{' '}
                        {environmentalAssessment.declared_vs_evidence.declared_by_applicant || 'No declarado'}
                      </p>
                      <p>
                        <strong>Medidas previstas:</strong>{' '}
                        {environmentalAssessment.declared_vs_evidence.declared_measures || 'No especificadas'}
                      </p>
                    </div>

                    <div className="env-contrast-col env-col-evidence">
                      <h4>Evidencia territorial de demostración (simulada)</h4>
                      <p>
                        <strong>Hallazgos cartográficos / normativos:</strong>{' '}
                        {environmentalAssessment.declared_vs_evidence.verifiable_evidence || (
                          <span className="env-insufficient-badge">Sin evidencia territorial (Información insuficiente)</span>
                        )}
                      </p>
                      <p>
                        <strong>Proximidad a fuentes hídricas:</strong>{' '}
                        {environmentalAssessment.declared_vs_evidence.proximity_to_water_meters !== null &&
                        environmentalAssessment.declared_vs_evidence.proximity_to_water_meters !== undefined
                          ? `${environmentalAssessment.declared_vs_evidence.proximity_to_water_meters} metros`
                          : 'No determinada'}
                      </p>
                      <p>
                        <strong>Zona de riesgo / faja marginal:</strong>{' '}
                        {environmentalAssessment.declared_vs_evidence.is_in_protected_or_risk_area === true ? (
                          'SÍ (Faja marginal intangible / Riesgo alto PDM)'
                        ) : environmentalAssessment.declared_vs_evidence.is_in_protected_or_risk_area === false ? (
                          'NO (Fuera de faja marginal)'
                        ) : (
                          <span className="env-insufficient-badge">No determinado: información insuficiente</span>
                        )}
                      </p>
                      <div className="social-source-tag">
                        {environmentalAssessment.declared_vs_evidence.evidence_source}
                        {environmentalAssessment.declared_vs_evidence.is_simulated && (
                          <span className="social-simulated-pill">Simulado</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {environmentalAssessment.status === 'insufficient' ? (
                  <div className="env-insufficient-banner">
                    <h4>Información insuficiente</h4>
                    <p>
                      Faltan datos esenciales para sustentar una valoración ambiental completa. No se emite pronunciamiento favorable por defecto.
                    </p>
                  </div>
                ) : (
                  <>
                    <h3 style={{ marginTop: '1.25rem', marginBottom: '0.5rem', fontSize: '1rem', color: '#0f172a' }}>
                      Impactos identificados y posibles mitigaciones
                    </h3>
                    <div className="env-impacts-grid">
                      {environmentalAssessment.impacts.map((imp, idx) => (
                        <div key={idx} className={`env-impact-card severity-${imp.severity}`}>
                          <div className="env-impact-header">
                            <span className="env-impact-comp">{imp.component_label}</span>
                            <span className={`env-severity-badge severity-${imp.severity}`}>
                              Severidad {imp.severity.toUpperCase()}
                            </span>
                          </div>
                          <p className="env-impact-desc">
                            <strong>Impacto:</strong> {imp.description}
                          </p>
                          <p className="env-impact-substantiation">
                            <strong>Sustento:</strong> {imp.substantiation}
                          </p>
                          {imp.mitigations && imp.mitigations.length > 0 && (
                            <div className="env-impact-mitigations">
                              <strong>Posibles mitigaciones:</strong>
                              <ul>
                                {imp.mitigations.map((m, mIdx) => (
                                  <li key={mIdx}>{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <TechnicalDetails data={environmentalAssessment} />
              </>
            )}
          </section>

          <section className="flow-panel legal-flow-panel">
            <div className="flow-panel-heading">
              <div>
                <span className="story-label">PMV 2 · HU2.2 / HU1.10</span>
                <h2>3. Conformidad jurídica y citas normativas exactas</h2>
              </div>
              <span className="review-badge">Asesoría Jurídica</span>
            </div>
            <p className="flow-hint">
              Contrasta los antecedentes del expediente con el corpus normativo versionado, citando el artículo o sección exacta de la norma aplicable para su cotejo directo, o advirtiendo cita no verificable sin fabricar artículos (Asesoría Jurídica).
            </p>
            <Link
              to={`/proyectos/${projectId}/revision-juridica`}
              className="btn btn-primary"
            >
              Abrir detalle de revisión jurídica y citas exactas
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
