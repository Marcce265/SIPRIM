import { useState } from 'react'
import { evaluateProjectWithIA, resolveProject } from '../../api/pmv1.api'
import { PageHeader } from '../../components/ui/PageHeader'
import { ExpedienteCodeBadge } from '../../components/proyecto/ExpedienteCodeBadge'
import { isValidExpedienteLookup, normalizeExpedienteQuery } from '../../utils/expedienteRef'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'
import type { Proyecto } from '../../types/proyecto'

interface DictamenIA {
  puntaje: number
  viabilidad: 'ALTA' | 'MEDIA' | 'BAJA'
  justificacion: string
  observaciones: string[]
  recomendaciones: string[]
}

export function GeminiIntegrationPage() {
  const [rawRef, setRawRef] = useState('')
  const [proyecto, setProyecto] = useState<Proyecto | null>(null)
  const [dictamen, setDictamen] = useState<DictamenIA | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const evaluar = async () => {
    const query = normalizeExpedienteQuery(rawRef)
    if (!isValidExpedienteLookup(query)) {
      setError('Ingrese el código EXP-… del expediente PMV1 o su UUID.')
      return
    }
    setLoading(true)
    setError(null)
    setDictamen(null)
    setProyecto(null)
    try {
      const project = await resolveProject(query)
      const mapped = mapPmV1ToProyecto(project)
      setProyecto(mapped)
      const result = await evaluateProjectWithIA(project.project_id)
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
        description="Use el mismo código de expediente (EXP-…) o UUID generado al registrar en PMV1."
      />
      <section className="ia-panel">
        <label className="form-field" htmlFor="gemini-project-ref">
          <span className="form-field-label">Código o UUID del expediente PMV1</span>
        </label>
        <div className="lookup-row">
          <input
            id="gemini-project-ref"
            className="form-field-input"
            type="text"
            value={rawRef}
            onChange={(event) => setRawRef(event.target.value)}
            placeholder="Ej. EXP-K7M2P9"
            spellCheck={false}
          />
          <button className="btn btn-primary" type="button" disabled={loading} onClick={() => void evaluar()}>
            {loading ? 'Evaluando…' : 'Evaluar con IA'}
          </button>
        </div>
        {loading && <p role="status">Consultando Gemini desde el backend…</p>}
        {error && <p role="alert" className="ia-error">{error}</p>}
        {proyecto?.codigo && (
          <ExpedienteCodeBadge code={proyecto.codigo} projectId={proyecto.id} compact />
        )}
        {dictamen && (
          <div className="ia-dictamen" aria-live="polite">
            <h2>Dictamen preliminar</h2>
            <p>
              <strong>{dictamen.puntaje.toFixed(1)} / 100</strong> · Viabilidad {dictamen.viabilidad}
            </p>
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
