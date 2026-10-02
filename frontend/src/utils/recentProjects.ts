import type { LegacyProyecto } from '../types/proyecto'

const STORAGE_KEY = 'siprim:proyectos-recientes'
const MAX_ITEMS = 8

export function loadRecentProjects(): LegacyProyecto[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as LegacyProyecto[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function rememberProject(proyecto: LegacyProyecto): void {
  const current = loadRecentProjects().filter((p) => p.id !== proyecto.id)
  const next = [proyecto, ...current].slice(0, MAX_ITEMS)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}
