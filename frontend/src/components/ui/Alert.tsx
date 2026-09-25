import type { ReactNode } from 'react'

type AlertVariant = 'error' | 'success'

interface AlertProps {
  variant: AlertVariant
  children: ReactNode
}

export function Alert({ variant, children }: AlertProps) {
  const role = variant === 'error' ? 'alert' : 'status'
  return (
    <div className={`alert alert-${variant}`} role={role}>
      {children}
    </div>
  )
}
