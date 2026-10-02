export type RoadmapStatus = 'active' | 'planned'

export interface RoadmapItem {
  label: string
  status: RoadmapStatus
}

export const PMV1_ROADMAP: RoadmapItem[] = [
  { label: 'Registro de expedientes de inversión', status: 'active' },
  { label: 'Validación de datos del proyecto', status: 'active' },
  { label: 'Evaluación económica preliminar', status: 'active' },
  { label: 'Revisión jurídica y de zonificación', status: 'active' },
  { label: 'Consulta de normativa aplicable', status: 'active' },
  { label: 'Dictamen con validación de autoridad', status: 'active' },
  { label: 'Ranking y priorización consolidada', status: 'planned' },
]
