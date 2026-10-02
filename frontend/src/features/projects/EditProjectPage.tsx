import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { PageHeader } from '../../components/ui/PageHeader'
import { simulationRepository } from '../../simulation/repository'
import { useSimulation } from '../../simulation/useSimulation'
import type { ProjectInput } from '../../types/proyecto'
import { useAuth } from '../auth/AuthContext'
import { ExpedienteForm } from '../registrar/ExpedienteForm'
import { normalizeProyectoForm, validateProyecto, type ProyectoFieldErrors } from '../registrar/validateProyecto'

export function EditProjectPage() {
  const { projectId = '' } = useParams()
  const { state } = useSimulation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const project = state.projects.find((item) => item.id === projectId)
  const current = project
    ? state.projectVersions.find((item) => item.id === project.versionActualId)
    : undefined
  const [form, setForm] = useState<ProjectInput>(() =>
    current
      ? {
          nombre: current.nombre,
          descripcion: current.descripcion,
          presupuesto: current.presupuesto,
          beneficiarios: current.beneficiarios,
        }
      : { nombre: '', descripcion: '', presupuesto: 0, beneficiarios: 0 },
  )
  const [fieldErrors, setFieldErrors] = useState<ProyectoFieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  if (!project || !current) {
    return <section className="empty-state"><h1>Proyecto no encontrado</h1><Link to="/proyectos" className="btn btn-secondary">Volver</Link></section>
  }

  const updateField = <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setFieldErrors((previous) => ({ ...previous, [key]: undefined }))
  }

  const submit = () => {
    const errors = validateProyecto(form)
    setFieldErrors(errors)
    setSubmitError(null)
    if (Object.keys(errors).length > 0) return
    try {
      if (!user) throw new Error('Sesión no disponible.')
      const hadCompletedEvaluation = state.evaluations.some(
        (item) => item.proyectoVersionId === current.id && item.estado === 'completado',
      )
      const version = simulationRepository.updateProject(
        project.id,
        normalizeProyectoForm(form),
        user,
      )
      navigate(`/proyectos/${project.id}`, {
        state: {
          mensaje: hadCompletedEvaluation
            ? `Cambios guardados como versión ${version.numero}; el resultado anterior se conserva.`
            : 'Proyecto actualizado.',
        },
      })
    } catch (caught) {
      setSubmitError(caught instanceof Error ? caught.message : 'No se pudo guardar.')
    }
  }

  return (
    <div className="form-page">
      <PageHeader
        title={`Editar ${project.codigo}`}
        description="Si la versión actual ya fue evaluada, los cambios crearán una nueva versión sin alterar el resultado anterior."
      />
      {submitError && <Alert variant="error">{submitError}</Alert>}
      <ExpedienteForm
        form={form}
        fieldErrors={fieldErrors}
        submitError={null}
        loading={false}
        onFieldChange={updateField}
        onSubmit={submit}
        onReset={() => navigate(`/proyectos/${project.id}`)}
        submitLabel="Guardar cambios"
        resetLabel="Cancelar"
      />
    </div>
  )
}
