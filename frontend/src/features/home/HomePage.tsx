import { Link, useLocation } from 'react-router-dom'
import { RoadmapPanel } from '../../components/roadmap/RoadmapPanel'
import { Alert } from '../../components/ui/Alert'
import { useSimulation } from '../../simulation/useSimulation'
import { useAuth } from '../auth/AuthContext'

export function HomePage() {
  const { state } = useSimulation()
  const { user } = useAuth()
  const location = useLocation()
  const completed = state.evaluations.filter((item) => item.estado === 'completado').length

  return (
    <div className="home-layout">
      <section className="hero">
        {(location.state as { restored?: boolean } | null)?.restored && (
          <Alert variant="success">Datos iniciales restaurados correctamente.</Alert>
        )}
        <p className="hero-eyebrow">Taller de Proyectos · Modo demostración</p>
        <h1>Simulación económica de proyectos municipales</h1>
        <p className="hero-lead">
          Registre un proyecto, ejecute el agente económico simulado y reproduzca su
          puntuación. Los datos permanecen en este navegador y no requieren bases, colas ni LLM.
        </p>
        <div className="hero-actions">
          <Link to="/proyectos" className="btn btn-primary">
            Ver proyectos
          </Link>
          {user?.rol === 'PLANNER' && <Link to="/proyectos/nuevo" className="btn btn-secondary">Registrar proyecto</Link>}
          {user?.rol === 'ADMIN' && <Link to="/criterios" className="btn btn-secondary">Administrar criterios</Link>}
        </div>
        <ul className="hero-stats" aria-label="Beneficios clave">
          <li>
            <strong>{state.projects.length} proyectos</strong>
            <span>Con versiones persistentes</span>
          </li>
          <li>
            <strong>{completed} evaluaciones</strong>
            <span>Resultados económicos completos</span>
          </li>
          <li>
            <strong>1 agente simulado</strong>
            <span>Cálculo determinista y explicable</span>
          </li>
        </ul>
      </section>

      <div className="home-side">
        <RoadmapPanel />

        <section className="mode-card">
          <h2>Perfil activo</h2>
          <p><strong>{user?.rol === 'ADMIN' ? 'Administrador' : 'Planificador'}</strong></p>
          <p>{user?.rol === 'ADMIN' ? 'Puede activar umbrales; no ve acciones de evaluación.' : 'Puede registrar, editar y evaluar proyectos; no ve acciones administrativas.'}</p>
          <small>Estos roles demuestran comportamientos de interfaz; no son seguridad real de servidor.</small>
        </section>
      </div>
    </div>
  )
}
