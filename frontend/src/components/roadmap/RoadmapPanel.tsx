import { PMV1_ROADMAP } from './constants'

export function RoadmapPanel() {
  return (
    <aside className="roadmap-panel" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title">Alcance de la demostración</h2>
      <p className="roadmap-intro">
        El PMV 1 ejecuta un cálculo económico real dentro del navegador. Las capacidades
        marcadas como posteriores pertenecen a la arquitectura objetivo y no generan
        resultados en esta demostración.
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
