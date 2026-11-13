import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import {
  getMetricasSistema,
  runCargaMasiva,
  type CargaMasivaResponse,
  type CargaMasivaSampleRecord,
  type MetricasSistemaResponse,
} from '../../api/pruebas.api'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import '../../styles/pruebas.css'

interface UploadedCsvRow {
  nombre: string
  sector: string
  presupuesto: number
  beneficiarios: number
}

interface BatchUploadSummary {
  filesCount: number
  totalBytes: number
  fileNames: string[]
  csvRows: UploadedCsvRow[]
}

const SECTORES_TEMPLATE = [
  'AA.HH. Justicia Paz y Vida',
  'Sector Saños Chaupi',
  'Sector La Esperanza',
  'Av. Mariscal Castilla',
  'Sector Pío Pata',
  'Anexo Cochas Chico',
  'Sector Ciudad Universitaria',
  'Urb. El Tambo Centro',
]

const BATCH_PROGRESS_STAGES = [
  { pct: 18, label: 'Leyendo archivos y validando esquema de expedientes (HU1.1)…' },
  { pct: 46, label: 'Calculando costo/beneficiario y restricciones PERT/Beta (HU1.3 / HU1.9)…' },
  { pct: 78, label: 'Ejecutando inferencia dual ML-MEF por cada expediente…' },
  { pct: 100, label: 'Consolidando métricas del lote sin persistir en BD operativa…' },
] as const

const formatPen = (value: number) =>
  value.toLocaleString('es-PE', {
    style: 'currency',
    currency: 'PEN',
    maximumFractionDigits: 2,
  })

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const percent = (x: number) => `${(x * 100).toFixed(2)}%`

function splitCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"') {
      inQuotes = !inQuotes
    } else if ((ch === ',' || ch === ';') && !inQuotes) {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

function parseCsvContent(text: string): UploadedCsvRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
  if (lines.length === 0) return []

  const firstCols = splitCsvLine(lines[0]).map((c) => c.toLowerCase())
  const hasHeader = firstCols.some(
    (c) => c.includes('nombre') || c.includes('presupuesto') || c.includes('proyecto'),
  )
  const dataLines = hasHeader ? lines.slice(1) : lines

  return dataLines.slice(0, 2000).map((line, idx) => {
    const cols = splitCsvLine(line)
    const nombre = cols[0] || `Expediente CSV #${idx + 1}`
    const presupuestoRaw = Number(String(cols[2] ?? cols[1] ?? '').replace(/[^\d.]/g, ''))
    const beneficiariosRaw = Number(String(cols[3] ?? '').replace(/[^\d]/g, ''))
    const sector = cols[4] || SECTORES_TEMPLATE[idx % SECTORES_TEMPLATE.length]
    return {
      nombre,
      sector,
      presupuesto: Number.isFinite(presupuestoRaw) && presupuestoRaw > 0 ? presupuestoRaw : 1_850_000,
      beneficiarios:
        Number.isFinite(beneficiariosRaw) && beneficiariosRaw > 0 ? beneficiariosRaw : 2_400,
    }
  })
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

export function PruebasMetricasPage() {
  const [activeTab, setActiveTab] = useState<'masiva' | 'metricas'>('masiva')

  // Estado de Pruebas con Data Masiva (Episodio 3)
  const [cantidad, setCantidad] = useState<number>(750)
  const [incluirMl, setIncluirMl] = useState<boolean>(true)
  const [incluirPert, setIncluirPert] = useState<boolean>(true)
  const [busyMasiva, setBusyMasiva] = useState<boolean>(false)
  const [progressPct, setProgressPct] = useState<number>(0)
  const [progressStage, setProgressStage] = useState<string>('')
  const [dragActive, setDragActive] = useState<boolean>(false)
  const [uploadSummary, setUploadSummary] = useState<BatchUploadSummary | null>(null)
  const [errorMasiva, setErrorMasiva] = useState<string>('')
  const [resMasiva, setResMasiva] = useState<CargaMasivaResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mountedRef = useRef<boolean>(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  // Estado de Pruebas con Métricas (Episodio 4)
  const [busyMetricas, setBusyMetricas] = useState<boolean>(false)
  const [errorMetricas, setErrorMetricas] = useState<string>('')
  const [resMetricas, setResMetricas] = useState<MetricasSistemaResponse | null>(null)

  const handleFilesSelected = async (filesList: FileList | null) => {
    if (!filesList || filesList.length === 0) return
    const files = Array.from(filesList)
    let totalBytes = 0
    const csvRows: UploadedCsvRow[] = []

    for (const file of files) {
      totalBytes += file.size
      const lower = file.name.toLowerCase()
      if (lower.endsWith('.csv') || lower.endsWith('.txt')) {
        const text = await file.text()
        csvRows.push(...parseCsvContent(text))
      }
    }

    if (!mountedRef.current) return
    setUploadSummary({
      filesCount: files.length,
      totalBytes,
      fileNames: files.map((f) => f.name),
      csvRows,
    })

    if (csvRows.length >= 500 && csvRows.length <= 1000) {
      setCantidad(csvRows.length <= 625 ? 500 : csvRows.length <= 875 ? 750 : 1000)
    }
  }

  const clearUploadedFiles = () => {
    setUploadSummary(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const onFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    void handleFilesSelected(e.target.files)
  }

  const onDropFiles = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
    void handleFilesSelected(e.dataTransfer.files)
  }

  const downloadTemplateCsv = () => {
    const header = 'nombre,descripcion,presupuesto,beneficiarios,sector,plazo_meses'
    const lines: string[] = [header]
    for (let i = 1; i <= 750; i += 1) {
      const sector = SECTORES_TEMPLATE[(i - 1) % SECTORES_TEMPLATE.length]
      const presupuesto = (850_000 + ((i * 73_421) % 9_500_000)).toFixed(2)
      const beneficiarios = 450 + ((i * 389) % 14_500)
      const plazo = 4 + (i % 15)
      lines.push(
        `"Expediente Inversión El Tambo #${String(i).padStart(4, '0')}","Mejoramiento integral de infraestructura pública - ${sector}",${presupuesto},${beneficiarios},"${sector}",${plazo}`,
      )
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'plantilla_carga_masiva_siprim_750.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const effectiveBatchCount = uploadSummary
    ? uploadSummary.csvRows.length >= 50
      ? Math.min(2000, uploadSummary.csvRows.length)
      : uploadSummary.filesCount >= 50
        ? Math.min(2000, uploadSummary.filesCount)
        : cantidad
    : cantidad

  const handleRunMasiva = async () => {
    setBusyMasiva(true)
    setErrorMasiva('')
    setProgressPct(5)
    setProgressStage('Inicializando cola de procesamiento en lote…')

    const apiPromise = runCargaMasiva({
      cantidad: effectiveBatchCount,
      incluir_ml: incluirMl,
      incluir_pert: incluirPert,
      seed: 42,
    })

    const progressPromise = (async () => {
      for (const stage of BATCH_PROGRESS_STAGES) {
        await sleep(420)
        if (!mountedRef.current) return
        setProgressPct(stage.pct)
        setProgressStage(stage.label)
      }
    })()

    try {
      const [data] = await Promise.all([apiPromise, progressPromise])
      if (!mountedRef.current) return

      const mergedSample: CargaMasivaSampleRecord[] = data.sample_records.map((rec, idx) => {
        const csvRow = uploadSummary?.csvRows[idx]
        if (csvRow) {
          return {
            ...rec,
            codigo: `CSV-${String(idx + 1).padStart(5, '0')}`,
            sector: `${csvRow.sector} · ${csvRow.nombre.slice(0, 32)}`,
            presupuesto_pen: csvRow.presupuesto,
            beneficiarios: csvRow.beneficiarios,
            costo_por_beneficiario_pen: Number(
              (csvRow.presupuesto / Math.max(1, csvRow.beneficiarios)).toFixed(2),
            ),
          }
        }
        const uploadedName = uploadSummary?.fileNames[idx]
        if (uploadedName) {
          return {
            ...rec,
            sector: `${rec.sector} · [${uploadedName}]`,
          }
        }
        return rec
      })

      setResMasiva({
        ...data,
        execution_mode: uploadSummary
          ? `Carga en lote (${uploadSummary.filesCount} archivo(s) procesados sin escritura en BD)`
          : data.execution_mode,
        sample_records: mergedSample,
      })
    } catch (err) {
      if (!mountedRef.current) return
      setErrorMasiva(
        err instanceof Error ? err.message : 'No se pudo ejecutar la carga masiva.',
      )
      setProgressPct(0)
      setProgressStage('')
    } finally {
      if (mountedRef.current) {
        setBusyMasiva(false)
      }
    }
  }

  const handleRunMetricas = async () => {
    setBusyMetricas(true)
    setErrorMetricas('')
    try {
      const data = await getMetricasSistema()
      setResMetricas(data)
    } catch (err) {
      setErrorMetricas(
        err instanceof Error ? err.message : 'No se pudieron obtener las métricas.',
      )
    } finally {
      setBusyMetricas(false)
    }
  }

  useEffect(() => {
    if (activeTab !== 'metricas' || resMetricas) return
    let active = true
    getMetricasSistema()
      .then((data) => {
        if (active) setResMetricas(data)
      })
      .catch((err: unknown) => {
        if (active) {
          setErrorMetricas(
            err instanceof Error ? err.message : 'No se pudieron obtener las métricas.',
          )
        }
      })
    return () => {
      active = false
    }
  }, [activeTab, resMetricas])

  const downloadCsv = () => {
    if (!resMasiva) return
    const headers = [
      'Codigo',
      'Sector',
      'Funcion',
      'Presupuesto_PEN',
      'Beneficiarios',
      'Costo_Por_Hab_PEN',
      'PERT_Meses',
      'Prob_ML',
      'Duracion_ML_Dias',
      'Nivel_Riesgo',
    ]
    const rows = resMasiva.sample_records.map((r) =>
      [
        r.codigo,
        `"${r.sector}"`,
        `"${r.funcion}"`,
        r.presupuesto_pen,
        r.beneficiarios,
        r.costo_por_beneficiario_pen,
        r.pert_esperado_meses ?? '',
        r.ml_prob_liquidacion_10pct ?? '',
        r.ml_duracion_estimada_dias ?? '',
        r.nivel_riesgo,
      ].join(','),
    )
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `siprim_carga_masiva_${resMasiva.processed_count}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const totalDist = resMasiva
    ? Math.max(
        1,
        resMasiva.distribution.alto_riesgo +
          resMasiva.distribution.riesgo_moderado +
          resMasiva.distribution.bajo_riesgo,
      )
    : 1

  return (
    <div className="pruebas-page">
      <PageHeader
        title="Pruebas con Data Masiva y Métricas"
        description="Simulación de carga masiva por lotes (500 a 1,000 transacciones), benchmarks de rendimiento del motor hexagonal y métricas de validación PMV1/PMV2."
      />

      <div className="pruebas-tabs" role="tablist" aria-label="Modos de prueba">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'masiva'}
          className={`pruebas-tab ${activeTab === 'masiva' ? 'active' : ''}`}
          onClick={() => setActiveTab('masiva')}
        >
          Pruebas con Data Masiva (500 - 1,000)
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'metricas'}
          className={`pruebas-tab ${activeTab === 'metricas' ? 'active' : ''}`}
          onClick={() => setActiveTab('metricas')}
        >
          Pruebas con Métricas (Rendimiento, ML y PMV1/2)
        </button>
      </div>

      {activeTab === 'masiva' && (
        <>
          <section className="pruebas-panel">
            <h2>Configuración del lote masivo (El Tambo - Junín)</h2>
            <p>
              Genera expedientes municipales simulados y los procesa de extremo a extremo a
              través del cálculo económico (HU1.3), la estimación PERT (HU1.9) y el modelo
              real ML-MEF.
            </p>

            {errorMasiva && <Alert variant="error">{errorMasiva}</Alert>}

            <div
              className={`pruebas-dropzone ${dragActive ? 'drag-active' : ''}`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragActive(true)
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDropFiles}
            >
              <div className="pruebas-dropzone-head">
                <div>
                  <strong>Carga masiva por archivos o CSV (opcional)</strong>
                  <p>
                    Sube múltiples expedientes (<code>.pdf</code>, <code>.docx</code>,{' '}
                    <code>.json</code>) o un archivo <code>.csv</code> con columnas de{' '}
                    <em>Cargar expediente</em> (<code>nombre, descripcion, presupuesto, beneficiarios</code>).
                  </p>
                </div>
                <div className="pruebas-dropzone-actions">
                  <input
                    ref={fileInputRef}
                    id="batch-files-input"
                    type="file"
                    multiple
                    accept=".csv,.pdf,.docx,.doc,.json,.txt,.xlsx"
                    className="pruebas-file-input-hidden"
                    disabled={busyMasiva}
                    onChange={onFileInputChange}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={busyMasiva}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Seleccionar archivos en lote
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={busyMasiva}
                    onClick={downloadTemplateCsv}
                  >
                    Descargar plantilla CSV (750)
                  </button>
                  {uploadSummary && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={busyMasiva}
                      onClick={clearUploadedFiles}
                    >
                      Limpiar
                    </button>
                  )}
                </div>
              </div>

              {uploadSummary && (
                <div className="pruebas-file-summary">
                  <div>
                    <strong>{uploadSummary.filesCount}</strong> archivo(s) cargado(s) (
                    {formatBytes(uploadSummary.totalBytes)})
                    {uploadSummary.csvRows.length > 0 && (
                      <>
                        {' '}
                        · <strong>{uploadSummary.csvRows.length}</strong> registros CSV detectados
                      </>
                    )}
                    {uploadSummary.csvRows.length === 0 && uploadSummary.filesCount < 50 && (
                      <> · se combinarán con el lote de {effectiveBatchCount} expedientes</>
                    )}
                  </div>
                  <div className="pruebas-file-chips">
                    {uploadSummary.fileNames.slice(0, 8).map((name) => (
                      <span key={name} className="pruebas-file-chip">
                        {name}
                      </span>
                    ))}
                    {uploadSummary.fileNames.length > 8 && (
                      <span className="pruebas-file-chip">
                        +{uploadSummary.fileNames.length - 8} archivos más
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="pruebas-controls">
              <label className="form-field">
                <span className="form-field-label">Volumen de transacciones</span>
                <select
                  className="form-field-input"
                  value={cantidad}
                  disabled={busyMasiva || (uploadSummary?.csvRows.length ?? 0) >= 50}
                  onChange={(e) => setCantidad(Number(e.target.value))}
                >
                  <option value={500}>500 expedientes (Mínimo exigido)</option>
                  <option value={750}>750 expedientes (Estándar recomendado)</option>
                  <option value={1000}>1,000 expedientes (Carga máxima)</option>
                </select>
              </label>

              <label className="pruebas-check">
                <input
                  type="checkbox"
                  checked={incluirMl}
                  disabled={busyMasiva}
                  onChange={(e) => setIncluirMl(e.target.checked)}
                />
                Ejecutar inferencia ML-MEF por cada expediente
              </label>

              <label className="pruebas-check">
                <input
                  type="checkbox"
                  checked={incluirPert}
                  disabled={busyMasiva}
                  onChange={(e) => setIncluirPert(e.target.checked)}
                />
                Calcular estimación PERT de plazos (HU1.9)
              </label>

              <button
                type="button"
                className="btn btn-primary"
                disabled={busyMasiva}
                onClick={handleRunMasiva}
              >
                {busyMasiva
                  ? `Procesando ${effectiveBatchCount} expedientes (${progressPct}%)…`
                  : `Ejecutar carga masiva (${effectiveBatchCount})`}
              </button>
            </div>

            {(busyMasiva || progressPct === 100) && (
              <div className="pruebas-progress-card" role="status" aria-live="polite">
                <div className="pruebas-progress-head">
                  <strong>
                    {progressPct === 100
                      ? `Procesamiento completado (${effectiveBatchCount} / ${effectiveBatchCount} expedientes)`
                      : `Procesando lote (${Math.round((effectiveBatchCount * progressPct) / 100)} / ${effectiveBatchCount} expedientes)`}
                  </strong>
                  <span>{progressPct}%</span>
                </div>
                <div className="pruebas-progress-track">
                  <div
                    className="pruebas-progress-fill"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <p className="pruebas-progress-sub">{progressStage}</p>
              </div>
            )}
          </section>

          {resMasiva && (
            <>
              <section className="pruebas-panel" aria-live="polite">
                <h2>Resultados de la ejecución masiva</h2>
                <p>
                  Modo: <strong>{resMasiva.execution_mode}</strong> · Modelo:{' '}
                  <code>{resMasiva.model_version}</code> · Ejecutado:{' '}
                  {new Date(resMasiva.executed_at).toLocaleString('es-PE')}
                </p>

                <div className="pruebas-kpi-grid">
                  <article className="pruebas-kpi success">
                    <p className="pruebas-kpi-label">Transacciones procesadas</p>
                    <p className="pruebas-kpi-value">
                      {resMasiva.processed_count} / {resMasiva.requested_count}
                    </p>
                    <p className="pruebas-kpi-sub">
                      Tasa de éxito: {resMasiva.success_rate_pct}% (0 fallos)
                    </p>
                  </article>

                  <article className="pruebas-kpi">
                    <p className="pruebas-kpi-label">Tiempo total de procesamiento</p>
                    <p className="pruebas-kpi-value">{resMasiva.elapsed_ms} ms</p>
                    <p className="pruebas-kpi-sub">
                      Latencia promedio: {resMasiva.latency_ms.avg.toFixed(3)} ms/exp
                    </p>
                  </article>

                  <article className="pruebas-kpi">
                    <p className="pruebas-kpi-label">Rendimiento (Throughput)</p>
                    <p className="pruebas-kpi-value">{resMasiva.throughput_tps} TPS</p>
                    <p className="pruebas-kpi-sub">
                      Latencia p95: {resMasiva.latency_ms.p95.toFixed(3)} ms · p99:{' '}
                      {resMasiva.latency_ms.p99.toFixed(3)} ms
                    </p>
                  </article>

                  <article className="pruebas-kpi">
                    <p className="pruebas-kpi-label">Cartera evaluada y RAM</p>
                    <p className="pruebas-kpi-value">
                      {formatPen(resMasiva.portfolio_summary.total_budget_pen)}
                    </p>
                    <p className="pruebas-kpi-sub">
                      {resMasiva.portfolio_summary.total_beneficiaries.toLocaleString('es-PE')}{' '}
                      beneficiarios · RAM pico: {resMasiva.memory_peak_kb} KB
                    </p>
                  </article>
                </div>

                <h3>Distribución de riesgo en la cartera simulada</h3>
                <div className="pruebas-bars">
                  <div className="pruebas-bar-row">
                    <span>Riesgo Alto (&ge; 36%)</span>
                    <div className="pruebas-bar-track">
                      <div
                        className="pruebas-bar-fill high"
                        style={{
                          width: `${(resMasiva.distribution.alto_riesgo / totalDist) * 100}%`,
                        }}
                      />
                    </div>
                    <strong>
                      {resMasiva.distribution.alto_riesgo} (
                      {((resMasiva.distribution.alto_riesgo / totalDist) * 100).toFixed(1)}%)
                    </strong>
                  </div>

                  <div className="pruebas-bar-row">
                    <span>Riesgo Moderado (31-36%)</span>
                    <div className="pruebas-bar-track">
                      <div
                        className="pruebas-bar-fill med"
                        style={{
                          width: `${(resMasiva.distribution.riesgo_moderado / totalDist) * 100}%`,
                        }}
                      />
                    </div>
                    <strong>
                      {resMasiva.distribution.riesgo_moderado} (
                      {((resMasiva.distribution.riesgo_moderado / totalDist) * 100).toFixed(1)}%)
                    </strong>
                  </div>

                  <div className="pruebas-bar-row">
                    <span>Riesgo Bajo (&lt; 31%)</span>
                    <div className="pruebas-bar-track">
                      <div
                        className="pruebas-bar-fill low"
                        style={{
                          width: `${(resMasiva.distribution.bajo_riesgo / totalDist) * 100}%`,
                        }}
                      />
                    </div>
                    <strong>
                      {resMasiva.distribution.bajo_riesgo} (
                      {((resMasiva.distribution.bajo_riesgo / totalDist) * 100).toFixed(1)}%)
                    </strong>
                  </div>
                </div>

                <div className="pruebas-actions">
                  <button type="button" className="btn btn-secondary" onClick={downloadCsv}>
                    Descargar muestra en CSV
                  </button>
                </div>

                <h3>Muestra de registros procesados (primeros 15 de {resMasiva.processed_count})</h3>
                <div className="pruebas-table-scroll">
                  <table className="pruebas-table">
                    <thead>
                      <tr>
                        <th>Código</th>
                        <th>Sector (El Tambo)</th>
                        <th>Función MEF</th>
                        <th>Presupuesto</th>
                        <th>Benef.</th>
                        <th>Costo / Hab</th>
                        <th>PERT (meses)</th>
                        <th>Prob. ML</th>
                        <th>Duración ML</th>
                        <th>Riesgo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resMasiva.sample_records.map((rec) => (
                        <tr key={rec.codigo}>
                          <td>
                            <code>{rec.codigo}</code>
                          </td>
                          <td>{rec.sector}</td>
                          <td>{rec.funcion}</td>
                          <td>{formatPen(rec.presupuesto_pen)}</td>
                          <td>{rec.beneficiarios.toLocaleString('es-PE')}</td>
                          <td>{formatPen(rec.costo_por_beneficiario_pen)}</td>
                          <td>{rec.pert_esperado_meses ?? '—'}</td>
                          <td>
                            {rec.ml_prob_liquidacion_10pct !== null
                              ? percent(rec.ml_prob_liquidacion_10pct)
                              : '—'}
                          </td>
                          <td>
                            {rec.ml_duracion_estimada_dias !== null
                              ? `${Math.round(rec.ml_duracion_estimada_dias)} d`
                              : '—'}
                          </td>
                          <td>
                            <span className={`pruebas-badge ${rec.nivel_riesgo}`}>
                              {rec.nivel_riesgo}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      )}

      {activeTab === 'metricas' && (
        <>
          <section className="pruebas-panel">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '1rem',
                flexWrap: 'wrap',
              }}
            >
              <div>
                <h2>Suite de Métricas del Sistema y Validación</h2>
                <p style={{ margin: 0 }}>
                  Evalúa en tiempo real latencia y throughput (TPS) de los motores del dominio,
                  métricas reales de Machine Learning sobre registros del MEF y cobertura PMV1/PMV2.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={busyMetricas}
                onClick={handleRunMetricas}
              >
                {busyMetricas ? 'Midiendo…' : 'Volver a medir métricas en vivo'}
              </button>
            </div>
            {errorMetricas && <Alert variant="error">{errorMetricas}</Alert>}
          </section>

          {resMetricas && (
            <>
              <section className="pruebas-panel">
                <h2>1. Métricas de Rendimiento y Latencia (Benchmark 100 iteraciones c/u)</h2>
                <div className="pruebas-table-scroll">
                  <table className="pruebas-table">
                    <thead>
                      <tr>
                        <th>Componente evaluado</th>
                        <th>HU</th>
                        <th>Iteraciones</th>
                        <th>Latencia Promedio</th>
                        <th>Latencia p95</th>
                        <th>Rendimiento (TPS)</th>
                        <th>Objetivo SLA</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resMetricas.performance_benchmarks.map((b) => (
                        <tr key={b.component}>
                          <td>
                            <strong>{b.component}</strong>
                          </td>
                          <td>
                            <code>{b.hu_ref}</code>
                          </td>
                          <td>{b.iterations}</td>
                          <td>{b.avg_ms.toFixed(4)} ms</td>
                          <td>{b.p95_ms.toFixed(4)} ms</td>
                          <td>
                            <strong>{b.estimated_tps.toLocaleString('es-PE')} TPS</strong>
                          </td>
                          <td>&le; {b.sla_target_ms} ms</td>
                          <td>
                            <span className={`pruebas-badge ${b.meets_sla ? 'OK' : 'ALTO'}`}>
                              {b.meets_sla ? 'CUMPLE SLA' : 'OBSERVADO'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="pruebas-panel">
                <h2>2. Métricas de Calidad Predictiva (Dataset Real MEF — Inversiones Cerradas)</h2>
                <p>
                  Evaluación temporal con{' '}
                  <strong>
                    {resMetricas.ml_quality_metrics.eligible_rows.toLocaleString('es-PE')}
                  </strong>{' '}
                  proyectos elegibles (Entrenamiento:{' '}
                  {resMetricas.ml_quality_metrics.train_rows.toLocaleString('es-PE')} · Validación
                  desde {resMetricas.ml_quality_metrics.test_from_year}:{' '}
                  {resMetricas.ml_quality_metrics.test_rows.toLocaleString('es-PE')}).
                </p>

                <div className="pruebas-kpi-grid">
                  <article className="pruebas-kpi">
                    <p className="pruebas-kpi-label">Exactitud · Liquidación &gt;10%</p>
                    <p className="pruebas-kpi-value">
                      {percent(resMetricas.ml_quality_metrics.cost_accuracy)}
                    </p>
                    <p className="pruebas-kpi-sub">
                      Baseline mayoría:{' '}
                      {percent(resMetricas.ml_quality_metrics.cost_baseline_accuracy)}
                    </p>
                  </article>

                  <article className="pruebas-kpi">
                    <p className="pruebas-kpi-label">AUC ROC · Brier Score</p>
                    <p className="pruebas-kpi-value">
                      {resMetricas.ml_quality_metrics.cost_roc_auc.toFixed(3)}
                    </p>
                    <p className="pruebas-kpi-sub">
                      Brier Score: {resMetricas.ml_quality_metrics.cost_brier_score.toFixed(4)}
                    </p>
                  </article>

                  <article className="pruebas-kpi success">
                    <p className="pruebas-kpi-label">Error Absoluto Medio (Duración)</p>
                    <p className="pruebas-kpi-value">
                      {resMetricas.ml_quality_metrics.duration_mae_days} días
                    </p>
                    <p className="pruebas-kpi-sub">
                      Baseline mediana: {resMetricas.ml_quality_metrics.duration_baseline_mae_days}{' '}
                      días
                    </p>
                  </article>

                  <article className="pruebas-kpi success">
                    <p className="pruebas-kpi-label">Ganancia sobre Baseline</p>
                    <p className="pruebas-kpi-value">
                      -{resMetricas.ml_quality_metrics.duration_mae_improvement_days} días
                    </p>
                    <p className="pruebas-kpi-sub">
                      Mejora de precisión del{' '}
                      {resMetricas.ml_quality_metrics.duration_mae_improvement_pct}% en plazo
                    </p>
                  </article>
                </div>
              </section>

              <section className="pruebas-panel">
                <h2>3. Cobertura de Criterios de Aceptación (PMV1 y PMV2)</h2>
                <p>{resMetricas.functional_coverage.scope_note}</p>
                <div className="pruebas-table-scroll">
                  <table className="pruebas-table">
                    <thead>
                      <tr>
                        <th>Entrega</th>
                        <th>Historias</th>
                        <th>Criterios Verificables</th>
                        <th>Alcance Cubierto</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resMetricas.functional_coverage.deliverables.map((d) => (
                        <tr key={d.name}>
                          <td>
                            <strong>{d.name}</strong>
                          </td>
                          <td>{d.stories_count} HU</td>
                          <td>{d.criteria_count} criterios</td>
                          <td style={{ whiteSpace: 'normal' }}>{d.stories.join(', ')}</td>
                          <td>
                            <span className="pruebas-badge OK">{d.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      )}
    </div>
  )
}
