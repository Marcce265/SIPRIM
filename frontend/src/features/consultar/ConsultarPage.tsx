import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ExpedienteCodeBadge } from '../../components/proyecto/ExpedienteCodeBadge'
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
        description="Busque por código de expediente (EXP-…) generado al registrar, o por UUID técnico."
      />

      <form className="lookup-form" onSubmit={onSubmit}>
        <label className="form-field">
          <span className="form-field-label">Código o UUID del expediente</span>
          <div className="lookup-row">
            <input
              className="form-field-input"
              type="text"
              value={inputId}
              onChange={(e) => setInputId(e.target.value)}
              placeholder="Ej. EXP-K7M2P9"
              spellCheck={false}
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
          {proyecto.codigo && (
            <ExpedienteCodeBadge code={proyecto.codigo} projectId={proyecto.id} compact />
          )}
          <ProyectoCard proyecto={proyecto} />
          <div className="next-steps">
            <h2>Flujo principal</h2>
            <p>
              Desde el detalle puede validar, encolar evaluación económica, ejecutar prechecks y
              (según rol) normativa RAG o aprobación humana.
            </p>
            <Link to={`/proyectos/${proyecto.id}`} className="btn btn-primary">
              Continuar evaluación
            </Link>
          </div>
        </section>
      )}
    </div>
  )
}
