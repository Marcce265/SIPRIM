import { PMV1_ROADMAP } from './constants'

export function RoadmapPanel() {
  return (
    <aside className="roadmap-panel" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title">Hoja de ruta PMV1</h2>
      <p className="roadmap-intro">
        Esta interfaz implementa la carga única del expediente para distribuirlo luego entre
        los agentes especialistas. Las siguientes capacidades dependen del backend y de
        historias posteriores.
      </p>
      <ul className="roadmap-list">
        {PMV1_ROADMAP.map((item) => (
          <li key={item.label} className={`roadmap-item ${item.status}`}>
            <span className="roadmap-bullet" aria-hidden />
            <span>{item.label}</span>
            {item.status === 'active' && <span className="roadmap-tag">Disponible</span>}
          </li>
        ))}
      </ul>
    </aside>
  )
}
