import { clearAccessToken } from '../../api/authStorage'
import type { AuthSession } from '../../types/auth'
import { AUTH_STORAGE_KEY } from './constants'

export function loadAuthSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AuthSession
    const user = parsed?.user
    if (!user?.email || !Array.isArray(user.roles)) {
      clearAuthSession()
      return null
    }
    return parsed
  } catch {
    clearAuthSession()
    return null
  }
}

export function saveAuthSession(session: AuthSession): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

export function clearAuthSession(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY)
  clearAccessToken()
}
