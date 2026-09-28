import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import { GuestRoute } from '../features/auth/GuestRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { ConsultarPage } from '../features/consultar/ConsultarPage'
import { HomePage } from '../features/home/HomePage'
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
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
