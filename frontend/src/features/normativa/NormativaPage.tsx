import { useState, type FormEvent } from 'react'
import { searchNormative } from '../../api/pmv1.api'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import { PageHeader } from '../../components/ui/PageHeader'
import type { NormativeChunkItem, NormativeSearchResponse } from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'

function resolveFallbackLocation(item: NormativeChunkItem): string {
  if (item.location && item.location.trim().length > 0) {
    return item.location.trim()
  }
  const mTopic = item.topic.match(
    /\(([^)]*(?:Art|Título|Titulo|Reglamento|RNE|SINAGERD|Sección|Seccion|Ley DUS|Índice|Indice)[^)]*)\)/i,
  )
  if (mTopic) {
    return mTopic[1].trim()
  }
  const mContent = item.content.match(/^(Art(?:[ií]culo)?\.\s*\d+[^\.\-\:]*)/i)
  if (mContent) {
    return mContent[1].trim()
  }
  return `Fragmento ID ${item.id}`
}

export function NormativaPage() {
  const [query, setQuery] = useState('contrataciones obras municipales')
  const [result, setResult] = useState<NormativeSearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await searchNormative(query.trim(), newIdempotencyKey('norm'))
      setResult(data)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Búsqueda fallida.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="form-page pmv1-flow">
      <PageHeader
        title="Consulta normativa"
        description="Normativa municipal y nacional aplicable a proyectos de inversión."
      />

      <form className="lookup-form" onSubmit={(e) => void onSubmit(e)}>
        {error && <Alert variant="error">{error}</Alert>}
        <FormField
          label="Consulta semántica"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Buscando…' : 'Buscar normativa'}
        </button>
      </form>

      {result && (
        <section className="flow-panel" aria-live="polite">
          <p className="flow-hint">{result.disclaimer}</p>
          {result.alerts_found.length > 0 && (
            <Alert variant="error">Alertas: {result.alerts_found.join(' · ')}</Alert>
          )}

          {result.results.length === 0 ? (
            <div className="norm-empty-notice" role="status">
              <h3>No se encontró sustento normativo suficiente para esta consulta</h3>
              <p>
                El repositorio normativo vigente no contiene fragmentos aplicables para el criterio consultado.
                El sistema no genera normas ni artículos ficticios ante la ausencia de evidencia documental.
              </p>
            </div>
          ) : (
            <ul className="norm-results">
              {result.results.map((item) => {
                const locationDisplay = resolveFallbackLocation(item)
                return (
                  <li key={item.id} className={item.has_alert ? 'norm-hit alert' : 'norm-hit'}>
                    <header className="norm-hit-header">
                      <div className="norm-hit-title-group">
                        <strong className="norm-doc-name">{item.document_name}</strong>
                        <span className="norm-version-tag">Versión: {item.version}</span>
                      </div>
                      <div className="norm-hit-meta">
                        <span className="norm-code-badge">{item.short_code}</span>
                        <span className="norm-score-badge">Relevancia: {item.relevance_score.toFixed(2)}</span>
                      </div>
                    </header>
                    <div className="norm-hit-location-bar">
                      <span className="norm-location-badge">
                        <span className="location-label">Ubicación verificable:</span>{' '}
                        <strong className="location-value">{locationDisplay}</strong>
                      </span>
                      <span className="norm-chunk-id">ID Fragmento: {item.id}</span>
                    </div>
                    <p className="norm-topic">
                      <strong>Materia:</strong> {item.topic}
                    </p>
                    <blockquote className="norm-content">{item.content}</blockquote>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
