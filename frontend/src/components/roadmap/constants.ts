export type RoadmapStatus = 'active' | 'planned'

export interface RoadmapItem {
  label: string
  status: RoadmapStatus
}

export const PMV1_ROADMAP: RoadmapItem[] = [
  { label: 'Registro y versiones de proyectos', status: 'active' },
  { label: 'Validación de datos obligatorios', status: 'active' },
  { label: 'Agente económico simulado', status: 'active' },
  { label: 'Criterios económicos versionados', status: 'active' },
  { label: 'Agentes social, ambiental, técnico y jurídico', status: 'planned' },
  { label: 'Integración con servicios y colas', status: 'planned' },
  { label: 'Ranking, mapa e informes', status: 'planned' },
]
