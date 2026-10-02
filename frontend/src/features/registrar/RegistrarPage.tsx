import { PageHeader } from '../../components/ui/PageHeader'
import { ExpedienteForm } from './ExpedienteForm'
import { useRegistrarProyecto } from './useRegistrarProyecto'

export function RegistrarPage() {
  const { form, fieldErrors, submitError, loading, updateField, resetForm, submit } =
    useRegistrarProyecto()

  return (
    <div className="form-page">
      <PageHeader
        title="Registrar proyecto"
        description="Complete los datos mínimos del PMV 1. Se guardarán localmente en este navegador. HU05, HU07."
      />
      <ExpedienteForm
        form={form}
        fieldErrors={fieldErrors}
        submitError={submitError}
        loading={loading}
        onFieldChange={updateField}
        onSubmit={submit}
        onReset={resetForm}
        submitLabel="Registrar proyecto"
      />
    </div>
  )
}
