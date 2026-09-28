import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
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
          Municipalidad Distrital de El Tambo · PMV1
        </p>

        <form className="login-form" onSubmit={onSubmit} noValidate>
          {error && <Alert variant="error">{error}</Alert>}

          <FormField
            label="Correo institucional"
            type="email"
            autoComplete="username"
            value={email}
            placeholder="planificador@eltambo.gob.pe"
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
          <p className="login-demo-hint">
            Demo PMV1: <code>planificador@eltambo.gob.pe</code> / <code>siprim2026</code>
          </p>
          <p>Las credenciales reales se integrarán con el backend (RNF-03).</p>
        </footer>
      </div>
    </div>
  )
}
