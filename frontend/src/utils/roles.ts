export const SUPERADMIN_ROLE = 'SUPERADMIN'

export function roleGrantsAccess(userRoles: string[], requiredRole: string): boolean {
  if (userRoles.includes(SUPERADMIN_ROLE)) return true
  return userRoles.includes(requiredRole)
}

export function roleGrantsAny(userRoles: string[], anyOf: string[]): boolean {
  if (userRoles.includes(SUPERADMIN_ROLE)) return true
  return anyOf.some((role) => userRoles.includes(role))
}
