export type UserRole = 'planificador' | 'evaluador' | 'administrador'

export interface AuthUser {
  id: string
  nombre: string
  email: string
  rol: UserRole
}

export interface AuthSession {
  user: AuthUser
  loggedInAt: string
}

export interface LoginCredentials {
  email: string
  password: string
}
