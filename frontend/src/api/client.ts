import type { ApiErrorBody } from '../types/proyecto'
import { clearAccessToken, loadAccessToken } from './authStorage'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function parseApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody & {
      missing_fields?: string[]
      campos_faltantes?: string[]
    }
    if (typeof body.detail === 'string') {
      const extra = body.missing_fields ?? body.campos_faltantes
      if (extra?.length) {
        return `${body.detail} (${extra.join(', ')})`
      }
      return body.detail
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => d.msg).join('. ')
    }
  } catch {
    /* respuesta no JSON */
  }
  if (response.status === 500) {
    return (
      'Error interno del servidor (500). Si acaba de levantar Docker, ejecute el bootstrap PMV1 ' +
      'en auth_db (ver database/README.md) y reinicie la API.'
    )
  }
  return `Error del servidor (${response.status})`
}

export interface ApiFetchOptions extends RequestInit {
  auth?: boolean
  idempotencyKey?: string
  /** Tiempo máximo de espera (ms). Evita quedar en “Ingresando…” si el API no responde. */
  timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 20_000

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { auth = false, idempotencyKey, timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...init } =
    options
  const mergedHeaders = new Headers(headers)

  if (auth) {
    const token = loadAccessToken()
    if (!token) {
      throw new Error('Sesión expirada. Vuelva a iniciar sesión.')
    }
    mergedHeaders.set('Authorization', `Bearer ${token}`)
  }

  if (idempotencyKey) {
    mergedHeaders.set('Idempotency-Key', idempotencyKey)
  }

  if (init.body && !mergedHeaders.has('Content-Type')) {
    mergedHeaders.set('Content-Type', 'application/json')
  }

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergedHeaders,
      signal: controller.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(
        'El servidor no respondió a tiempo. Verifique que la API esté activa en http://127.0.0.1:8000.',
      )
    }
    throw new Error(
      'No se pudo conectar con el servidor. Compruebe que el backend esté en ejecución.',
    )
  } finally {
    window.clearTimeout(timer)
  }

  if (res.status === 401) {
    clearAccessToken()
  }

  if (!res.ok) {
    throw new Error(await parseApiError(res))
  }

  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}
