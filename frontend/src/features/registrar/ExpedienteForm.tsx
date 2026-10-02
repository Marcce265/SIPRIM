import type { FormEvent } from 'react'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import type { ProjectInput } from '../../types/proyecto'
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
}: ExpedienteFormProps) {
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
