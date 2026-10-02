import { useState, type FormEvent } from 'react'
import { searchNormative } from '../../api/pmv1.api'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import { PageHeader } from '../../components/ui/PageHeader'
import type { NormativeSearchResponse } from '../../types/pmv1'
import { newIdempotencyKey } from '../../utils/idempotency'

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
          <ul className="norm-results">
            {result.results.map((item) => (
              <li key={item.id} className={item.has_alert ? 'norm-hit alert' : 'norm-hit'}>
                <header>
                  <strong>{item.document_name}</strong>
                  <span>
                    {item.short_code} · v{item.version} · score {item.relevance_score.toFixed(2)}
                  </span>
                </header>
                <p className="norm-topic">{item.topic}</p>
                <p className="norm-content">{item.content}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
