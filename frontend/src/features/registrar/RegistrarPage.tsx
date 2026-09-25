import { PageHeader } from '../../components/ui/PageHeader'
import { ExpedienteForm } from './ExpedienteForm'
import { useRegistrarProyecto } from './useRegistrarProyecto'

export function RegistrarPage() {
  const { form, fieldErrors, submitError, loading, updateField, resetForm, submit } =
    useRegistrarProyecto()

  return (
    <div className="form-page">
      <PageHeader
        title="Cargar expediente del proyecto"
        description="Complete el expediente básico (HU1.1). Los datos se almacenan en el backend para futuras evaluaciones por agentes especialistas."
      />
      <ExpedienteForm
        form={form}
        fieldErrors={fieldErrors}
        submitError={submitError}
        loading={loading}
        onFieldChange={updateField}
        onSubmit={submit}
        onReset={resetForm}
      />
    </div>
  )
}
