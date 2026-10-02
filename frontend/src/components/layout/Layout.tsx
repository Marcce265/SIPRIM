import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../features/auth/AuthContext'
import { simulationRepository } from '../../simulation/repository'
import { useSimulation } from '../../simulation/useSimulation'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link active' : 'nav-link'

export function Layout() {
  const { user, logout } = useAuth()
  const { recoveryNotice, clearRecoveryNotice } = useSimulation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const restoreData = () => {
    const confirmed = window.confirm(
      'Se borrarán los cambios locales y se restaurarán los proyectos A y B. ¿Continuar?',
    )
    if (confirmed) {
      simulationRepository.restoreSeedData()
      navigate('/', { replace: true, state: { restored: true } })
    }
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
                Simulación académica de proyectos municipales
              </p>
            </div>
          </div>
          <nav className="main-nav" aria-label="Principal">
            <NavLink to="/" end className={navLinkClass}>
              Inicio
            </NavLink>
            <NavLink to="/proyectos" className={navLinkClass}>
              Proyectos
            </NavLink>
            {user?.rol === 'PLANNER' && (
              <NavLink to="/proyectos/nuevo" className={navLinkClass}>Registrar</NavLink>
            )}
            {user?.rol === 'ADMIN' && (
              <NavLink to="/criterios" className={navLinkClass}>Criterios</NavLink>
            )}
          </nav>
          <div className="user-menu">
            <span className="demo-pill">Modo demostración</span>
            {user && (
              <>
                <div className="user-info">
                  <p className="user-name">{user.nombre}</p>
                  <p className="user-role">{user.rol === 'ADMIN' ? 'Administrador' : 'Planificador'}</p>
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
        {recoveryNotice && (
          <div className="recovery-banner" role="status">
            <span>{recoveryNotice}</span>
            <button type="button" onClick={clearRecoveryNotice}>Cerrar</button>
          </div>
        )}
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>
          PMV 1 · Modo demostración · Datos guardados localmente en este navegador
        </p>
        <p className="footer-muted">
          Simulación universitaria. La puntuación no constituye viabilidad ni decisión municipal.
        </p>
        <button type="button" className="footer-reset" onClick={restoreData}>Restaurar datos iniciales</button>
      </footer>
    </div>
  )
}
