import { PMV1_ROADMAP } from './constants'

export function RoadmapPanel() {
  return (
    <aside className="roadmap-panel" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title">Funciones del sistema</h2>
      <p className="roadmap-intro">
        Capacidades conectadas a la API PMV1. Las marcadas como posteriores corresponden al
        roadmap del producto completo.
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
