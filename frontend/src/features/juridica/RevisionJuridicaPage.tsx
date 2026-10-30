import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { evaluateLegalAssessment, getLegalAssessment, getProject } from '../../api/pmv1.api'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { TechnicalDetails } from '../../components/ui/TechnicalDetails'
import type { LegalAssessmentResponse, PMV1ProjectResponse } from '../../types/pmv1'
import { getPhysicalExpediente } from '../../utils/physicalExpedienteStorage'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'

export function RevisionJuridicaPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [assessment, setAssessment] = useState<LegalAssessmentResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then(setProject)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'No se pudo cargar el expediente.')
      })

    getLegalAssessment(projectId)
      .then(setAssessment)
      .catch(() => {
        // No evaluado previamente
      })
  }, [projectId])

  const runReview = async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await evaluateLegalAssessment(projectId)
      setAssessment(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ejecutar la revisión jurídica.')
    } finally {
      setLoading(false)
    }
  }

  const physicalExpediente = projectId ? getPhysicalExpediente(projectId) : null

  return (
    <div className="form-page pmv1-flow">
      <PageHeader
        title="Detalle de revisión jurídica"
        description="Evaluación de conformidad normativa y citas exactas para el Asesor Jurídico (PMV 2 · HU2.2 / HU1.10)."
      />

      {error && <Alert variant="error">{error}</Alert>}
      {!project && !error && <p className="muted">Cargando expediente…</p>}
      {project && <ProyectoCard proyecto={mapPmV1ToProyecto(project)} compact />}

      <section className="flow-panel legal-flow-panel">
        <div className="flow-panel-heading">
          <div>
            <span className="story-label">PMV 2 · HU2.2 / HU1.10</span>
            <h2>Conformidad legal y citas normativas exactas</h2>
          </div>
          <span className="review-badge">Revisión Asesoría Jurídica</span>
        </div>
        <p className="flow-hint">
          Contrasta los antecedentes del expediente con el corpus normativo versionado y cita el artículo o sección exacta aplicable para su cotejo por el Asesor Jurídico, advirtiendo citas no verificables sin fabricar artículos.
        </p>

        <button
          type="button"
          className="btn btn-primary"
          disabled={loading || !project}
          onClick={() => void runReview()}
        >
          {loading
            ? 'Analizando normativa…'
            : assessment
            ? 'Actualizar revisión jurídica'
            : 'Ejecutar revisión jurídica'}
        </button>

        {assessment && (
          <article className="legal-result" aria-live="polite">
            <header className="legal-result-header">
              <div>
                <span className="result-eyebrow">Informe Jurídico Preliminar · HU2.2</span>
                <h3>{assessment.status_label}</h3>
              </div>
              <span
                className={`status-pill ${
                  assessment.status === 'verified'
                    ? 'status-review'
                    : assessment.status === 'requires_review'
                    ? 'status-review'
                    : 'status-review'
                }`}
              >
                {assessment.requires_human_review ? 'Requiere revisión' : 'Cotejo conforme'}
              </span>
            </header>

            <p className="legal-conclusion">{assessment.summary}</p>

            <dl className="legal-checks">
              <div>
                <dt>Antecedentes contractuales</dt>
                <dd>
                  {physicalExpediente
                    ? `${physicalExpediente.fileName} adjunto; contenido para cotejo.`
                    : 'No se adjuntaron antecedentes contractuales físicos o digitalizados.'}
                </dd>
              </div>
              <div>
                <dt>Citas comprobables (CA-HU2.2-01)</dt>
                <dd>
                  {assessment.verifiable_citations_count} cita(s) con artículo exacto y versión.
                </dd>
              </div>
              <div>
                <dt>Citas no verificables (CA-HU2.2-02)</dt>
                <dd>
                  {assessment.unverifiable_citations_count > 0
                    ? `${assessment.unverifiable_citations_count} hallazgo(s) sin cita verificable.`
                    : 'Ninguna (todas comprobables).'}
                </dd>
              </div>
            </dl>

            <section className="legal-findings-section" aria-labelledby="legal-findings-title">
              <h4 id="legal-findings-title" style={{ margin: '1rem 0 0.5rem', color: '#0f172a' }}>
                Hallazgos jurídicos y citas normativas vinculadas
              </h4>

              {assessment.findings.map((finding) => (
                <div
                  key={finding.finding_id}
                  className={`legal-finding-card ${
                    finding.citation.is_verifiable ? 'is-verifiable' : 'is-unverifiable'
                  }`}
                >
                  <div className="legal-finding-header">
                    <div>
                      <h4 className="legal-finding-title">{finding.title}</h4>
                      <p className="legal-finding-desc">{finding.description}</p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
                      <span
                        className={`social-badge-status ${
                          finding.citation.is_verifiable ? 'sufficient' : 'insufficient'
                        }`}
                      >
                        {finding.citation.status_label}
                      </span>
                      {finding.requires_human_review ? (
                        <span className="green-measures-pill pill-warn">
                          ⚠️ Revisión humana obligatoria
                        </span>
                      ) : (
                        <span className="green-measures-pill pill-ok">
                          Cotejo conforme
                        </span>
                      )}
                    </div>
                  </div>

                  {finding.citation.is_verifiable ? (
                    <div className="legal-citation-box">
                      <div className="social-score-tag" style={{ marginBottom: '0.35rem' }}>
                        CA-HU2.2-01 · Cita exacta y comprobable
                      </div>
                      <div style={{ fontSize: '0.86rem', color: '#0f172a', marginBottom: '0.35rem' }}>
                        <strong>Denominación de la norma:</strong> {finding.citation.document_name}
                      </div>
                      <div style={{ fontSize: '0.84rem', color: '#475569', marginBottom: '0.35rem' }}>
                        <strong>Versión de la norma:</strong> {finding.citation.version}
                      </div>
                      <div>
                        <strong>Ubicación precisa:</strong>{' '}
                        <span className="citation-article-badge">
                          {finding.citation.article_or_section}
                        </span>
                      </div>
                      <div style={{ marginTop: '0.5rem' }}>
                        <strong style={{ fontSize: '0.8rem', color: '#475569' }}>
                          Fragmento normativo para cotejo:
                        </strong>
                        <blockquote className="citation-fragment-quote">
                          “{finding.citation.fragment_content}”
                        </blockquote>
                      </div>

                      <div className="citation-meta">
                        <div>
                          <strong>Fuente:</strong> {finding.citation.data_origin}
                          {finding.citation.is_simulated && (
                            <span className="social-simulated-pill">Simulado</span>
                          )}
                        </div>
                        {finding.citation.citation_hash && (
                          <div>
                            <strong>Trazabilidad SHA-256:</strong>{' '}
                            <span className="citation-hash-pill">
                              {finding.citation.citation_hash.slice(0, 16)}…
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="citation-unverifiable-callout">
                      <div style={{ fontWeight: 700, marginBottom: '0.25rem', color: '#b45309' }}>
                        ⚠️ Cita no verificable (CA-HU2.2-02)
                      </div>
                      <p style={{ margin: '0.35rem 0', lineHeight: 1.45 }}>
                        {finding.citation.limitation_note}
                      </p>
                      <div style={{ marginTop: '0.35rem', fontSize: '0.82rem' }}>
                        <strong>Ubicación de artículo:</strong> No identificable (no se fabrica ningún número de artículo)
                      </div>
                      <div style={{ marginTop: '0.25rem', fontSize: '0.82rem' }}>
                        <strong>Referencia documental:</strong>{' '}
                        {finding.citation.document_name || 'No identificada'}{' '}
                        {finding.citation.version ? `(${finding.citation.version})` : ''}
                      </div>
                      {finding.citation.fragment_content && (
                        <div style={{ marginTop: '0.4rem', fontSize: '0.8rem' }}>
                          <strong>Fragmento histórico / referencial:</strong>
                          <blockquote className="citation-fragment-quote" style={{ margin: '0.25rem 0' }}>
                            “{finding.citation.fragment_content}”
                          </blockquote>
                        </div>
                      )}
                      <div style={{ marginTop: '0.5rem', fontWeight: 600, color: '#92400e', fontSize: '0.8rem' }}>
                        Estado del hallazgo: No confirmado jurídicamente · Requiere revisión humana por el Asesor Jurídico
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </section>

            <TechnicalDetails data={assessment} />
          </article>
        )}
      </section>
    </div>
  )
}
