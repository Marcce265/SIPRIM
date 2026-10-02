import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import { AprobacionPage } from '../features/aprobacion/AprobacionPage'
import { GuestRoute } from '../features/auth/GuestRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { RoleRoute } from '../features/auth/RoleRoute'
import { ConsultarPage } from '../features/consultar/ConsultarPage'
import { HomePage } from '../features/home/HomePage'
import { NormativaPage } from '../features/normativa/NormativaPage'
import { ProyectoDetallePage } from '../features/proyecto/ProyectoDetallePage'
import { RegistrarPage } from '../features/registrar/RegistrarPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="registrar" element={<RegistrarPage />} />
          <Route path="consultar" element={<ConsultarPage />} />
          <Route path="proyectos/:projectId" element={<ProyectoDetallePage />} />

          <Route element={<RoleRoute anyOf={['LEGAL_ADVISOR']} />}>
            <Route path="normativa" element={<NormativaPage />} />
          </Route>

          <Route element={<RoleRoute anyOf={['ADMIN']} />}>
            <Route path="proyectos/:projectId/aprobacion" element={<AprobacionPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
