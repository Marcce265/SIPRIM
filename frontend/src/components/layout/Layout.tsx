import { NavLink, Outlet } from 'react-router-dom'
import { useApiHealth } from '../../hooks/useApiHealth'
import { ApiStatusPill } from './ApiStatusPill'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link active' : 'nav-link'

export function Layout() {
  const apiOnline = useApiHealth()

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
          </nav>
          <ApiStatusPill apiOnline={apiOnline} />
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>
          PMV1 · Municipalidad Distrital de El Tambo · Soporte a la preevaluación
          multidimensional (Invierte.pe)
        </p>
        <p className="footer-muted">
          Las decisiones finales permanecen en manos de las autoridades y especialistas
          municipales.
        </p>
      </footer>
    </div>
  )
}
