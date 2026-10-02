import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

interface RoleRouteProps {
  anyOf: string[]
}

export function RoleRoute({ anyOf }: RoleRouteProps) {
  const { hasRole } = useAuth()
  const allowed = anyOf.some((role) => hasRole(role))

  if (!allowed) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
