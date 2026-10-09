import { Navigate, Outlet } from 'react-router-dom'
import { roleGrantsAny } from '../../utils/roles'
import { useAuth } from './AuthContext'

interface RoleRouteProps {
  anyOf: string[]
}

export function RoleRoute({ anyOf }: RoleRouteProps) {
  const { user } = useAuth()
  const allowed = roleGrantsAny(user?.roles ?? [], anyOf)

  if (!allowed) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
