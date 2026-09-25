import type { ApiErrorBody } from '../types/proyecto'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function parseApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody
    if (typeof body.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => d.msg).join('. ')
    }
  } catch {
    /* respuesta no JSON */
  }
  return `Error del servidor (${response.status})`
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    throw new Error(await parseApiError(res))
  }
  return res.json() as Promise<T>
}
