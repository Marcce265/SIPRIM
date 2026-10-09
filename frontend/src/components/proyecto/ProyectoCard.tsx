import { Link } from 'react-router-dom'
import type { Proyecto } from '../../types/proyecto'
import { formatCurrency, formatDate, formatNumber } from '../../utils/format'

interface ProyectoCardProps {
  proyecto: Proyecto
  compact?: boolean
}

function displayProjectId(proyecto: Proyecto): string {
  if (proyecto.codigo) return proyecto.codigo
  const id = String(proyecto.id)
  return id.length > 8 ? `${id.slice(0, 8)}…` : id
}

export function ProyectoCard({ proyecto, compact = false }: ProyectoCardProps) {
  const estado = String(proyecto.estado ?? 'unknown')

  return (
    <article className={`proyecto-card ${compact ? 'compact' : ''}`}>
      <header className="proyecto-card-header">
        <div>
          <p className="proyecto-id">
            {proyecto.codigo ? 'Código expediente · ' : 'UUID · '}
            {displayProjectId(proyecto)}
          </p>
          <h2 className="proyecto-nombre">{proyecto.nombre}</h2>
        </div>
        <span className={`estado-badge estado-${estado.toLowerCase()}`}>
          {estado.replace('_', ' ')}
        </span>
      </header>

      {!compact && <p className="proyecto-desc">{proyecto.descripcion}</p>}

      <dl className="proyecto-meta">
        <div>
          <dt>Ubicación</dt>
          <dd>{proyecto.ubicacion}</dd>
        </div>
        <div>
          <dt>Tipo</dt>
          <dd>{proyecto.tipo_proyecto}</dd>
        </div>
        <div>
          <dt>Presupuesto</dt>
          <dd>{formatCurrency(proyecto.presupuesto)}</dd>
        </div>
        <div>
          <dt>Beneficiarios</dt>
          <dd>{formatNumber(proyecto.beneficiarios)}</dd>
        </div>
        {proyecto.fecha_creacion && (
          <div className="span-full">
            <dt>Registrado</dt>
            <dd>{formatDate(proyecto.fecha_creacion)}</dd>
          </div>
        )}
      </dl>

      <footer className="proyecto-card-footer">
        <Link to={`/proyectos/${proyecto.id}`} className="link-button">
          Ver expediente
        </Link>
      </footer>
    </article>
  )
}
