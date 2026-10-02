import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('SIPRIM UI error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-fallback">
          <h1>Algo falló al cargar la interfaz</h1>
          <p>{this.state.error.message}</p>
          <p>
            Pruebe borrar datos locales del sitio (localStorage) o abrir{' '}
            <a href="/login">/login</a> de nuevo.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              localStorage.clear()
              window.location.href = '/login'
            }}
          >
            Limpiar datos y volver al login
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
