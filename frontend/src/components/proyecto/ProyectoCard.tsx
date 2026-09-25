import { Link } from 'react-router-dom'
import type { Proyecto } from '../../types/proyecto'
import { formatCurrency, formatDate, formatNumber } from '../../utils/format'

interface ProyectoCardProps {
  proyecto: Proyecto
  compact?: boolean
}

export function ProyectoCard({ proyecto, compact = false }: ProyectoCardProps) {
  return (
    <article className={`proyecto-card ${compact ? 'compact' : ''}`}>
      <header className="proyecto-card-header">
        <div>
          <p className="proyecto-id">Expediente #{proyecto.id}</p>
          <h2 className="proyecto-nombre">{proyecto.nombre}</h2>
        </div>
        <span className={`estado-badge estado-${proyecto.estado.toLowerCase()}`}>
          {proyecto.estado.replace('_', ' ')}
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
        <div className="span-full">
          <dt>Registrado</dt>
          <dd>{formatDate(proyecto.fecha_creacion)}</dd>
        </div>
      </dl>

      <footer className="proyecto-card-footer">
        <Link to={`/consultar?id=${proyecto.id}`} className="link-button">
          Ver detalle
        </Link>
      </footer>
    </article>
  )
}
