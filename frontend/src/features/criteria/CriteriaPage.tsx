import { useState, type FormEvent } from 'react'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import { PageHeader } from '../../components/ui/PageHeader'
import { simulationRepository } from '../../simulation/repository'
import { useSimulation } from '../../simulation/useSimulation'
import { formatCurrencyPrecise, formatDate } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'

export function CriteriaPage() {
  const { state } = useSimulation()
  const { user } = useAuth()
  const active = state.criteriaVersions.find((item) => item.estado === 'activo')!
  const [excellent, setExcellent] = useState(String(active.costoExcelente))
  const [unacceptable, setUnacceptable] = useState(String(active.costoInaceptable))
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    try {
      if (!user) throw new Error('Sesión no disponible.')
      const criteria = simulationRepository.activateCriteria(
        Number(excellent),
        Number(unacceptable),
        user,
      )
      setMessage(`Criterios v${criteria.numero} activados. Las evaluaciones anteriores no cambiaron.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo activar la configuración.')
    }
  }

  return (
    <div className="wide-page detail-stack">
      <PageHeader
        title="Criterios económicos"
        description="Configuración académica del agente económico simulado. HU03, HU11."
      />
      {message && <Alert variant="success">{message}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}
      <div className="settings-grid">
        <form className="settings-card" onSubmit={submit} noValidate>
          <p className="eyebrow">Configuración activa v{active.numero}</p>
          <h2>Activar nuevos umbrales</h2>
          <p className="settings-note">
            Se crea una versión nueva. El criterio económico conserva un peso de 100 % en este PMV.
          </p>
          <FormField
            label="Costo excelente por beneficiario (S/)"
            type="number"
            min={0.01}
            step={0.01}
            value={excellent}
            onChange={(event) => setExcellent(event.target.value)}
          />
          <FormField
            label="Costo inaceptable por beneficiario (S/)"
            type="number"
            min={0.01}
            step={0.01}
            value={unacceptable}
            onChange={(event) => setUnacceptable(event.target.value)}
          />
          <div className="fixed-weight"><span>Peso económico</span><strong>100 %</strong></div>
          <button type="submit" className="btn btn-primary">Activar configuración</button>
        </form>
        <section className="settings-card criteria-explanation">
          <p className="eyebrow">Regla aplicada</p>
          <h2>Interpolación lineal</h2>
          <ul>
            <li>Costo ≤ excelente: 100 puntos.</li>
            <li>Costo ≥ inaceptable: 0 puntos.</li>
            <li>Entre ambos: interpolación lineal.</li>
          </ul>
          <p>Es un criterio académico de comparación, no una declaración de viabilidad.</p>
        </section>
      </div>
      <section>
        <div className="section-heading"><div><p className="eyebrow">Trazabilidad</p><h2>Historial de criterios</h2></div></div>
        <div className="table-shell">
          <table className="data-table">
            <thead><tr><th>Versión</th><th>Excelente</th><th>Inaceptable</th><th>Peso</th><th>Estado</th><th>Activada</th></tr></thead>
            <tbody>
              {[...state.criteriaVersions].sort((a, b) => b.numero - a.numero).map((item) => (
                <tr key={item.id}>
                  <td><strong>v{item.numero}</strong></td>
                  <td>{formatCurrencyPrecise(item.costoExcelente)}</td>
                  <td>{formatCurrencyPrecise(item.costoInaceptable)}</td>
                  <td>{item.pesoEconomico} %</td>
                  <td><span className={`config-status ${item.estado}`}>{item.estado}</span></td>
                  <td>{formatDate(item.fechaActivacion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
