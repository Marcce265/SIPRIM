import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import { GuestRoute } from '../features/auth/GuestRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { RoleRoute } from '../features/auth/RoleRoute'
import { CriteriaPage } from '../features/criteria/CriteriaPage'
import { HomePage } from '../features/home/HomePage'
import { EditProjectPage } from '../features/projects/EditProjectPage'
import { ProjectDetailPage } from '../features/projects/ProjectDetailPage'
import { ProjectListPage } from '../features/projects/ProjectListPage'
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
          <Route path="proyectos" element={<ProjectListPage />} />
          <Route path="proyectos/:projectId" element={<ProjectDetailPage />} />
          <Route element={<RoleRoute role="PLANNER" />}>
            <Route path="proyectos/nuevo" element={<RegistrarPage />} />
            <Route path="proyectos/:projectId/editar" element={<EditProjectPage />} />
          </Route>
          <Route element={<RoleRoute role="ADMIN" />}>
            <Route path="criterios" element={<CriteriaPage />} />
          </Route>
          <Route path="registrar" element={<Navigate to="/proyectos/nuevo" replace />} />
          <Route path="consultar" element={<Navigate to="/proyectos" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
