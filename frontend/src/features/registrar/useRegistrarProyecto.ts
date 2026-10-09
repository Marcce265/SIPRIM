import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../../api/pmv1.api'
import type { ProjectInput } from '../../types/proyecto'
import {
  PHYSICAL_EXPEDIENTE_MAX_BYTES,
  savePhysicalExpediente,
} from '../../utils/physicalExpedienteStorage'
import { formatFileSize } from '../../utils/format'
import { EMPTY_PROYECTO_FORM } from './constants'
import {
  normalizeProyectoForm,
  validateProyecto,
  type ProyectoFieldErrors,
} from './validateProyecto'

export function useRegistrarProyecto() {
  const navigate = useNavigate()
  const [form, setForm] = useState<ProjectInput>(EMPTY_PROYECTO_FORM)
  const [fieldErrors, setFieldErrors] = useState<ProyectoFieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [physicalFile, setPhysicalFileState] = useState<File | null>(null)
  const [physicalFileError, setPhysicalFileError] = useState<string | null>(null)

  const setPhysicalFile = useCallback((file: File | null) => {
    if (file && file.size > PHYSICAL_EXPEDIENTE_MAX_BYTES) {
      setPhysicalFileState(null)
      setPhysicalFileError(
        `El archivo supera ${formatFileSize(PHYSICAL_EXPEDIENTE_MAX_BYTES)}. Elija uno más liviano.`,
      )
      return
    }
    setPhysicalFileError(null)
    setPhysicalFileState(file)
  }, [])

  const updateField = useCallback(<K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }, [])

  const resetForm = useCallback(() => {
    setForm(EMPTY_PROYECTO_FORM)
    setFieldErrors({})
    setSubmitError(null)
    setPhysicalFileState(null)
    setPhysicalFileError(null)
  }, [])

  const submit = useCallback(async () => {
    setSubmitError(null)
    const errors = validateProyecto(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setLoading(true)
    try {
      const payload = normalizeProyectoForm(form)
      const project = await createProject({
        title: payload.nombre,
        description: payload.descripcion,
        location: 'El Tambo - Huancayo',
        proposed_land_use: 'Infraestructura urbana',
        estimated_budget_pen: payload.presupuesto,
        beneficiaries_count: payload.beneficiarios,
      })

      let mensaje = `Expediente registrado. Código: ${project.code}. Guarde este código para consultas.`
      if (physicalFile) {
        try {
          await savePhysicalExpediente(project.project_id, physicalFile)
          mensaje = `Expediente ${project.code} registrado. Archivo adjunto: ${physicalFile.name}.`
        } catch (fileErr) {
          mensaje =
            fileErr instanceof Error
              ? `Proyecto creado, pero no se guardó el archivo: ${fileErr.message}`
              : 'Proyecto creado, pero no se pudo guardar el archivo adjunto.'
        }
      }

      navigate(`/proyectos/${project.project_id}`, {
        state: { mensaje },
      })
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'No se pudo registrar el proyecto.')
    } finally {
      setLoading(false)
    }
  }, [form, navigate, physicalFile])

  return {
    form,
    fieldErrors,
    submitError,
    loading,
    physicalFile,
    physicalFileError,
    updateField,
    setPhysicalFile,
    resetForm,
    submit,
  }
}
