import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getProject, legalPrecheck } from '../../api/pmv1.api'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import type { LegalPrecheckResponse, PMV1ProjectResponse } from '../../types/pmv1'
import { getPhysicalExpediente } from '../../utils/physicalExpedienteStorage'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'

export function RevisionJuridicaPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [result, setResult] = useState<LegalPrecheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then(setProject)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'No se pudo cargar el expediente.')
      })
  }, [projectId])

  const runReview = async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      setResult(await legalPrecheck(projectId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ejecutar la revisión jurídica.')
    } finally {
      setLoading(false)
    }
  }

  const sources = result?.sources ?? []
  const physicalExpediente = projectId ? getPhysicalExpediente(projectId) : null

  return (
    <div className="form-page pmv1-flow">
      <PageHeader
        title="Detalle de revisión jurídica"
        description="Evaluación preliminar de conformidad con contratación pública para PMV1 · HU1.10."
      />

      {error && <Alert variant="error">{error}</Alert>}
      {!project && !error && <p className="muted">Cargando expediente…</p>}
      {project && <ProyectoCard proyecto={mapPmV1ToProyecto(project)} compact />}

      <section className="flow-panel legal-flow-panel">
        <div className="flow-panel-heading">
          <div>
            <span className="story-label">PMV1 · HU1.10</span>
            <h2>Conformidad con contratación pública</h2>
          </div>
          <span className="review-badge">Revisión jurídica</span>
        </div>
        <p className="flow-hint">
          Contrasta los antecedentes del expediente con el sustento normativo disponible,
          sin reemplazar la decisión de Asesoría Jurídica.
        </p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={loading || !project}
          onClick={() => void runReview()}
        >
          {loading ? 'Analizando…' : 'Ejecutar revisión jurídica'}
        </button>

        {result && (
          <article className="legal-result" aria-live="polite">
            <header className="legal-result-header">
              <div>
                <span className="result-eyebrow">Resultado preliminar</span>
                <h3>Conformidad no determinada</h3>
              </div>
              <span className="status-pill status-review">Requiere revisión</span>
            </header>

            <p className="legal-conclusion">
              No se afirma cumplimiento ni incumplimiento definitivo. La decisión debe ser
              validada por un asesor jurídico con antecedentes y fuentes verificables.
            </p>

            <dl className="legal-checks">
              <div>
                <dt>Antecedentes contractuales</dt>
                <dd>
                  {physicalExpediente
                    ? `${physicalExpediente.fileName} adjunto; contenido pendiente de verificación.`
                    : 'No se adjuntaron antecedentes contractuales verificables.'}
                </dd>
              </div>
              <div>
                <dt>Sustento normativo</dt>
                <dd>
                  {sources.length > 0
                    ? `${sources.length} fuente(s) identificada(s) para revisión.`
                    : 'Faltan norma, versión y fragmento verificable.'}
                </dd>
              </div>
              <div>
                <dt>Decisión automática</dt>
                <dd>No emitida · validación humana obligatoria</dd>
              </div>
            </dl>

            <section className="legal-observations" aria-labelledby="legal-observations-title">
              <h4 id="legal-observations-title">Observaciones detectadas</h4>
              <ul>
                {result.observations.map((observation) => (
                  <li key={observation}>{observation}</li>
                ))}
              </ul>
            </section>

            <section className="legal-evidence" aria-labelledby="legal-evidence-title">
              <h4 id="legal-evidence-title">Trazabilidad normativa</h4>
              {sources.length > 0 ? (
                <ul>
                  {sources.map((source) => (
                    <li key={source}>{source}</li>
                  ))}
                </ul>
              ) : (
                <p>
                  No hay una norma, versión y fragmento de sustento vinculados a este
                  resultado. Derive el expediente a Asesoría Jurídica antes de continuar.
                </p>
              )}
            </section>

            <TechnicalDetails data={result} />
          </article>
        )}
      </section>
    </div>
  )
}
