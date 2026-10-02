import type { AuthSession } from '../../types/auth'
import { AUTH_STORAGE_KEY } from './constants'

export function loadAuthSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AuthSession>
    if (
      parsed?.schemaVersion === 1 &&
      typeof parsed.userId === 'string' &&
      typeof parsed.loggedInAt === 'string'
    ) {
      return parsed as AuthSession
    }
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return null
  } catch {
    return null
  }
}

export function saveAuthSession(session: AuthSession): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

export function clearAuthSession(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY)
}
