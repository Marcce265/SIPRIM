import type { AuthUser, LoginCredentials } from '../../types/auth'

export const AUTH_STORAGE_KEY = 'siprim:auth-session'

/** Usuarios demo PMV1 hasta que el backend exponga RNF-03 (auth real). */
export const DEMO_USERS: Array<AuthUser & { password: string }> = [
  {
    id: '1',
    nombre: 'Planificador Municipal',
    email: 'planificador@eltambo.gob.pe',
    rol: 'planificador',
    password: 'siprim2026',
  },
  {
    id: '2',
    nombre: 'Evaluador Técnico',
    email: 'evaluador@eltambo.gob.pe',
    rol: 'evaluador',
    password: 'siprim2026',
  },
  {
    id: '3',
    nombre: 'Administrador SIPRIM',
    email: 'admin@eltambo.gob.pe',
    rol: 'administrador',
    password: 'siprim2026',
  },
]

export function findDemoUser(credentials: LoginCredentials): AuthUser | null {
  const email = credentials.email.trim().toLowerCase()
  const match = DEMO_USERS.find(
    (u) => u.email.toLowerCase() === email && u.password === credentials.password,
  )
  if (!match) return null
  const { password: _password, ...user } = match
  return user
}
