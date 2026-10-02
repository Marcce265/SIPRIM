import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import { useApiHealth } from '../../hooks/useApiHealth'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const apiOnline = useApiHealth()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const message = await login({ email, password })
      if (message) {
        setError(message)
        return
      }
      navigate(from, { replace: true })
    } finally {
      setLoading(false)
    }
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
            <p>Sistema de priorización de inversiones municipales</p>
          </div>
        </header>

        <p className="login-context">Municipalidad Distrital de El Tambo · Junín</p>

        {apiOnline === false && (
          <Alert variant="error">
            El servicio no está disponible en este momento. Intente más tarde o contacte a
            informática municipal.
          </Alert>
        )}

        <form className="login-form" onSubmit={onSubmit} noValidate>
          {error && <Alert variant="error">{error}</Alert>}

          <FormField
            label="Correo institucional"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="usuario@eltambo.gob.pe"
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

          <button
            type="submit"
            className="btn btn-primary login-submit"
            disabled={loading || apiOnline === false}
          >
            {loading ? 'Ingresando…' : 'Ingresar al sistema'}
          </button>
        </form>

        <footer className="login-footer">
          <p>
            Acceso restringido al personal autorizado. Las credenciales las entrega la
            municipalidad.
          </p>
        </footer>
      </div>
    </div>
  )
}
