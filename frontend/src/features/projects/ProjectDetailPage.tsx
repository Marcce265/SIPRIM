import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { EconomicResultPanel } from '../../components/evaluation/EconomicResultPanel'
import { StatusBadge } from '../../components/evaluation/StatusBadge'
import { Alert } from '../../components/ui/Alert'
import { simulationRepository } from '../../simulation/repository'
import { useSimulation } from '../../simulation/useSimulation'
import { formatCurrency, formatDate, formatNumber } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'

export function ProjectDetailPage() {
  const { projectId = '' } = useParams()
  const location = useLocation()
  const { state } = useSimulation()
  const { user } = useAuth()
  const [message, setMessage] = useState<string | null>(
    (location.state as { mensaje?: string } | null)?.mensaje ?? null,
  )
  const [error, setError] = useState<string | null>(null)

  const project = state.projects.find((item) => item.id === projectId)
  const version = project
    ? state.projectVersions.find((item) => item.id === project.versionActualId)
    : undefined
  const versions = state.projectVersions
    .filter((item) => item.proyectoId === projectId)
    .sort((a, b) => b.numero - a.numero)
  const evaluations = state.evaluations
    .filter((item) => item.proyectoId === projectId)
    .sort((a, b) => b.fechaSolicitud.localeCompare(a.fechaSolicitud))
  const inProgress = evaluations.some(
    (item) => item.estado === 'pendiente' || item.estado === 'procesando',
  )

  if (!project || !version) {
    return (
      <section className="empty-state">
        <h1>Proyecto no encontrado</h1>
        <Link to="/proyectos" className="btn btn-secondary">Volver al listado</Link>
      </section>
    )
  }

  const requestEvaluation = (simulateFailure = false) => {
    setError(null)
    setMessage(null)
    try {
      if (!user) throw new Error('Sesión no disponible.')
      simulationRepository.requestEvaluation(project.id, user, { simulateFailure })
      setMessage(
        simulateFailure
          ? 'Se inició un fallo controlado para demostrar el estado y el reintento.'
          : 'Evaluación iniciada. Observe el cambio de pendiente a procesando y completado.',
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo iniciar la evaluación.')
    }
  }

  return (
    <div className="wide-page detail-stack">
      <nav className="breadcrumb" aria-label="Migas de pan">
        <Link to="/proyectos">Proyectos</Link><span>/</span><span>{project.codigo}</span>
      </nav>

      {message && <Alert variant="success">{message}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      <section className="detail-card">
        <header className="detail-header">
          <div>
            <p className="eyebrow">{project.codigo} · Versión {version.numero}</p>
            <h1>{version.nombre}</h1>
          </div>
          <StatusBadge status={project.estado} />
        </header>
        <p className="detail-description">{version.descripcion}</p>
        <dl className="summary-grid">
          <div><dt>Presupuesto</dt><dd>{formatCurrency(version.presupuesto)}</dd></div>
          <div><dt>Beneficiarios</dt><dd>{formatNumber(version.beneficiarios)}</dd></div>
          <div><dt>Versión actual</dt><dd>v{version.numero}</dd></div>
          <div><dt>Actualizado</dt><dd>{formatDate(project.fechaActualizacion)}</dd></div>
        </dl>
        {user?.roles.includes('PLANNER') && (
          <div className="detail-actions">
            <Link to={`/proyectos/${project.id}/editar`} className="btn btn-secondary">
              Editar proyecto
            </Link>
            <button
              type="button"
              className="btn btn-primary"
              disabled={inProgress}
              onClick={() => requestEvaluation(false)}
            >
              {evaluations.length > 0 ? 'Repetir evaluación' : 'Iniciar evaluación'}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={inProgress}
              onClick={() => requestEvaluation(true)}
            >
              Simular fallo técnico
            </button>
          </div>
        )}
        {user?.roles.includes('ADMIN') && (
          <p className="role-note">Vista de consulta. El perfil Planificador inicia evaluaciones.</p>
        )}
      </section>

      <section>
        <div className="section-heading">
          <div><p className="eyebrow">HU10–HU11</p><h2>Historial económico</h2></div>
          <p>Los resultados conservan las entradas y umbrales usados.</p>
        </div>
        {evaluations.length === 0 ? (
          <div className="empty-inline">Aún no se ha ejecutado una evaluación económica.</div>
        ) : (
          <div className="evaluation-list">
            {evaluations.map((evaluation) => (
              <EconomicResultPanel key={evaluation.id} evaluation={evaluation} />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="section-heading"><div><p className="eyebrow">HU08</p><h2>Versiones del proyecto</h2></div></div>
        <div className="table-shell">
          <table className="data-table">
            <thead><tr><th>Versión</th><th>Nombre</th><th>Presupuesto</th><th>Beneficiarios</th><th>Creada</th></tr></thead>
            <tbody>
              {versions.map((item) => (
                <tr key={item.id}>
                  <td><strong>v{item.numero}</strong>{item.id === version.id && <span className="current-label">Actual</span>}</td>
                  <td>{item.nombre}</td>
                  <td>{formatCurrency(item.presupuesto)}</td>
                  <td>{formatNumber(item.beneficiarios)}</td>
                  <td>{formatDate(item.fechaCreacion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
