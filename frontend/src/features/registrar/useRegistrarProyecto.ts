import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../../api/pmv1.api'
import type { ProyectoCreate } from '../../types/proyecto'
import { EMPTY_PROYECTO_FORM } from './constants'
import {
  normalizeProyectoForm,
  validateProyecto,
  type ProyectoFieldErrors,
} from './validateProyecto'

function toProjectCode(title: string): string {
  const base = title
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 24)
  return base || `PROY-${Date.now().toString(36).toUpperCase()}`
}

export function useRegistrarProyecto() {
  const navigate = useNavigate()
  const [form, setForm] = useState<ProyectoCreate>(EMPTY_PROYECTO_FORM)
  const [fieldErrors, setFieldErrors] = useState<ProyectoFieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const updateField = useCallback(<K extends keyof ProyectoCreate>(key: K, value: ProyectoCreate[K]) => {
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
        code: toProjectCode(payload.nombre),
        title: payload.nombre,
        description: payload.descripcion,
        location: payload.ubicacion,
        proposed_land_use: payload.tipo_proyecto,
        estimated_budget_pen: payload.presupuesto,
        beneficiaries_count: payload.beneficiarios,
      })

      navigate(`/proyectos/${project.project_id}`, {
        state: { mensaje: 'Expediente registrado correctamente.' },
      })
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'No se pudo registrar el proyecto.')
    } finally {
      setLoading(false)
    }
  }, [form, navigate])

  return {
    form,
    fieldErrors,
    submitError,
    loading,
    updateField,
    resetForm,
    submit,
  }
}
