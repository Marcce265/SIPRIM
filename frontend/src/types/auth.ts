export type UserRole = 'ADMIN' | 'PLANNER'

export interface AuthUser {
  id: string
  nombre: string
  email: string
  rol: UserRole
}

export interface AuthSession {
  schemaVersion: 1
  userId: string
  loggedInAt: string
}

export interface LoginCredentials {
  email: string
  password: string
}
