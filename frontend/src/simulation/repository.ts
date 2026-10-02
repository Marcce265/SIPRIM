import type { AuthUser, UserRole } from '../types/auth'
import type {
  CriteriaVersion,
  EconomicEvaluation,
  Project,
  ProjectInput,
  ProjectVersion,
  SimulationState,
} from '../types/proyecto'
import { evaluateEconomicProject, validateEconomicCriteria } from './economicAgent'

export const SIMULATION_STORAGE_KEY = 'siprim:demo-data:v1'
export const SIMULATION_SCHEMA_VERSION = 1 as const

const listeners = new Set<() => void>()
let recoveryNotice: string | null = null

function isoAt(value: string): string {
  return new Date(value).toISOString()
}

function buildSeedState(): SimulationState {
  const criteria: CriteriaVersion = {
    id: 'criteria-v1',
    numero: 1,
    costoExcelente: 200,
    costoInaceptable: 500,
    pesoEconomico: 100,
    estado: 'activo',
    creadoPor: 'demo-admin',
    fechaActivacion: isoAt('2026-09-25T14:00:00-05:00'),
  }
  const projects: Project[] = [
    {
      id: 'project-a',
      codigo: 'PRY-A',
      estado: 'evaluado',
      versionActualId: 'project-a-v1',
      creadoPor: 'demo-planner',
      fechaCreacion: isoAt('2026-09-25T14:10:00-05:00'),
      fechaActualizacion: isoAt('2026-09-25T14:12:00-05:00'),
    },
    {
      id: 'project-b',
      codigo: 'PRY-B',
      estado: 'evaluado',
      versionActualId: 'project-b-v1',
      creadoPor: 'demo-planner',
      fechaCreacion: isoAt('2026-09-25T14:15:00-05:00'),
      fechaActualizacion: isoAt('2026-09-25T14:17:00-05:00'),
    },
  ]
  const projectVersions: ProjectVersion[] = [
    {
      id: 'project-a-v1',
      proyectoId: 'project-a',
      numero: 1,
      nombre: 'Proyecto A — Mejoramiento de losa deportiva',
      descripcion: 'Caso académico para comparar costo por beneficiario.',
      presupuesto: 120_000,
      beneficiarios: 600,
      creadoPor: 'demo-planner',
      fechaCreacion: projects[0].fechaCreacion,
    },
    {
      id: 'project-b-v1',
      proyectoId: 'project-b',
      numero: 1,
      nombre: 'Proyecto B — Ampliación de veredas',
      descripcion: 'Caso académico para comparar costo por beneficiario.',
      presupuesto: 90_000,
      beneficiarios: 300,
      creadoPor: 'demo-planner',
      fechaCreacion: projects[1].fechaCreacion,
    },
  ]
  const evaluations: EconomicEvaluation[] = projectVersions.map((version, index) => {
    const finishedAt = isoAt(`2026-09-25T14:${index === 0 ? '12' : '17'}:00-05:00`)
    return {
      id: `evaluation-${index + 1}`,
      codigo: `ECO-${String(index + 1).padStart(3, '0')}`,
      proyectoId: version.proyectoId,
      proyectoVersionId: version.id,
      criteriosVersionId: criteria.id,
      entrada: {
        nombre: version.nombre,
        descripcion: version.descripcion,
        presupuesto: version.presupuesto,
        beneficiarios: version.beneficiarios,
        versionNumero: version.numero,
      },
      configuracion: {
        versionNumero: criteria.numero,
        costoExcelente: criteria.costoExcelente,
        costoInaceptable: criteria.costoInaceptable,
        pesoEconomico: criteria.pesoEconomico,
      },
      estado: 'completado',
      solicitadaPor: 'demo-planner',
      fechaSolicitud: finishedAt,
      fechaInicio: finishedAt,
      fechaFinalizacion: finishedAt,
      resultado: evaluateEconomicProject(version, criteria, finishedAt),
    }
  })
  return {
    schemaVersion: SIMULATION_SCHEMA_VERSION,
    nextProjectNumber: 3,
    nextEvaluationNumber: 3,
    projects,
    projectVersions,
    criteriaVersions: [criteria],
    evaluations,
    updatedAt: isoAt('2026-09-25T14:17:00-05:00'),
  }
}

