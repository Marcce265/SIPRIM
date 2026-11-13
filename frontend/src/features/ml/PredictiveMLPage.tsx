import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { resolveProject } from '../../api/pmv1.api'
import { getLatestML, getMLMetadata, predictWithML } from '../../api/predictiveMl.api'
import type { MLMetadata, MLPrediction } from '../../api/predictiveMl.api'
import type { PMV1ProjectResponse } from '../../types/pmv1'
import { PageHeader } from '../../components/ui/PageHeader'
import { Alert } from '../../components/ui/Alert'
import '../../styles/predictive-ml.css'

const categoryFields = [
  ['FUNCION', 'Función de la inversión'],
  ['DEPARTAMENTO', 'Departamento'],
  ['DES_MODALIDAD', 'Modalidad de ejecución'],
  ['TIPO_INVERSION', 'Tipo de inversión'],
] as const
const percent = (x: number) => `${(x * 100).toFixed(2)} %`
const errorText = (e: unknown) => e instanceof Error ? e.message : 'No se pudo completar la operación.'

export function PredictiveMLPage() {
  const [params] = useSearchParams()
  const [reference, setReference] = useState(params.get('project') ?? '')
  const [metadata, setMetadata] = useState<MLMetadata | null>(null)
  const [project, setProject] = useState<PMV1ProjectResponse | null>(null)
  const [result, setResult] = useState<MLPrediction | null>(null)
  const [categories, setCategories] = useState<Record<string, string>>({})
  const [days, setDays] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getMLMetadata().then(value => { if (active) setMetadata(value) }).catch(e => { if (active) setError(errorText(e)) })
    return () => { active = false }
  }, [])

  async function lookup(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setProject(null); setResult(null); setCategories({}); setDays('')
    try {
      const value = await resolveProject(reference.trim())
      const previous = await getLatestML(value.project_id)
      setProject(value)
      if (previous) { setResult(previous); setCategories(previous.categories); setDays(previous.planned_days?.toString() ?? '') }
    } catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }

  async function run(event: FormEvent) {
    event.preventDefault()
    if (!project) return
    setBusy(true); setError(''); setResult(null)
    try {
      setResult(await predictWithML(project.project_id, {
        project_version_id: project.project_version_id,
        function: categories.FUNCION, department: categories.DEPARTAMENTO,
        execution_mode: categories.DES_MODALIDAD, investment_type: categories.TIPO_INVERSION,
        planned_days: days ? Number(days) : null,
      }))
    } catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }

  const changed = () => setResult(null)
  return <div className="form-page ml-page">
    <PageHeader title="Predicciones con ML" description="Evaluación vinculada a expedientes registrados: liquidación frente al monto viable y duración de ejecución física." />
    {error && <Alert variant="error">{error}</Alert>}
    {!metadata && !error && <p role="status">Cargando el modelo y su información de validación…</p>}
    {metadata && <>
      <section className="ml-panel">
        <h2>1. Consultar un expediente</h2>
        <form className="lookup-form" onSubmit={lookup}>
          <label className="form-field"><span className="form-field-label">Código o UUID del expediente</span>
            <div className="lookup-row"><input className="form-field-input" value={reference} required disabled={busy} placeholder="Código EXP-… o UUID" onChange={e => { setReference(e.target.value); setProject(null); setResult(null) }} />
              <button className="btn btn-primary" disabled={busy || !reference.trim()}>Consultar expediente</button></div>
          </label>
        </form>
        {project && <div className="ml-project"><strong>{project.code} · {project.title}</strong><p>Versión {project.version_number} · Presupuesto registrado: <strong>{Number(project.estimated_budget_pen).toLocaleString('es-PE', { style: 'currency', currency: 'PEN' })}</strong></p><Link to={`/proyectos/${project.project_id}`}>Ver expediente</Link></div>}
      </section>
      {project && <section className="ml-panel">
        <h2>2. Completar los datos de predicción</h2>
        <p>El presupuesto se obtiene del expediente. Confirme estos datos adicionales según su documentación; se conservarán junto con la predicción.</p>
        <form onSubmit={run}>
          <fieldset disabled={busy} className="ml-fields">
            {categoryFields.map(([key, label]) => <label className="form-field" key={key}><span className="form-field-label">{label}</span>
              <select className="form-field-input" required value={categories[key] ?? ''} onChange={e => { setCategories(current => ({ ...current, [key]: e.target.value })); changed() }}><option value="">Seleccione según el expediente</option>{metadata.categories[key].map(value => <option key={value} value={value}>{value}</option>)}</select>
            </label>)}
            <label className="form-field"><span className="form-field-label">Plazo programado en días (opcional)</span><input className="form-field-input" type="number" min="1" max="3650" step="1" value={days} onChange={e => { setDays(e.target.value); changed() }} /></label>
          </fieldset>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Procesando…' : 'Ejecutar predicción ML'}</button>
        </form>
      </section>}
      {result && <section className="ml-panel" aria-live="polite">
        <h2>Resultado guardado</h2>
        <p>Expediente {result.project_code} · {new Date(result.created_at).toLocaleString('es-PE')} · Modelo {result.model_version}</p>
        <div className="ml-result-grid">
          <article className="ml-result"><h3>Liquidación superior al monto viable en más de 10 %</h3><p className="ml-number">{percent(result.cost_probability)}</p><p>Probabilidad estimada por Random Forest. No representa un porcentaje de sobrecosto ni una aprobación.</p><p className="ml-caution">Señal exploratoria: revise el rendimiento frente a la referencia en la sección de validación.</p></article>
          <article className="ml-result"><h3>Duración física estimada</h3><p className="ml-number">{Math.round(result.estimated_duration_days)} días</p><p>Estimación de Gradient Boosting a partir de duraciones registradas.</p>{result.difference_days !== null && <p>Comparación con los {result.planned_days} días ingresados: <strong>{result.difference_days > 0 ? '+' : ''}{Math.round(result.difference_days)} días</strong>. Esta diferencia no es una probabilidad de retraso.</p>}</article>
        </div>
        <details><summary>Ver respuesta y trazabilidad</summary><pre className="ml-json">{JSON.stringify(result, null, 2)}</pre></details>
      </section>}
      <section className="ml-panel">
        <h2>Datos reales y validación</h2>
        <p><a href={metadata.source_url} target="_blank" rel="noreferrer">Fuente oficial: inversiones cerradas del MEF</a>. {metadata.eligible_rows.toLocaleString('es-PE')} registros elegibles; {metadata.train_rows.toLocaleString('es-PE')} de entrenamiento y {metadata.test_rows.toLocaleString('es-PE')} de evaluación temporal desde {metadata.test_from_year}.</p>
        <div className="ml-table-scroll"><table className="ml-table"><caption>Resultados sobre registros reservados; no son garantías para un proyecto individual</caption><thead><tr><th>Indicador</th><th>Modelo</th><th>Referencia</th></tr></thead><tbody>
          <tr><td>Exactitud · liquidación</td><td>{percent(metadata.metrics.cost.accuracy)}</td><td>{percent(metadata.metrics.cost.baseline_accuracy)} · clase mayoritaria</td></tr>
          <tr><td>AUC ROC · liquidación</td><td>{metadata.metrics.cost.roc_auc.toFixed(3)}</td><td>0,500 · sin discriminación</td></tr>
          <tr><td>Error absoluto medio · duración</td><td>{metadata.metrics.duration.mae_days.toFixed(1)} días</td><td>{metadata.metrics.duration.median_baseline_mae_days.toFixed(1)} días · mediana de entrenamiento</td></tr>
        </tbody></table></div>
        {metadata.metrics.cost.accuracy <= metadata.metrics.cost.baseline_accuracy && <p className="ml-caution">El clasificador de liquidación no supera a la clase mayoritaria en exactitud. Su resultado debe interpretarse como exploratorio.</p>}
        <details><summary>Alcance, limitaciones y versión</summary><ul>{metadata.limitations.map(line => <li key={line}>{line}</li>)}</ul><p>Entrenado: {metadata.trained_at}. Modelo: {metadata.model_version}.</p><p className="ml-hash">SHA-256 de la fuente: {metadata.source_sha256}</p></details>
      </section>
    </>}
  </div>
}
