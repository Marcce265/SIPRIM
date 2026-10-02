import type { EconomicEvaluation } from '../../types/proyecto'
import { formatCurrencyPrecise, formatDate, formatNumber } from '../../utils/format'
import { StatusBadge } from './StatusBadge'

export function EconomicResultPanel({ evaluation }: { evaluation: EconomicEvaluation }) {
  const result = evaluation.resultado
  return (
    <article className="evaluation-card">
      <header className="evaluation-card-header">
        <div>
          <p className="eyebrow">Evaluación {evaluation.codigo}</p>
          <h3>Agente económico simulado</h3>
        </div>
        <StatusBadge status={evaluation.estado} />
      </header>

      {(evaluation.estado === 'pendiente' || evaluation.estado === 'procesando') && (
        <div className="evaluation-progress" role="status" aria-live="polite">
          <span className="spinner" aria-hidden />
          <p>
            {evaluation.estado === 'pendiente'
              ? 'La evaluación está pendiente de ejecución.'
              : 'El agente simulado está aplicando la regla económica.'}
          </p>
        </div>
      )}

      {evaluation.estado === 'fallido' && (
        <p className="inline-error">{evaluation.error ?? 'La evaluación no pudo completarse.'}</p>
      )}

      {result && (
        <>
          <dl className="result-grid">
            <div>
              <dt>Presupuesto evaluado</dt>
              <dd>{formatCurrencyPrecise(result.presupuesto)}</dd>
            </div>
            <div>
              <dt>Beneficiarios</dt>
              <dd>{formatNumber(result.beneficiarios)}</dd>
            </div>
            <div>
              <dt>Costo por beneficiario</dt>
              <dd>{formatCurrencyPrecise(result.costoPorBeneficiario)}</dd>
            </div>
            <div className="score-cell">
              <dt>Puntuación académica</dt>
              <dd>{result.puntuacion.toFixed(2)} / 100</dd>
            </div>
            <div>
              <dt>Umbral excelente</dt>
              <dd>≤ {formatCurrencyPrecise(result.costoExcelente)}</dd>
            </div>
            <div>
              <dt>Umbral inaceptable</dt>
              <dd>≥ {formatCurrencyPrecise(result.costoInaceptable)}</dd>
            </div>
            <div>
              <dt>Peso económico</dt>
              <dd>{result.pesoEconomico} %</dd>
            </div>
            <div>
              <dt>Fecha de cálculo</dt>
              <dd>{formatDate(result.fechaCalculo)}</dd>
            </div>
          </dl>
          <div className="formula-box">
            <strong>Fórmula</strong>
            <code>{result.formula}</code>
          </div>
          <p className="result-explanation">{result.explicacion}</p>
        </>
      )}
    </article>
  )
}