function isValidState(value: unknown): value is SimulationState {
  if (!value || typeof value !== 'object') return false
  const state = value as Partial<SimulationState>
  if (
    state.schemaVersion !== SIMULATION_SCHEMA_VERSION ||
    !Array.isArray(state.projects) ||
    !Array.isArray(state.projectVersions) ||
    !Array.isArray(state.criteriaVersions) ||
    !Array.isArray(state.evaluations) ||
    typeof state.nextProjectNumber !== 'number' ||
    typeof state.nextEvaluationNumber !== 'number'
  ) {
    return false
  }
  const criteriaVersions = state.criteriaVersions
  const evaluations = state.evaluations
  const activeCriteria = criteriaVersions.filter(
    (criteria) => criteria?.estado === 'activo',
  )
  return (
    activeCriteria.length === 1 &&
    criteriaVersions.every(
      (criteria) =>
        typeof criteria?.id === 'string' &&
        Number.isInteger(criteria?.numero) &&
        criteria.numero > 0 &&
        criteria.pesoEconomico === 100 &&
        validateEconomicCriteria(criteria.costoExcelente, criteria.costoInaceptable).length === 0,
    ) &&
    state.projects.every(
      (project) =>
        typeof project?.id === 'string' &&
        typeof project?.codigo === 'string' &&
        typeof project?.versionActualId === 'string',
    ) &&
    state.projectVersions.every(
      (version) =>
        typeof version?.id === 'string' &&
        typeof version?.proyectoId === 'string' &&
        typeof version?.nombre === 'string' &&
        typeof version?.descripcion === 'string' &&
        Number.isFinite(version?.presupuesto) &&
        version.presupuesto > 0 &&
        Number.isInteger(version?.beneficiarios) &&
        version.beneficiarios > 0,
    ) &&
    evaluations.every(
      (evaluation) =>
        typeof evaluation?.id === 'string' &&
        typeof evaluation?.entrada?.nombre === 'string' &&
        Number.isFinite(evaluation?.entrada?.presupuesto) &&
        evaluation.entrada.presupuesto > 0 &&
        Number.isInteger(evaluation?.entrada?.beneficiarios) &&
        evaluation.entrada.beneficiarios > 0 &&
        evaluation?.configuracion?.pesoEconomico === 100 &&
        validateEconomicCriteria(
          evaluation?.configuracion?.costoExcelente,
          evaluation?.configuracion?.costoInaceptable,
        ).length === 0,
    )
  )
}

function readInitialState(): SimulationState {
  if (typeof window === 'undefined') return buildSeedState()
  const serialized = window.localStorage.getItem(SIMULATION_STORAGE_KEY)
  if (!serialized) {
    const seed = buildSeedState()
    window.localStorage.setItem(SIMULATION_STORAGE_KEY, JSON.stringify(seed))
    return seed
  }
  try {
    const parsed: unknown = JSON.parse(serialized)
    if (!isValidState(parsed)) throw new Error('esquema no reconocido')
    return parsed
  } catch {
    const seed = buildSeedState()
    window.localStorage.setItem(SIMULATION_STORAGE_KEY, JSON.stringify(seed))
    recoveryNotice =
      'Los datos locales no eran válidos y se restauraron los casos iniciales de demostración.'
    return seed
  }
}

let state = readInitialState()

function persist(next: SimulationState): void {
  state = { ...next, updatedAt: new Date().toISOString() }
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(SIMULATION_STORAGE_KEY, JSON.stringify(state))
  }
  listeners.forEach((listener) => listener())
}

function assertRole(user: AuthUser, role: UserRole): void {
  if (!user.roles.includes(role)) {
    throw new Error(
      role === 'ADMIN'
        ? 'Esta acción está disponible para el perfil Administrador.'
        : 'Esta acción está disponible para el perfil Planificador.',
    )
  }
}

function validateProjectInput(input: ProjectInput): void {
  if (!input.nombre.trim()) throw new Error('El nombre es obligatorio.')
  if (!input.descripcion.trim()) throw new Error('La descripción es obligatoria.')
  if (!Number.isFinite(input.presupuesto) || input.presupuesto <= 0) {
    throw new Error('El presupuesto debe ser mayor que cero.')
  }
  if (!Number.isInteger(input.beneficiarios) || input.beneficiarios <= 0) {
    throw new Error('Los beneficiarios deben ser un entero mayor que cero.')
  }
}

