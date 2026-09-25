import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { registrarProyecto } from '../../api/proyectos.api'
import type { ProyectoCreate } from '../../types/proyecto'
import { rememberProject } from '../../utils/recentProjects'
import { EMPTY_PROYECTO_FORM } from './constants'
import {
  normalizeProyectoForm,
  validateProyecto,
  type ProyectoFieldErrors,
} from './validateProyecto'

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
      const res = await registrarProyecto(payload)
      rememberProject(res.proyecto)
      navigate(`/consultar?id=${res.proyecto.id}`, {
        state: { mensaje: res.mensaje, proyecto: res.proyecto },
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
