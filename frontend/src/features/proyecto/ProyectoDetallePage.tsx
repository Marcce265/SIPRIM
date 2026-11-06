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
  getPertEstimate,
  getProject,
  getProjectCheckpoint,
  getSocialAccessibility,
  registerPertEstimate,
  requestEvaluation,
  validateProject,
  zoningPrecheck,
} from '../../api/pmv1.api'
import { useAuth } from '../auth/AuthContext'
import type {
  CheckpointResponse,
  EvaluationResponse,
  HumanApprovalStatusResponse,
  PertEstimateResponse,
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
  const [checkpoint, setCheckpoint] = useState<CheckpointResponse | null>(null)
  const [socialAssessment, setSocialAssessment] = useState<SocialAccessibilityResponse | null>(null)
  const [socialError, setSocialError] = useState<string | null>(null)
  const [environmentalAssessment, setEnvironmentalAssessment] = useState<EnvironmentalAssessmentResponse | null>(null)
  const [environmentalError, setEnvironmentalError] = useState<string | null>(null)
  const [pertEstimate, setPertEstimate] = useState<PertEstimateResponse | null>(null)
  const [pertInputA, setPertInputA] = useState<string>('')
  const [pertInputM, setPertInputM] = useState<string>('')
  const [pertInputB, setPertInputB] = useState<string>('')
  const [pertTimeUnit, setPertTimeUnit] = useState<string>('meses')
  const [pertError, setPertError] = useState<{ field?: string; reason?: string; message: string } | null>(null)
  const [pertSuccess, setPertSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(flash ?? null)
  const [busy, setBusy] = useState<string | null>(null)

  const loadProject = useCallback(async () => {
    if (!projectId) return
    setError(null)
    try {
      const data = await getProject(projectId)
      setProject(data)
      if (data.checkpoint) {
        setCheckpoint(data.checkpoint)
      }
      if (data.pert_estimate) {
        setPertEstimate(data.pert_estimate)
        setPertInputA(data.pert_estimate.optimistic_duration.toString())
        setPertInputM(data.pert_estimate.most_likely_duration.toString())
        setPertInputB(data.pert_estimate.pessimistic_duration.toString())
        setPertTimeUnit(data.pert_estimate.time_unit)
      }
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

  const loadCheckpoint = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await getProjectCheckpoint(projectId)
      setCheckpoint(data)
    } catch {
      /* opcional */
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

  const loadPertEstimate = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await getPertEstimate(projectId)
      setPertEstimate(data)
      if (data) {
        setPertInputA(data.optimistic_duration.toString())
        setPertInputM(data.most_likely_duration.toString())
        setPertInputB(data.pessimistic_duration.toString())
        setPertTimeUnit(data.time_unit)
      }
    } catch {
      /* opcional */
    }
  }, [projectId])

  const handleCalculatePert = async () => {
    if (!projectId) return
    setPertSuccess(null)

    const rawA = pertInputA.trim()
    const rawM = pertInputM.trim()
    const rawB = pertInputB.trim()

    if (!rawA) {
      setPertEstimate(null)
      setPertError({
        field: 'optimistic_duration',
        reason: 'Falta ingresar la duración optimista (a).',
        message: 'Falta ingresar la duración optimista (a). Ingrese un valor numérico mayor o igual a 0.',
      })
      return
    }
    if (!rawM) {
      setPertEstimate(null)
      setPertError({
        field: 'most_likely_duration',
        reason: 'Falta ingresar la duración más probable (m).',
        message: 'Falta ingresar la duración más probable (m). Ingrese un valor que cumpla a ≤ m ≤ b.',
      })
      return
    }
    if (!rawB) {
      setPertEstimate(null)
      setPertError({
        field: 'pessimistic_duration',
        reason: 'Falta ingresar la duración pesimista (b).',
        message: 'Falta ingresar la duración pesimista (b). Ingrese un valor que cumpla m ≤ b.',
      })
      return
    }

    const a = Number(rawA)
    const m = Number(rawM)
    const b = Number(rawB)

    if (isNaN(a) || !isFinite(a)) {
      setPertEstimate(null)
      setPertError({
        field: 'optimistic_duration',
        reason: 'La duración optimista (a) debe ser un número finito válido.',
        message: 'El valor ingresado en duración optimista (a) no es un número finito.',
      })
      return
    }
    if (isNaN(m) || !isFinite(m)) {
      setPertEstimate(null)
      setPertError({
        field: 'most_likely_duration',
        reason: 'La duración más probable (m) debe ser un número finito válido.',
        message: 'El valor ingresado en duración más probable (m) no es un número finito.',
      })
      return
    }
    if (isNaN(b) || !isFinite(b)) {
      setPertEstimate(null)
      setPertError({
        field: 'pessimistic_duration',
        reason: 'La duración pesimista (b) debe ser un número finito válido.',
        message: 'El valor ingresado en duración pesimista (b) no es un número finito.',
      })
      return
    }

    if (a < 0) {
      setPertEstimate(null)
      setPertError({
        field: 'optimistic_duration',
        reason: `La duración optimista (a = ${a}) no puede ser negativa; debe ser mayor o igual a 0.`,
        message: 'La duración optimista no puede ser un número negativo.',
      })
      return
    }
    if (m < 0) {
      setPertEstimate(null)
      setPertError({
        field: 'most_likely_duration',
        reason: `La duración más probable (m = ${m}) no puede ser negativa; debe ser mayor o igual a 0.`,
        message: 'La duración más probable no puede ser un número negativo.',
      })
      return
    }
    if (b < 0) {
      setPertEstimate(null)
      setPertError({
        field: 'pessimistic_duration',
        reason: `La duración pesimista (b = ${b}) no puede ser negativa; debe ser mayor o igual a 0.`,
        message: 'La duración pesimista no puede ser un número negativo.',
      })
      return
    }

    if (a > m) {
      setPertEstimate(null)
      setPertError({
        field: 'optimistic_duration',
        reason: `Orden inválido: la duración optimista (a = ${a}) no puede ser mayor que la duración más probable (m = ${m}). Corrija el orden 0 ≤ a ≤ m ≤ b.`,
        message: `El valor optimista (${a}) supera al más probable (${m}). Corrija el orden para poder calcular la estimación PERT.`,
      })
      return
    }
    if (m > b) {
      setPertEstimate(null)
      setPertError({
        field: 'most_likely_duration',
        reason: `Orden inválido: la duración más probable (m = ${m}) no puede ser mayor que la duración pesimista (b = ${b}). Corrija el orden 0 ≤ a ≤ m ≤ b.`,
        message: `El valor más probable (${m}) supera al pesimista (${b}). Corrija el orden para poder calcular la estimación PERT.`,
      })
      return
    }
    if (a > b) {
      setPertEstimate(null)
      setPertError({
        field: 'pessimistic_duration',
        reason: `Orden inválido: la duración optimista (a = ${a}) no puede ser mayor que la duración pesimista (b = ${b}). Corrija el orden 0 ≤ a ≤ m ≤ b.`,
        message: `El valor optimista (${a}) supera al pesimista (${b}). Corrija el orden para poder calcular la estimación PERT.`,
      })
      return
    }

    setBusy('pert')
    setPertError(null)
    try {
      const res = await registerPertEstimate(projectId, {
        project_version_id: project?.project_version_id,
        optimistic_duration: a,
        most_likely_duration: m,
        pessimistic_duration: b,
        time_unit: pertTimeUnit,
      })
      setPertEstimate(res)
      setPertSuccess('Estimación PERT calculada y registrada correctamente para la versión del expediente.')
    } catch (err: any) {
      setPertEstimate(null)
      setPertError({
        field: err.field,
        reason: err.reason || err.detail,
        message: err.detail || err.message || 'No se pudo calcular la estimación PERT.',
      })
    } finally {
      setBusy(null)
    }
  }

  useEffect(() => {
    void loadProject()
    void loadApproval()
    void loadCheckpoint()
    void loadSocialAssessment()
    void loadEnvironmentalAssessment()
    void loadPertEstimate()
  }, [loadProject, loadApproval, loadCheckpoint, loadSocialAssessment, loadEnvironmentalAssessment, loadPertEstimate])

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
      if (ev.status === 'completed' || ev.status === 'failed' || ev.status === 'pending_review') {
        await loadCheckpoint()
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
      if (accepted.status === 'pending_review' || accepted.checkpoint) {
        setInfo(
          'Procesamiento detenido en punto de control: se detectó riesgo alto configurado para revisión humana (HU3.1).',
        )
        if (accepted.checkpoint) setCheckpoint(accepted.checkpoint)
        await loadProject()
        await loadApproval()
        await loadCheckpoint()
        return
      }
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
      await loadProject()
      await loadApproval()
      await loadCheckpoint()
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

  // HU3.2: Garantizar aislamiento estricto por versión del expediente.
  // Un punto de control de una versión anterior u obsoleta no debe presentarse como activo en la versión vigente.
  const rawCheckpoint = checkpoint ?? project?.checkpoint ?? approval?.checkpoint ?? null
  const activeCheckpoint =
    rawCheckpoint && project && rawCheckpoint.project_version_id === project.project_version_id
      ? rawCheckpoint
      : null

  // HU3.1 / HU3.2: El aviso de pausa aplica ÚNICAMENTE si la versión vigente posee un punto de control
  // activo en estado 'pending_review' correspondiente a esa versión.
  const isPaused = Boolean(
    activeCheckpoint &&
      activeCheckpoint.status === 'pending_review' &&
      project &&
      activeCheckpoint.project_version_id === project.project_version_id
  )

  // HU3.2 CA01: Extraer la causa técnica específica y la observación para revisión humana.
  // Si los datos están incompletos, indicarlo con claridad sin inventar explicaciones.
  const pauseCause =
    (typeof activeCheckpoint?.cause === 'string' && activeCheckpoint.cause.trim()) ||
    (typeof activeCheckpoint?.reason === 'string' && activeCheckpoint.reason.trim()) ||
    (typeof activeCheckpoint?.details?.cause === 'string' && activeCheckpoint.details.cause.trim()) ||
    (typeof approval?.pause_reason === 'string' && approval.pause_reason.trim()) ||
    null

  const rawObservation =
    (typeof activeCheckpoint?.observation === 'string' && activeCheckpoint.observation.trim()) ||
    (typeof activeCheckpoint?.details?.observation === 'string' &&
      activeCheckpoint.details.observation.trim()) ||
    (typeof activeCheckpoint?.details?.risk_observation === 'string' &&
      activeCheckpoint.details.risk_observation.trim()) ||
    (typeof activeCheckpoint?.details?.declared_vs_evidence === 'object' &&
    activeCheckpoint.details.declared_vs_evidence !== null &&
    'verifiable_evidence' in activeCheckpoint.details.declared_vs_evidence &&
    typeof (activeCheckpoint.details.declared_vs_evidence as Record<string, unknown>).verifiable_evidence === 'string'
      ? ((activeCheckpoint.details.declared_vs_evidence as Record<string, unknown>).verifiable_evidence as string).trim()
      : null) ||
    null

  const pauseObservation =
    rawObservation && rawObservation !== pauseCause && rawObservation !== 'Observación pendiente de aclaración'
      ? rawObservation
      : null

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

          {isPaused && (
            <section
              className="checkpoint-pause-banner"
              aria-label="Aviso gerencial de punto de control de riesgo"
              data-testid="checkpoint-pause-banner"
            >
              <div className="checkpoint-pause-header">
                <h3 className="checkpoint-pause-title">
                  <span aria-hidden="true">⚠️</span> Punto de control activo · Evaluación pausada por riesgo alto
                </h3>
                <span className="checkpoint-badge">
                  Pendiente de revisión
                </span>
              </div>

              <div className="checkpoint-target-bar">
                <strong>Expediente afectado:</strong>{' '}
                <span>
                  {project?.code} (Versión {project?.version_number}) · {project?.title}
                </span>
              </div>

              <div className="checkpoint-boxes-grid">
                <div className="checkpoint-cause-box">
                  <div className="checkpoint-reason-title">
                    Causa técnica específica de la pausa (HU3.2 · CA01)
                  </div>
                  <p className="checkpoint-reason-text">
                    {pauseCause ? (
                      pauseCause
                    ) : (
                      <span className="checkpoint-incomplete-warning">
                        Información incompleta: La causa técnica específica de la pausa no se encuentra registrada en el punto de control. Requiere aclaración por el equipo técnico. Se conserva el estado pendiente de revisión.
                      </span>
                    )}
                  </p>
                </div>

                <div className="checkpoint-observation-box">
                  <div className="checkpoint-observation-title">
                    Observación concreta para revisión humana (HU3.2 · CA01)
                  </div>
                  <p className="checkpoint-observation-text">
                    {pauseObservation ? (
                      pauseObservation
                    ) : (
                      <span className="checkpoint-incomplete-warning">
                        Observación pendiente de aclaración: Se requiere comprobación técnica en campo y sustento formal de mitigaciones aprobadas.
                      </span>
                    )}
                  </p>
                </div>
              </div>

              <div className="checkpoint-meta-grid">
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Expediente y versión</div>
                  <div className="checkpoint-meta-value">
                    {project?.code} (v{project?.version_number})
                  </div>
                </div>
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Estado de procesamiento</div>
                  <div className="checkpoint-meta-value" style={{ color: '#b91c1c', fontWeight: 700 }}>
                    Pendiente de revisión
                  </div>
                </div>
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Origen de detección</div>
                  <div className="checkpoint-meta-value">
                    {activeCheckpoint?.risk_source_label ?? 'Impacto ambiental territorial (Recurso hídrico / Ecosistema)'}
                  </div>
                </div>
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Nivel de riesgo</div>
                  <div className="checkpoint-meta-value" style={{ color: '#dc2626', fontWeight: 700 }}>
                    {activeCheckpoint?.risk_level_label ?? 'Riesgo Alto'}
                  </div>
                </div>
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Fecha del punto de control</div>
                  <div className="checkpoint-meta-value">
                    {activeCheckpoint?.created_at ? formatDate(activeCheckpoint.created_at) : 'Fecha no registrada'}
                  </div>
                </div>
                <div className="checkpoint-meta-item">
                  <div className="checkpoint-meta-label">Acción requerida</div>
                  <div className="checkpoint-meta-value" style={{ color: '#9a3412', fontWeight: 600 }}>
                    Revisión humana obligatoria (Gerente de Planeamiento)
                  </div>
                </div>
              </div>

              <div className="checkpoint-footer-container">
                <p className="checkpoint-footer-notice">
                  <strong>Control gerencial (CA-HU3.2-01 / CA-HU3.2-02):</strong> El procesamiento automático ha sido detenido en este punto de control persistente. La evaluación no concluye ni se da por aprobada, y no habrá continuación automática. Mientras la causa no sea resuelta mediante validación humana facultada, este aviso y el estado pendiente permanecerán disponibles al recargar, reingresar o consultar nuevamente el expediente, sin repetir la evaluación ni crear puntos de control duplicados.
                </p>
              </div>
            </section>
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
            {isPaused && (
              <div className="checkpoint-blocked-alert" style={{ marginBottom: '1rem' }}>
                <strong>Punto de control activo:</strong> La evaluación técnica de este expediente se encuentra detenida en estado <strong>Pendiente de revisión</strong> por detección de riesgo alto (HU3.1). No se continuará automáticamente hacia la finalización ni se emitirá puntaje final sin revisión humana previa.
              </div>
            )}
            <p className="flow-hint">Disponible cuando el expediente esté completo.</p>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy !== null || !project?.project_version_id || isPaused}
              onClick={() => void runEvaluation()}
            >
              {busy === 'evaluation'
                ? 'Procesando…'
                : isPaused
                  ? 'Evaluación en pausa por riesgo'
                  : 'Solicitar evaluación'}
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


          {/* PMV 2 · HU1.9: Estimación de duración de obra e incertidumbre (PERT) */}
          <section className="flow-panel pert-flow-panel" aria-label="Estimación PERT e incertidumbre de plazos">
            <div className="flow-panel-heading">
              <div>
                <span className="story-label">PMV 2 · HU1.9</span>
                <h2>Estimación de duración de obra e incertidumbre (PERT)</h2>
              </div>
              <span className="review-badge">Planificación y Plazos</span>
            </div>
            <p className="flow-hint">
              Registre las tres duraciones de la obra en la misma unidad de tiempo para estimar la duración esperada bajo incertidumbre con la distribución PERT (0 ≤ a ≤ m ≤ b).
            </p>

            {hasRole('PLANNER') && (
              <div className="pert-inputs-container">
                <div className="pert-inputs-grid">
                  <div className="pert-input-field">
                    <label htmlFor="pert-unit">
                      <span>Unidad de tiempo</span>
                      <span className="pert-unit-tag">unidad</span>
                    </label>
                    <select
                      id="pert-unit"
                      className="form-field-input"
                      value={pertTimeUnit}
                      onChange={(e) => {
                      setPertTimeUnit(e.target.value)
                      setPertEstimate(null)
                      setPertSuccess(null)
                      setPertError(null)
                    }}
                    >
                      <option value="meses">Meses</option>
                      <option value="días">Días</option>
                      <option value="semanas">Semanas</option>
                    </select>
                  </div>

                  <div className="pert-input-field">
                    <label htmlFor="pert-opt">
                      <span>Duración optimista (a)</span>
                      <span className="pert-unit-tag">{pertTimeUnit}</span>
                    </label>
                    <input
                      id="pert-opt"
                      type="number"
                      step="any"
                      min="0"
                      className="form-field-input"
                      placeholder={`Ej. 4.0 (${pertTimeUnit})`}
                      value={pertInputA}
                      onChange={(e) => {
                        setPertInputA(e.target.value)
                        setPertEstimate(null)
                        setPertSuccess(null)
                        setPertError(null)
                      }}
                    />
                  </div>

                  <div className="pert-input-field">
                    <label htmlFor="pert-likely">
                      <span>Duración más probable (m)</span>
                      <span className="pert-unit-tag">{pertTimeUnit}</span>
                    </label>
                    <input
                      id="pert-likely"
                      type="number"
                      step="any"
                      min="0"
                      className="form-field-input"
                      placeholder={`Ej. 6.0 (${pertTimeUnit})`}
                      value={pertInputM}
                      onChange={(e) => {
                        setPertInputM(e.target.value)
                        setPertEstimate(null)
                        setPertSuccess(null)
                        setPertError(null)
                      }}
                    />
                  </div>

                  <div className="pert-input-field">
                    <label htmlFor="pert-pess">
                      <span>Duración pesimista (b)</span>
                      <span className="pert-unit-tag">{pertTimeUnit}</span>
                    </label>
                    <input
                      id="pert-pess"
                      type="number"
                      step="any"
                      min="0"
                      className="form-field-input"
                      placeholder={`Ej. 10.0 (${pertTimeUnit})`}
                      value={pertInputB}
                      onChange={(e) => {
                        setPertInputB(e.target.value)
                        setPertEstimate(null)
                        setPertSuccess(null)
                        setPertError(null)
                      }}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy !== null}
                    onClick={() => void handleCalculatePert()}
                  >
                    {busy === 'pert' ? 'Calculando y guardando…' : 'Calcular y registrar estimación PERT'}
                  </button>
                </div>
              </div>
            )}

            {pertError && (
              <div className="pert-error-banner" role="alert">
                <div className="pert-error-header">
                  <span>⚠️</span>
                  <span>Error de validación en estimaciones de plazo (HU1.9)</span>
                </div>
                <div className="pert-error-detail">
                  {pertError.field && (
                    <strong>
                      Campo a corregir:{' '}
                      {pertError.field === 'optimistic_duration'
                        ? 'Duración optimista (a)'
                        : pertError.field === 'most_likely_duration'
                          ? 'Duración más probable (m)'
                          : pertError.field === 'pessimistic_duration'
                            ? 'Duración pesimista (b)'
                            : pertError.field}
                      .
                    </strong>
                  )}{' '}
                  {pertError.reason || pertError.message}
                </div>
                <div className="pert-error-advice">
                  Requisito: Los tres valores deben estar completos, ser finitos y cumplir estrictamente 0 ≤ a ≤ m ≤ b.
                </div>
              </div>
            )}

            {pertSuccess && (
              <div className="pert-success-alert">
                <Alert variant="success">{pertSuccess}</Alert>
              </div>
            )}

            {pertEstimate && !pertError && (
              <div className="pert-result-container">
                {/* Aviso obligatorio de estimación no garantizada */}
                <div className="pert-disclaimer-callout" role="note">
                  <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>ℹ️</span>
                  <div>
                    <strong>AVISO OBLIGATORIO · ESTIMACIÓN REFERENCIAL, NO PLAZO GARANTIZADO</strong>
                    <p>{pertEstimate.disclaimer}</p>
                  </div>
                </div>

                {/* Resumen de magnitudes clave */}
                <div className="pert-metrics-grid">
                  <div className="pert-metric-card highlight">
                    <div className="pert-metric-label">Duración esperada PERT (μ)</div>
                    <div className="pert-metric-value-row">
                      <span className="pert-metric-num">{Number(pertEstimate.expected_duration).toFixed(2)}</span>
                      <span className="pert-metric-unit">{pertEstimate.time_unit}</span>
                    </div>
                    <div className="pert-metric-sub">Fórmula: (a + 4m + b) / 6</div>
                  </div>

                  <div className="pert-metric-card">
                    <div className="pert-metric-label">Incertidumbre / Desv. estándar (σ)</div>
                    <div className="pert-metric-value-row">
                      <span className="pert-metric-num">± {Number(pertEstimate.standard_deviation).toFixed(2)}</span>
                      <span className="pert-metric-unit">{pertEstimate.time_unit}</span>
                    </div>
                    <div className="pert-metric-sub">Incertidumbre PERT: (b - a) / 6 (No es margen garantizado)</div>
                  </div>

                  <div className="pert-metric-card">
                    <div className="pert-metric-label">Varianza del plazo (σ²)</div>
                    <div className="pert-metric-value-row">
                      <span className="pert-metric-num">{Number(pertEstimate.variance).toFixed(4)}</span>
                      <span className="pert-metric-unit">{pertEstimate.time_unit}²</span>
                    </div>
                    <div className="pert-metric-sub">Variabilidad cuadrática: ((b - a) / 6)²</div>
                  </div>
                </div>

                {/* Desglose de parámetros y fórmula aplicada */}
                <div className="pert-details-panel">
                  <h4>Desglose de estimaciones ingresadas y fórmula aplicada</h4>
                  <div className="pert-params-row">
                    <div className="pert-param-item">
                      <span className="pert-param-k">Optimista (a)</span>
                      <span className="pert-param-v">
                        {Number(pertEstimate.optimistic_duration).toFixed(2)} {pertEstimate.time_unit}
                      </span>
                    </div>
                    <div className="pert-param-item">
                      <span className="pert-param-k">Más probable (m)</span>
                      <span className="pert-param-v">
                        {Number(pertEstimate.most_likely_duration).toFixed(2)} {pertEstimate.time_unit}
                      </span>
                    </div>
                    <div className="pert-param-item">
                      <span className="pert-param-k">Pesimista (b)</span>
                      <span className="pert-param-v">
                        {Number(pertEstimate.pessimistic_duration).toFixed(2)} {pertEstimate.time_unit}
                      </span>
                    </div>
                    <div className="pert-param-item">
                      <span className="pert-param-k">Dispersión (b - a)</span>
                      <span className="pert-param-v">
                        {(Number(pertEstimate.pessimistic_duration) - Number(pertEstimate.optimistic_duration)).toFixed(2)}{' '}
                        {pertEstimate.time_unit}
                      </span>
                    </div>
                    <div className="pert-param-item">
                      <span className="pert-param-k">Rango de estimaciones [a, b]</span>
                      <span className="pert-param-v">
                        [{Number(pertEstimate.optimistic_duration).toFixed(2)}, {Number(pertEstimate.pessimistic_duration).toFixed(2)}]{' '}
                        {pertEstimate.time_unit}
                      </span>
                    </div>
                    <div className="pert-param-item">
                      <span className="pert-param-k">Rango esperado (μ ± σ)</span>
                      <span className="pert-param-v">
                        [{Number(pertEstimate.confidence_interval_low).toFixed(2)},{' '}
                        {Number(pertEstimate.confidence_interval_high).toFixed(2)}] {pertEstimate.time_unit}
                      </span>
                    </div>
                  </div>

                  <div className="pert-formula-box">
                    <strong>Fórmula aplicada: </strong>
                    {pertEstimate.formula_applied}
                  </div>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: '#475569', lineHeight: 1.4 }}>
                    <strong>Explicación: </strong>
                    {pertEstimate.explanation}
                  </p>
                </div>

                <TechnicalDetails data={pertEstimate} />
              </div>
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
            {isPaused && (
              <div className="checkpoint-blocked-alert" style={{ marginBottom: '1rem' }}>
                <strong>Aprobación final bloqueada:</strong> El expediente se encuentra en estado <strong>Pendiente de revisión</strong> por punto de control persistente ante riesgo alto (HU3.1). Conforme a las reglas de control, no se permite emitir un dictamen final de aprobación hasta que la revisión humana sea resuelta.
              </div>
            )}
            <ul className="flow-links">
              {hasRole('LEGAL_ADVISOR') && (
                <li>
                  <Link to="/normativa">Consultar normativa aplicable</Link>
                </li>
              )}
              {hasRole('ADMIN') && !isPaused && (
                <li>
                  <Link to={`/proyectos/${projectId}/aprobacion`}>
                    Emitir dictamen de aprobación
                  </Link>
                </li>
              )}
              {hasRole('ADMIN') && isPaused && (
                <li className="muted">
                  Emisión de dictamen deshabilitada: expediente detenido en punto de control por riesgo alto.
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
