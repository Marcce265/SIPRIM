import type { FormEvent } from 'react'
import { Alert } from '../../components/ui/Alert'
import { FormField } from '../../components/ui/FormField'
import type { ProyectoCreate } from '../../types/proyecto'
import { TIPOS_PROYECTO_SUGERIDOS } from './constants'
import type { ProyectoFieldErrors } from './validateProyecto'

interface ExpedienteFormProps {
  form: ProyectoCreate
  fieldErrors: ProyectoFieldErrors
  submitError: string | null
  loading: boolean
  onFieldChange: <K extends keyof ProyectoCreate>(key: K, value: ProyectoCreate[K]) => void
  onSubmit: () => void
  onReset: () => void
}

export function ExpedienteForm({
  form,
  fieldErrors,
  submitError,
  loading,
  onFieldChange,
  onSubmit,
  onReset,
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
          label="Ubicación territorial *"
          value={form.ubicacion}
          maxLength={300}
          placeholder="Ej. El Tambo - Huancayo"
          error={fieldErrors.ubicacion}
          onChange={(e) => onFieldChange('ubicacion', e.target.value)}
        />

        <FormField
          label="Tipo de proyecto *"
          list="tipos-proyecto"
          value={form.tipo_proyecto}
          maxLength={150}
          error={fieldErrors.tipo_proyecto}
          onChange={(e) => onFieldChange('tipo_proyecto', e.target.value)}
        />
        <datalist id="tipos-proyecto">
          {TIPOS_PROYECTO_SUGERIDOS.map((tipo) => (
            <option key={tipo} value={tipo} />
          ))}
        </datalist>

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
          {loading ? 'Registrando…' : 'Registrar expediente'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onReset}>
          Limpiar formulario
        </button>
      </div>
    </form>
  )
}
