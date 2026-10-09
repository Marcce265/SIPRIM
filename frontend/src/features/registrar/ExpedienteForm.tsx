import type { ChangeEvent, FormEvent } from 'react'
import { useRef } from 'react'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import type { ProjectInput } from '../../types/proyecto'
import { formatFileSize } from '../../utils/format'
import {
  PHYSICAL_EXPEDIENTE_ACCEPT,
  PHYSICAL_EXPEDIENTE_MAX_BYTES,
} from '../../utils/physicalExpedienteStorage'
import type { ProyectoFieldErrors } from './validateProyecto'

interface ExpedienteFormProps {
  form: ProjectInput
  fieldErrors: ProyectoFieldErrors
  submitError: string | null
  loading: boolean
  onFieldChange: <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => void
  onSubmit: () => void
  onReset: () => void
  submitLabel?: string
  resetLabel?: string
  physicalFile?: File | null
  onPhysicalFileChange?: (file: File | null) => void
  physicalFileError?: string | null
}

export function ExpedienteForm({
  form,
  fieldErrors,
  submitError,
  loading,
  onFieldChange,
  onSubmit,
  onReset,
  submitLabel = 'Guardar proyecto',
  resetLabel = 'Limpiar formulario',
  physicalFile = null,
  onPhysicalFileChange,
  physicalFileError = null,
}: ExpedienteFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handlePhysicalFile = (event: ChangeEvent<HTMLInputElement>) => {
    if (!onPhysicalFileChange) return
    onPhysicalFileChange(event.target.files?.[0] ?? null)
  }

  const clearPhysicalFile = () => {
    onPhysicalFileChange?.(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form className="expediente-form" onSubmit={handleSubmit} noValidate>
      {submitError && <Alert variant="error">{submitError}</Alert>}

      <div className="form-grid">
        <FormField
          className="span-2"
          label="Nombre del proyecto *"
          value={form.nombre}
          maxLength={200}
          placeholder="Ej. Mejoramiento de parque urbano"
          error={fieldErrors.nombre}
          onChange={(e) => onFieldChange('nombre', e.target.value)}
        />

        <FormField
          as="textarea"
          className="span-2"
          label="Descripción *"
          value={form.descripcion}
          maxLength={2000}
          rows={4}
          placeholder="Objetivo, alcance y beneficios esperados para la población."
          error={fieldErrors.descripcion}
          onChange={(e) => onFieldChange('descripcion', e.target.value)}
        />

        <FormField
          label="Presupuesto estimado (S/) *"
          type="number"
          min={0}
          step={0.01}
          value={form.presupuesto || ''}
          placeholder="2500000"
          error={fieldErrors.presupuesto}
          onChange={(e) =>
            onFieldChange('presupuesto', e.target.value === '' ? 0 : Number(e.target.value))
          }
        />

        <FormField
          label="Beneficiarios estimados *"
          type="number"
          min={1}
          step={1}
          value={form.beneficiarios || ''}
          placeholder="5000"
          error={fieldErrors.beneficiarios}
          onChange={(e) =>
            onFieldChange('beneficiarios', e.target.value === '' ? 0 : Number(e.target.value))
          }
        />

        {onPhysicalFileChange && (
          <div className="form-field span-2 expediente-upload">
            <span className="form-field-label">Expediente físico</span>
            <p className="expediente-upload-hint">
              Adjunte el documento escaneado o digital (PDF, Word o ZIP, máx.{' '}
              {formatFileSize(PHYSICAL_EXPEDIENTE_MAX_BYTES)}). Se conserva en este navegador
              vinculado al proyecto hasta existir carga oficial en la API.
            </p>
            <div className="expediente-upload-row">
              <input
                ref={fileInputRef}
                type="file"
                className="expediente-upload-input"
                accept={PHYSICAL_EXPEDIENTE_ACCEPT}
                onChange={handlePhysicalFile}
                tabIndex={-1}
                aria-hidden
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                Subir expediente físico
              </button>
              {physicalFile && (
                <div className="expediente-upload-meta">
                  <span className="expediente-upload-name" title={physicalFile.name}>
                    {physicalFile.name}
                  </span>
                  <span className="expediente-upload-size">{formatFileSize(physicalFile.size)}</span>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={clearPhysicalFile}>
                    Quitar
                  </button>
                </div>
              )}
            </div>
            {physicalFileError && (
              <span className="form-field-error" role="alert">
                {physicalFileError}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Guardando…' : submitLabel}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onReset}>
          {resetLabel}
        </button>
      </div>
    </form>
  )
}
