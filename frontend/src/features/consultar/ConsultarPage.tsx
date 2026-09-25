import type { FormEvent } from 'react'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { useConsultarProyecto } from './useConsultarProyecto'

export function ConsultarPage() {
  const { inputId, setInputId, proyecto, successMsg, error, loading, search } =
    useConsultarProyecto()

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    search()
  }

  return (
    <div className="form-page">
      <PageHeader
        title="Consultar expediente"
        description="Busque un proyecto registrado por su identificador. RF-01 · consulta individual."
      />

      <form className="lookup-form" onSubmit={onSubmit}>
        <label className="form-field">
          <span className="form-field-label">ID del expediente</span>
          <div className="lookup-row">
            <input
              className="form-field-input"
              type="number"
              min={1}
              value={inputId}
              onChange={(e) => setInputId(e.target.value)}
              placeholder="Ej. 1"
            />
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Buscando…' : 'Consultar'}
            </button>
          </div>
        </label>
      </form>

      {successMsg && <Alert variant="success">{successMsg}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      {proyecto && (
        <section className="result-section" aria-live="polite">
          <ProyectoCard proyecto={proyecto} />
          <div className="next-steps">
            <h2>Próximos pasos (backend pendiente)</h2>
            <ul>
              <li>Disparo de evaluación por agentes (RF-03 a RF-07)</li>
              <li>Consolidación y ranking de priorización (RF-08, RF-09)</li>
              <li>Panel de expedientes en revisión y validación humana</li>
            </ul>
          </div>
        </section>
      )}
    </div>
  )
}
