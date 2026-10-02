import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { loginApi } from '../../api/auth.api'
import { clearAccessToken, saveAccessToken } from '../../api/authStorage'
import type { AuthSession, AuthUser, LoginCredentials } from '../../types/auth'
import { clearAuthSession, loadAuthSession, saveAuthSession } from './authStorage'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  hasRole: (role: string) => boolean
  login: (credentials: LoginCredentials) => Promise<string | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => loadAuthSession())

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      const response = await loginApi(credentials)
      saveAccessToken(response.access_token)

      const user: AuthUser = {
        id: response.user_id,
        nombre: response.full_name,
        email: credentials.email.trim().toLowerCase(),
        roles: response.roles,
      }

      const next: AuthSession = {
        user,
        loggedInAt: new Date().toISOString(),
      }
      saveAuthSession(next)
      setSession(next)
      return null
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudo iniciar sesión.'
      if (message.toLowerCase().includes('credenciales') || message.includes('401')) {
        return 'Correo o contraseña incorrectos. Use las credenciales asignadas por la municipalidad.'
      }
      if (message.includes('no respondió a tiempo')) {
        return (
          'El servicio de autenticación no respondió. Compruebe que la API esté en ' +
          'http://127.0.0.1:8000/health y que PostgreSQL (auth_db) esté disponible ' +
          'según la guía del backend; el frontend solo consume la API oficial.'
        )
      }
      if (message.includes('No se pudo conectar')) {
        return (
          'No hay conexión con la API en el puerto 8000. Inicie el backend (Docker o uvicorn) ' +
          'antes de iniciar sesión.'
        )
      }
      return message
    }
  }, [])

  const logout = useCallback(() => {
    clearAccessToken()
    clearAuthSession()
    setSession(null)
  }, [])

  const hasRole = useCallback(
    (role: string) => session?.user.roles.includes(role) ?? false,
    [session],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: session !== null,
      hasRole,
      login,
      logout,
    }),
    [session, hasRole, login, logout],
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
