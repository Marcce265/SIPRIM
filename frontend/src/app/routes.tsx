import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import { ConsultarPage } from '../features/consultar/ConsultarPage'
import { HomePage } from '../features/home/HomePage'
import { RegistrarPage } from '../features/registrar/RegistrarPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="registrar" element={<RegistrarPage />} />
        <Route path="consultar" element={<ConsultarPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
