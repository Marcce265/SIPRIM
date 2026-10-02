import { Navigate, Outlet } from 'react-router-dom'
import type { UserRole } from '../../types/auth'
import { useAuth } from './AuthContext'

export function RoleRoute({ role }: { role: UserRole }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.rol !== role) return <Navigate to="/" replace />
  return <Outlet />
}
