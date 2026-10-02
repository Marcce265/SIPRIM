import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../features/auth/AuthContext'
import { useApiHealth } from '../../hooks/useApiHealth'
import { ApiStatusPill } from './ApiStatusPill'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link active' : 'nav-link'

function formatRoles(roles: string[]): string {
  const labels: Record<string, string> = {
    PLANNER: 'Planificador',
    LEGAL_ADVISOR: 'Asesor jurídico',
    ADMIN: 'Administrador',
  }
  return roles.map((r) => labels[r] ?? r).join(' · ')
}

export function Layout() {
  const apiOnline = useApiHealth()
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden>
              S
            </span>
            <div>
              <p className="brand-title">SIPRIM</p>
              <p className="brand-subtitle">
                Priorización de proyectos de inversión municipal
              </p>
            </div>
          </div>
          <nav className="main-nav" aria-label="Principal">
            <NavLink to="/" end className={navLinkClass}>
              Inicio
            </NavLink>
            <NavLink to="/registrar" className={navLinkClass}>
              Cargar expediente
            </NavLink>
            <NavLink to="/consultar" className={navLinkClass}>
              Consultar
            </NavLink>
            {hasRole('LEGAL_ADVISOR') && (
              <NavLink to="/normativa" className={navLinkClass}>
                Normativa
              </NavLink>
            )}
          </nav>
          <div className="user-menu">
            <ApiStatusPill apiOnline={apiOnline} />
            {user && (
              <>
                <div className="user-info">
                  <p className="user-name">{user.nombre}</p>
                  <p className="user-role">{formatRoles(user.roles ?? [])}</p>
                </div>
                <button type="button" className="btn-logout" onClick={handleLogout}>
                  Cerrar sesión
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>
          Municipalidad Distrital de El Tambo · Soporte a la preevaluación de inversiones
          (Invierte.pe)
        </p>
        <p className="footer-muted">
          Las decisiones finales permanecen en manos de las autoridades y especialistas
          municipales.
        </p>
      </footer>
    </div>
  )
}