export const simulationRepository = {
  getSnapshot(): SimulationState {
    return state
  },

  subscribe(listener: () => void): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },

  getRecoveryNotice(): string | null {
    return recoveryNotice
  },

  clearRecoveryNotice(): void {
    recoveryNotice = null
    state = { ...state }
    listeners.forEach((listener) => listener())
  },

  getProject(projectId: string): Project | undefined {
    return state.projects.find((project) => project.id === projectId)
  },

  getVersion(versionId: string): ProjectVersion | undefined {
    return state.projectVersions.find((version) => version.id === versionId)
  },

  getCurrentVersion(projectId: string): ProjectVersion | undefined {
    const project = this.getProject(projectId)
    return project ? this.getVersion(project.versionActualId) : undefined
  },

  getProjectVersions(projectId: string): ProjectVersion[] {
    return state.projectVersions
      .filter((version) => version.proyectoId === projectId)
      .sort((a, b) => b.numero - a.numero)
  },

  getProjectEvaluations(projectId: string): EconomicEvaluation[] {
    return state.evaluations
      .filter((evaluation) => evaluation.proyectoId === projectId)
      .sort((a, b) => b.fechaSolicitud.localeCompare(a.fechaSolicitud))
  },

  getActiveCriteria(): CriteriaVersion {
    const criteria = state.criteriaVersions.find((item) => item.estado === 'activo')
    if (!criteria) throw new Error('No existe una configuración económica activa.')
    return criteria
  },

  createProject(input: ProjectInput, user: AuthUser): Project {
    assertRole(user, 'PLANNER')
    validateProjectInput(input)
    const now = new Date().toISOString()
    const number = state.nextProjectNumber
    const id = `project-${number}`
    const versionId = `${id}-v1`
    const project: Project = {
      id,
      codigo: `PRY-${String(number).padStart(3, '0')}`,
      estado: 'listo',
      versionActualId: versionId,
      creadoPor: user.id,
      fechaCreacion: now,
      fechaActualizacion: now,
    }
    const version: ProjectVersion = {
      ...input,
      nombre: input.nombre.trim(),
      descripcion: input.descripcion.trim(),
      id: versionId,
      proyectoId: id,
      numero: 1,
      creadoPor: user.id,
      fechaCreacion: now,
    }
    persist({
      ...state,
      nextProjectNumber: number + 1,
      projects: [...state.projects, project],
      projectVersions: [...state.projectVersions, version],
    })
    return project
  },

  updateProject(projectId: string, input: ProjectInput, user: AuthUser): ProjectVersion {
    assertRole(user, 'PLANNER')
    validateProjectInput(input)
    const project = this.getProject(projectId)
    const current = this.getCurrentVersion(projectId)
    if (!project || !current) throw new Error('Proyecto no encontrado.')
    const hasCompletedEvaluation = state.evaluations.some(
      (evaluation) =>
        evaluation.proyectoVersionId === current.id && evaluation.estado === 'completado',
    )
    const now = new Date().toISOString()
    const normalized = {
      ...input,
      nombre: input.nombre.trim(),
      descripcion: input.descripcion.trim(),
    }
    let nextVersion: ProjectVersion
    let versions: ProjectVersion[]
    if (hasCompletedEvaluation) {
      nextVersion = {
        ...normalized,
        id: `${project.id}-v${current.numero + 1}`,
        proyectoId: project.id,
        numero: current.numero + 1,
        creadoPor: user.id,
        fechaCreacion: now,
      }
      versions = [...state.projectVersions, nextVersion]
    } else {
      nextVersion = { ...current, ...normalized }
      versions = state.projectVersions.map((version) =>
        version.id === current.id ? nextVersion : version,
      )
    }
    persist({
      ...state,
      projects: state.projects.map((item) =>
        item.id === project.id
          ? {
              ...item,
              estado: 'listo',
              versionActualId: nextVersion.id,
              fechaActualizacion: now,
            }
          : item,
      ),
      projectVersions: versions,
    })
    return nextVersion
  },

  requestEvaluation(
    projectId: string,
    user: AuthUser,
    options: { simulateFailure?: boolean } = {},
  ): EconomicEvaluation {
    assertRole(user, 'PLANNER')
    const project = this.getProject(projectId)
    const version = this.getCurrentVersion(projectId)
    const criteria = this.getActiveCriteria()
    if (!project || !version) throw new Error('Proyecto no encontrado.')
    const inProgress = state.evaluations.some(
      (evaluation) =>
        evaluation.proyectoId === projectId &&
        (evaluation.estado === 'pendiente' || evaluation.estado === 'procesando'),
    )
    if (inProgress) throw new Error('Ya existe una evaluación en curso para este proyecto.')
    validateProjectInput(version)
    const number = state.nextEvaluationNumber
    const evaluation: EconomicEvaluation = {
      id: `evaluation-${number}`,
      codigo: `ECO-${String(number).padStart(3, '0')}`,
      proyectoId: projectId,
      proyectoVersionId: version.id,
      criteriosVersionId: criteria.id,
      entrada: {
        nombre: version.nombre,
        descripcion: version.descripcion,
        presupuesto: version.presupuesto,
        beneficiarios: version.beneficiarios,
        versionNumero: version.numero,
      },
      configuracion: {
        versionNumero: criteria.numero,
        costoExcelente: criteria.costoExcelente,
        costoInaceptable: criteria.costoInaceptable,
        pesoEconomico: criteria.pesoEconomico,
      },
      estado: 'pendiente',
      solicitadaPor: user.id,
      fechaSolicitud: new Date().toISOString(),
      simularFallo: options.simulateFailure,
    }
    persist({
      ...state,
      nextEvaluationNumber: number + 1,
      evaluations: [...state.evaluations, evaluation],
      projects: state.projects.map((item) =>
        item.id === projectId ? { ...item, estado: 'evaluando' } : item,
      ),
    })
    return evaluation
  },

  advanceEvaluations(now = Date.now()): void {
    let changed = false
    const evaluations = state.evaluations.map((evaluation) => {
      if (evaluation.estado !== 'pendiente' && evaluation.estado !== 'procesando') {
        return evaluation
      }
      const elapsed = now - new Date(evaluation.fechaSolicitud).getTime()
      if (evaluation.estado === 'pendiente' && elapsed >= 450) {
        changed = true
        return { ...evaluation, estado: 'procesando' as const, fechaInicio: new Date(now).toISOString() }
      }
      if (evaluation.estado === 'procesando' && elapsed >= 1_300) {
        changed = true
        const completedAt = new Date(now).toISOString()
        if (evaluation.simularFallo) {
          return {
            ...evaluation,
            estado: 'fallido' as const,
            fechaFinalizacion: completedAt,
            error: 'Fallo técnico simulado. Puede reintentar la evaluación.',
          }
        }
        try {
          return {
            ...evaluation,
            estado: 'completado' as const,
            fechaFinalizacion: completedAt,
            resultado: evaluateEconomicProject(
              evaluation.entrada,
              evaluation.configuracion,
              completedAt,
            ),
          }
        } catch (error) {
          return {
            ...evaluation,
            estado: 'fallido' as const,
            fechaFinalizacion: completedAt,
            error: error instanceof Error ? error.message : 'No fue posible evaluar el proyecto.',
          }
        }
      }
      return evaluation
    })
    if (!changed) return

    const projects = state.projects.map((project) => {
      const projectEvaluations = evaluations.filter(
        (evaluation) => evaluation.proyectoId === project.id,
      )
      const running = projectEvaluations.some(
        (evaluation) => evaluation.estado === 'pendiente' || evaluation.estado === 'procesando',
      )
      if (running) return { ...project, estado: 'evaluando' as const }
      const latest = [...projectEvaluations].sort((a, b) =>
        b.fechaSolicitud.localeCompare(a.fechaSolicitud),
      )[0]
      if (!latest) return project
      return {
        ...project,
        estado: latest.estado === 'completado' ? ('evaluado' as const) : ('fallido' as const),
      }
    })
    persist({ ...state, evaluations, projects })
  },

  activateCriteria(
    excellentCost: number,
    unacceptableCost: number,
    user: AuthUser,
  ): CriteriaVersion {
    assertRole(user, 'ADMIN')
    const errors = validateEconomicCriteria(excellentCost, unacceptableCost)
    if (errors.length > 0) throw new Error(errors.join(' '))
    const nextNumber = Math.max(...state.criteriaVersions.map((item) => item.numero), 0) + 1
    const criteria: CriteriaVersion = {
      id: `criteria-v${nextNumber}`,
      numero: nextNumber,
      costoExcelente: excellentCost,
      costoInaceptable: unacceptableCost,
      pesoEconomico: 100,
      estado: 'activo',
      creadoPor: user.id,
      fechaActivacion: new Date().toISOString(),
    }
    persist({
      ...state,
      criteriaVersions: [
        ...state.criteriaVersions.map((item) => ({ ...item, estado: 'retirado' as const })),
        criteria,
      ],
    })
    return criteria
  },

  restoreSeedData(): void {
    recoveryNotice = null
    persist(buildSeedState())
  },
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== SIMULATION_STORAGE_KEY || !event.newValue) return
    try {
      const parsed: unknown = JSON.parse(event.newValue)
      if (!isValidState(parsed)) return
      state = parsed
      listeners.forEach((listener) => listener())
    } catch {
      // Otra pestaña puede estar escribiendo; se conserva el último estado válido.
    }
  })
}
