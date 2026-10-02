import { useState } from 'react'
import { apiFetch } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'

interface DictamenIA {
  puntaje: number
  viabilidad: 'ALTA' | 'MEDIA' | 'BAJA'
  justificacion: string
  observaciones: string[]
  recomendaciones: string[]
}

export function GeminiIntegrationPage() {
  const [rawId, setRawId] = useState('')
  const [dictamen, setDictamen] = useState<DictamenIA | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const evaluar = async () => {
    const id = Number(rawId)
    if (!Number.isSafeInteger(id) || id <= 0) {
      setError('Ingrese el ID numérico de un expediente registrado en el backend.')
      return
    }
    setLoading(true)
    setError(null)
    setDictamen(null)
    try {
      const result = await apiFetch<DictamenIA>(`/api/v1/proyectos/${id}/evaluacion-ia`, {
        method: 'POST',
        timeoutMs: 60_000,
      })
      setDictamen(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo completar la evaluación.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="form-page">
      <PageHeader
        title="Integración experimental con Gemini"
        description="Use un expediente creado en el backend FastAPI. Los proyectos del modo demostración se guardan en este navegador y no comparten identificadores."
      />
      <section className="ia-panel">
        <label className="form-field" htmlFor="gemini-project-id">
          <span className="form-field-label">ID numérico del expediente en el backend</span>
        </label>
        <div className="lookup-row">
          <input
            id="gemini-project-id"
            className="form-field-input"
            type="number"
            min="1"
            step="1"
            value={rawId}
            onChange={(event) => setRawId(event.target.value)}
            placeholder="Ej. 1"
          />
          <button className="btn btn-primary" type="button" disabled={loading} onClick={() => void evaluar()}>
            {loading ? 'Evaluando…' : 'Evaluar con IA'}
          </button>
        </div>
        {loading && <p role="status">Consultando Gemini desde el backend…</p>}
        {error && <p role="alert" className="ia-error">{error}</p>}
        {dictamen && (
          <div className="ia-dictamen" aria-live="polite">
            <h2>Dictamen preliminar</h2>
            <p><strong>{dictamen.puntaje.toFixed(1)} / 100</strong> · Viabilidad {dictamen.viabilidad}</p>
            <h3>Justificación</h3>
            <p>{dictamen.justificacion}</p>
            <h3>Observaciones</h3>
            <ul>{dictamen.observaciones.map((item, index) => <li key={index}>{item}</li>)}</ul>
            <h3>Recomendaciones</h3>
            <ul>{dictamen.recomendaciones.map((item, index) => <li key={index}>{item}</li>)}</ul>
            <p>Resultado orientativo. Requiere revisión humana y no constituye aprobación municipal.</p>
          </div>
        )}
      </section>
    </div>
  )
}
