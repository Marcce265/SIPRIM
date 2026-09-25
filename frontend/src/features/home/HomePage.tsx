import { Link } from 'react-router-dom'
import { useMemo } from 'react'
import { ProyectoCard } from '../../components/proyecto/ProyectoCard'
import { RoadmapPanel } from '../../components/roadmap/RoadmapPanel'
import { loadRecentProjects } from '../../utils/recentProjects'

export function HomePage() {
  const recientes = useMemo(() => loadRecentProjects(), [])

  return (
    <div className="home-layout">
      <section className="hero">
        <p className="hero-eyebrow">Municipalidad Distrital de El Tambo · Junín</p>
        <h1>Sistema inteligente de priorización de inversiones urbanas</h1>
        <p className="hero-lead">
          Registre el expediente básico de su proyecto una sola vez. SIPRIM prepara la
          información para la preevaluación económica, social, ambiental, técnica y jurídica,
          con trazabilidad y apoyo a la decisión pública — sin reemplazar la autoridad
          municipal.
        </p>
        <div className="hero-actions">
          <Link to="/registrar" className="btn btn-primary">
            Cargar expediente
          </Link>
          <Link to="/consultar" className="btn btn-secondary">
            Consultar por ID
          </Link>
        </div>
        <ul className="hero-stats" aria-label="Beneficios clave">
          <li>
            <strong>Una sola carga</strong>
            <span>HU1.1 · RF-01</span>
          </li>
          <li>
            <strong>5 dimensiones</strong>
            <span>Agentes especialistas (roadmap)</span>
          </li>
          <li>
            <strong>Human-in-the-loop</strong>
            <span>Control institucional</span>
          </li>
        </ul>
      </section>

      <div className="home-side">
        <RoadmapPanel />

        {recientes.length > 0 && (
          <section className="recientes" aria-labelledby="recientes-title">
            <h2 id="recientes-title">Expedientes recientes en este navegador</h2>
            <p className="recientes-note">
              El backend aún no expone un listado general; aquí se muestran los proyectos
              registrados o consultados desde esta computadora.
            </p>
            <div className="recientes-list">
              {recientes.map((p) => (
                <ProyectoCard key={p.id} proyecto={p} compact />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
