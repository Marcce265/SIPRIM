import { BrowserRouter } from 'react-router-dom'
import { ErrorBoundary } from '../components/ui/ErrorBoundary'
import { AuthProvider } from '../features/auth/AuthContext'
import { AppRoutes } from './routes'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
