import type { AuthUser, LoginCredentials } from '../types/auth'

type DemoAccount = AuthUser & { demoPassword: string }

const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  {
    id: 'demo-admin',
    nombre: 'Administrador de demostración',
    email: 'admin@siprim.demo',
    rol: 'ADMIN',
    demoPassword: 'demo2026',
  },
  {
    id: 'demo-planner',
    nombre: 'Planificador de demostración',
    email: 'planificador@siprim.demo',
    rol: 'PLANNER',
    demoPassword: 'demo2026',
  },
] as const

function publicUser(account: DemoAccount): AuthUser {
  const { demoPassword: _demoPassword, ...user } = account
  return user
}

export const DEMO_USERS: readonly AuthUser[] = DEMO_ACCOUNTS.map(publicUser)

export function authenticateDemoUser(credentials: LoginCredentials): AuthUser | null {
  const email = credentials.email.trim().toLowerCase()
  const account = DEMO_ACCOUNTS.find(
    (candidate) =>
      candidate.email.toLowerCase() === email &&
      candidate.demoPassword === credentials.password,
  )
  return account ? publicUser(account) : null
}

export function getDemoUser(userId: string): AuthUser | null {
  const account = DEMO_ACCOUNTS.find((candidate) => candidate.id === userId)
  return account ? publicUser(account) : null
}

export function getDemoCredentials(role: AuthUser['rol']): LoginCredentials {
  const account = DEMO_ACCOUNTS.find((candidate) => candidate.rol === role)
  if (!account) throw new Error('Perfil de demostración no disponible.')
  return { email: account.email, password: account.demoPassword }
}
