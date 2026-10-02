export type UserRole = 'ADMIN' | 'PLANNER' | 'LEGAL_ADVISOR'

export interface AuthUser {
  id: string
  nombre: string
  email: string
  roles: string[]
}

export interface AuthSession {
  user: AuthUser
  loggedInAt: string
}

export interface LoginCredentials {
  email: string
  password: string
}
