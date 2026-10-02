import type {
  LegacyProyecto,
  LegacyProyectoCreate,
  LegacyRegistrarProyectoResponse,
} from '../types/proyecto'
import { apiFetch } from './client'

export async function checkHealth(): Promise<boolean> {
  try {
    const data = await apiFetch<{ status?: string }>('/health')
    return data.status === 'ok'
  } catch {
    return false
  }
}

export async function registrarProyecto(
  payload: LegacyProyectoCreate,
): Promise<LegacyRegistrarProyectoResponse> {
  return apiFetch<LegacyRegistrarProyectoResponse>('/api/v1/proyectos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function obtenerProyecto(id: number): Promise<LegacyProyecto> {
  return apiFetch<LegacyProyecto>(`/api/v1/proyectos/${id}`)
}
