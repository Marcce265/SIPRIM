import type { Proyecto } from '../types/proyecto'

const STORAGE_KEY = 'siprim:proyectos-recientes'
const MAX_ITEMS = 8

function sanitizeProyecto(entry: unknown): Proyecto | null {
  if (!entry || typeof entry !== 'object') return null
  const p = entry as Partial<Proyecto>
  if (p.id == null || !p.nombre || !p.estado) return null
  return {
    ...(p as Proyecto),
    id: String(p.id),
  }
}

export function loadRecentProjects(): Proyecto[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown[]
    if (!Array.isArray(parsed)) return []
    return parsed.map(sanitizeProyecto).filter((p): p is Proyecto => p !== null)
  } catch {
    return []
  }
}

export function rememberProject(proyecto: Proyecto): void {
  const current = loadRecentProjects().filter((p) => p.id !== proyecto.id)
  const next = [proyecto, ...current].slice(0, MAX_ITEMS)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}
