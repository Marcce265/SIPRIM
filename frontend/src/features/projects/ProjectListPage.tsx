import { Link } from 'react-router-dom'
import { StatusBadge } from '../../components/evaluation/StatusBadge'
import { PageHeader } from '../../components/ui/PageHeader'
import { useSimulation } from '../../simulation/useSimulation'
import { formatCurrency, formatDate, formatNumber } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'

export function ProjectListPage() {
  const { state } = useSimulation()
  const { user } = useAuth()

  return (
    <div className="wide-page">
      <div className="page-heading-row">
        <PageHeader
          title="Proyectos"
          description="Expedientes y evaluaciones guardados en este navegador. HU05, HU09–HU11."
        />
        {user?.roles.includes('PLANNER') && (
          <Link to="/proyectos/nuevo" className="btn btn-primary">
            Registrar proyecto
          </Link>
        )}
      </div>

      {state.projects.length === 0 ? (
        <section className="empty-state">
          <h2>No hay proyectos registrados</h2>
          <p>Registre el primer proyecto para ejecutar la comparación económica.</p>
          {user?.roles.includes('PLANNER') && (
            <Link to="/proyectos/nuevo" className="btn btn-primary">
              Registrar proyecto
            </Link>
          )}
        </section>
      ) : (
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>Código y proyecto</th>
                <th>Versión</th>
                <th>Presupuesto</th>
                <th>Beneficiarios</th>
                <th>Estado</th>
                <th>Actualizado</th>
                <th><span className="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {state.projects.map((project) => {
                const version = state.projectVersions.find(
                  (item) => item.id === project.versionActualId,
                )
                if (!version) return null
                return (
                  <tr key={project.id}>
                    <td>
                      <strong>{project.codigo}</strong>
                      <span className="table-primary">{version.nombre}</span>
                    </td>
                    <td>v{version.numero}</td>
                    <td>{formatCurrency(version.presupuesto)}</td>
                    <td>{formatNumber(version.beneficiarios)}</td>
                    <td><StatusBadge status={project.estado} /></td>
                    <td>{formatDate(project.fechaActualizacion)}</td>
                    <td>
                      <Link to={`/proyectos/${project.id}`} className="link-button">
                        Ver detalle
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
