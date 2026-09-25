export type RoadmapStatus = 'active' | 'planned'

export interface RoadmapItem {
  label: string
  status: RoadmapStatus
}

export const PMV1_ROADMAP: RoadmapItem[] = [
  { label: 'Carga de expediente (HU1.1)', status: 'active' },
  { label: 'Validación de datos faltantes (HU1.2)', status: 'planned' },
  { label: 'Evaluación multidimensional (agentes)', status: 'planned' },
  { label: 'Expedientes en revisión y alertas', status: 'planned' },
  { label: 'Validación humana (human-in-the-loop)', status: 'planned' },
  { label: 'Ranking y priorización (RF-09)', status: 'planned' },
  { label: 'Acceso con roles (RNF-03)', status: 'planned' },
]
