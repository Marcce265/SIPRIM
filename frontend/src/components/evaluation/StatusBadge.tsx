import type { EvaluationStatus, ProjectStatus } from '../../types/proyecto'

const LABELS: Record<EvaluationStatus | ProjectStatus, string> = {
  listo: 'Listo para evaluar',
  evaluando: 'Evaluando',
  evaluado: 'Evaluado',
  fallido: 'Fallido',
  pendiente: 'Pendiente',
  procesando: 'Procesando',
  completado: 'Completado',
}

export function StatusBadge({ status }: { status: EvaluationStatus | ProjectStatus }) {
  return <span className={`estado-badge estado-${status}`}>{LABELS[status]}</span>
}
