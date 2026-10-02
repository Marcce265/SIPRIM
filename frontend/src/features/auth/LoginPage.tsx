import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import { getDemoCredentials } from '../../simulation/demoUsers'
import type { UserRole } from '../../types/auth'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    const message = await login({ email, password })
    setLoading(false)

    if (message) {
      setError(message)
      return
    }

    navigate(from, { replace: true })
  }

  const accessAs = async (role: UserRole) => {
    setError(null)
    setLoading(true)
    const credentials = getDemoCredentials(role)
    const message = await login(credentials)
    setLoading(false)
    if (message) {
      setError(message)
      return
    }
    navigate(from, { replace: true })
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <header className="login-header">
          <span className="login-mark" aria-hidden>
            S
          </span>
          <div>
            <h1>SIPRIM</h1>
            <p>Acceso al sistema de priorización municipal</p>
          </div>
        </header>

        <p className="login-context">
          Taller de Proyectos · PMV 1
        </p>

        <div className="demo-mode-callout">
          <strong>Modo demostración</strong>
          <span>Seleccione un perfil para recorrer la simulación sin backend.</span>
        </div>

        <div className="profile-buttons" aria-label="Perfiles de demostración">
          <button type="button" onClick={() => accessAs('PLANNER')} disabled={loading}>
            <strong>Planificador</strong>
            <span>Registra, edita y evalúa proyectos</span>
          </button>
          <button type="button" onClick={() => accessAs('ADMIN')} disabled={loading}>
            <strong>Administrador</strong>
            <span>Configura umbrales económicos</span>
          </button>
        </div>

        <div className="login-divider"><span>o ingrese las credenciales demo</span></div>

        <form className="login-form" onSubmit={onSubmit} noValidate>
          {error && <Alert variant="error">{error}</Alert>}

          <FormField
            label="Correo institucional"
            type="email"
            autoComplete="username"
            value={email}
            placeholder="planificador@siprim.demo"
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <FormField
            label="Contraseña"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? 'Ingresando…' : 'Ingresar al sistema'}
          </button>
        </form>

        <footer className="login-footer">
          <p className="login-demo-hint">Contraseña de ambos perfiles: <code>demo2026</code></p>
          <p>No se almacenan contraseñas ni tokens en <code>localStorage</code>. Esto no representa autenticación real del servidor.</p>
        </footer>
      </div>
    </div>
  )
}
