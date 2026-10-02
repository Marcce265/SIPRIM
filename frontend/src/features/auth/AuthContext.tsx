/* oxlint-disable react/only-export-components -- el proveedor y su hook forman una API unica */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { AuthSession, AuthUser, LoginCredentials } from '../../types/auth'
import { authenticateDemoUser, getDemoUser } from '../../simulation/demoUsers'
import {
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
} from './authStorage'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<string | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => loadAuthSession())

  const login = useCallback(async (credentials: LoginCredentials) => {
    const user = authenticateDemoUser(credentials)
    if (!user) {
      return 'Correo o contraseña incorrectos.'
    }

    const next: AuthSession = {
      schemaVersion: 1,
      userId: user.id,
      loggedInAt: new Date().toISOString(),
    }
    saveAuthSession(next)
    setSession(next)
    return null
  }, [])

  const logout = useCallback(() => {
    clearAuthSession()
    setSession(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session ? getDemoUser(session.userId) : null,
      isAuthenticated: session !== null && getDemoUser(session.userId) !== null,
      login,
      logout,
    }),
    [session, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return ctx
}
