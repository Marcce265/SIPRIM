import type { PMV1ProjectResponse } from '../types/pmv1'
import type { Proyecto } from '../types/proyecto'

export function mapPmV1ToProyecto(project: PMV1ProjectResponse): Proyecto {
  return {
    id: project.project_id,
    project_version_id: project.project_version_id,
    nombre: project.title,
    descripcion: project.description,
    ubicacion: project.location ?? '—',
    tipo_proyecto: project.proposed_land_use ?? '—',
    presupuesto: project.estimated_budget_pen,
    beneficiarios: project.beneficiaries_count,
    estado: project.status,
    codigo: project.code,
    fecha_creacion: '',
  }
}
