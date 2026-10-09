import { useState, type FormEvent } from 'react'
import { apiFetch } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'

interface DictamenIA {
  puntaje: number
  viabilidad: 'ALTA' | 'MEDIA' | 'BAJA'
  justificacion: string
  observaciones: string[]
  recomendaciones: string[]
}

interface ProyectoBackend {
  id: number
  nombre: string
  codigo: string
}

interface RegistroResponse {
  proyecto: ProyectoBackend
}

interface ValidacionResponse {
  estado: string
  campos_faltantes: string[]
  mensaje: string
}

const demoServerless = import.meta.env.VITE_IA_DEMO_SERVERLESS === 'true'

export function GeminiIntegrationPage() {
  const [rawId, setRawId] = useState('')
  const [dictamen, setDictamen] = useState<DictamenIA | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [registrando, setRegistrando] = useState(false)
  const [proyecto, setProyecto] = useState<ProyectoBackend | null>(null)
  const [validacion, setValidacion] = useState<ValidacionResponse | null>(null)
  const [form, setForm] = useState({ nombre: '', descripcion: '', ubicacion: '', presupuesto: '', beneficiarios: '', tipo_proyecto: '' })

  const registrar = async (event: FormEvent) => {
    event.preventDefault()
    setRegistrando(true)
    setError(null)
    setDictamen(null)
    setProyecto(null)
    setValidacion(null)
    try {
      const payload = {
          nombre: form.nombre,
          descripcion: form.descripcion,
          ubicacion: form.ubicacion,
          presupuesto: Number(form.presupuesto),
          beneficiarios: Number(form.beneficiarios),
          tipo_proyecto: form.tipo_proyecto,
      }
      if (demoServerless) {
        const resultado = await apiFetch<{ proyecto: ProyectoBackend; validacion: ValidacionResponse; dictamen: DictamenIA }>(
          '/api/v1/proyectos/evaluacion-ia-demo',
          { method: 'POST', body: JSON.stringify(payload), timeoutMs: 60_000 },
        )
        setProyecto(resultado.proyecto)
        setValidacion(resultado.validacion)
        setDictamen(resultado.dictamen)
        setRawId(String(resultado.proyecto.id))
        return
      }
      const registrado = await apiFetch<RegistroResponse>('/api/v1/proyectos', {
        method: 'POST', body: JSON.stringify(payload),
      })
      setProyecto(registrado.proyecto)
      setRawId(String(registrado.proyecto.id))
      const resultado = await apiFetch<ValidacionResponse>(`/api/v1/proyectos/${registrado.proyecto.id}/validar`, { method: 'POST' })
      setValidacion(resultado)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el expediente.')
    } finally {
      setRegistrando(false)
    }
  }

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
        title="Evaluación preliminar con IA"
        description="Registre un expediente municipal, valide sus datos y solicite un dictamen orientativo de Gemini."
      />
      <section className="ia-panel">
        <h2>1. Registrar expediente para evaluación IA</h2>
        <p>Este registro usa el backend. Es independiente de los expedientes locales del modo demostración.</p>
        {demoServerless && <p>Demostración temporal: el expediente y el dictamen se muestran en esta sesión; no se guardan en una base de datos. Las decisiones requieren revisión humana.</p>}
        <form className="ia-register-form" onSubmit={(event) => void registrar(event)}>
          {([
            ['nombre', 'Nombre del proyecto', 'text'],
            ['descripcion', 'Descripción y objetivo', 'text'],
            ['ubicacion', 'Ubicación', 'text'],
            ['presupuesto', 'Presupuesto (S/)', 'number'],
            ['beneficiarios', 'Beneficiarios', 'number'],
            ['tipo_proyecto', 'Tipo de proyecto', 'text'],
          ] as const).map(([name, label, type]) => (
            <label className="form-field" key={name}>
              <span className="form-field-label">{label}</span>
              <input className="form-field-input" type={type} min={type === 'number' ? '1' : undefined} step={name === 'presupuesto' ? '0.01' : undefined} required value={form[name]} onChange={(event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))} />
            </label>
          ))}
          <button className="btn btn-primary" type="submit" disabled={registrando || loading}>{registrando ? (demoServerless ? 'Evaluando con Gemini…' : 'Registrando y validando…') : (demoServerless ? 'Registrar, validar y evaluar con IA' : 'Registrar y validar')}</button>
        </form>
        {proyecto && <p role="status"><strong>Expediente #{proyecto.id} · {proyecto.codigo}</strong> — {proyecto.nombre}</p>}
        {validacion && <p role="status">Validación: <strong>{validacion.estado}</strong>. {validacion.mensaje}</p>}
        {!demoServerless && <><h2>2. Evaluar expediente con Gemini</h2>
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
          <button className="btn btn-primary" type="button" disabled={loading || registrando} onClick={() => void evaluar()}>
            {loading ? 'Evaluando…' : 'Evaluar con IA'}
          </button>
        </div>
        </>}
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
