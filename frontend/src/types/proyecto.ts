export type ProjectStatus = 'listo' | 'evaluando' | 'evaluado' | 'fallido'
export type EvaluationStatus = 'pendiente' | 'procesando' | 'completado' | 'fallido'

export interface ProjectInput {
  nombre: string
  descripcion: string
  presupuesto: number
  beneficiarios: number
}

export interface Project {
  id: string
  codigo: string
  estado: ProjectStatus
  versionActualId: string
  creadoPor: string
  fechaCreacion: string
  fechaActualizacion: string
}

export interface ProjectVersion extends ProjectInput {
  id: string
  proyectoId: string
  numero: number
  creadoPor: string
  fechaCreacion: string
}

export interface CriteriaVersion {
  id: string
  numero: number
  costoExcelente: number
  costoInaceptable: number
  pesoEconomico: 100
  estado: 'activo' | 'retirado'
  creadoPor: string
  fechaActivacion: string
}

export interface EconomicResult {
  presupuesto: number
  beneficiarios: number
  costoPorBeneficiario: number
  formula: 'presupuesto / beneficiarios'
  costoExcelente: number
  costoInaceptable: number
  pesoEconomico: 100
  puntuacion: number
  explicacion: string
  versionAlgoritmo: 'criterio-economico-academico-v1'
  fechaCalculo: string
}

export interface EconomicProjectSnapshot extends ProjectInput {
  versionNumero: number
}

export interface EconomicCriteriaSnapshot {
  versionNumero: number
  costoExcelente: number
  costoInaceptable: number
  pesoEconomico: 100
}

export interface EconomicEvaluation {
  id: string
  codigo: string
  proyectoId: string
  proyectoVersionId: string
  criteriosVersionId: string
  entrada: EconomicProjectSnapshot
  configuracion: EconomicCriteriaSnapshot
  estado: EvaluationStatus
  solicitadaPor: string
  fechaSolicitud: string
  fechaInicio?: string
  fechaFinalizacion?: string
  resultado?: EconomicResult
  error?: string
  simularFallo?: boolean
}

export interface SimulationState {
  schemaVersion: 1
  nextProjectNumber: number
  nextEvaluationNumber: number
  projects: Project[]
  projectVersions: ProjectVersion[]
  criteriaVersions: CriteriaVersion[]
  evaluations: EconomicEvaluation[]
  updatedAt: string
}

// Contratos heredados: permanecen aislados en el adaptador HTTP y no son usados
// por el recorrido de demostracion.
export interface LegacyProyectoCreate {
  nombre: string
  descripcion: string
  ubicacion: string
  presupuesto: number
  beneficiarios: number
  tipo_proyecto: string
}

export interface LegacyProyecto extends LegacyProyectoCreate {
  id: number
  estado: string
  fecha_creacion: string
}

export interface LegacyRegistrarProyectoResponse {
  mensaje: string
  proyecto: LegacyProyecto
}

export interface ApiErrorBody {
  detail: string | { msg: string; loc: string[] }[]
}
