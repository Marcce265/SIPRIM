import type { Proyecto, ProyectoCreate, RegistrarProyectoResponse } from '../types/proyecto'
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
  payload: ProyectoCreate,
): Promise<RegistrarProyectoResponse> {
  return apiFetch<RegistrarProyectoResponse>('/api/v1/proyectos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function obtenerProyecto(id: number): Promise<Proyecto> {
  return apiFetch<Proyecto>(`/api/v1/proyectos/${id}`)
}
