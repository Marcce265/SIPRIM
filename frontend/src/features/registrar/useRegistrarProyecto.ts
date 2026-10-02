import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { simulationRepository } from '../../simulation/repository'
import type { ProjectInput } from '../../types/proyecto'
import { useAuth } from '../auth/AuthContext'
import { EMPTY_PROYECTO_FORM } from './constants'
import {
  normalizeProyectoForm,
  validateProyecto,
  type ProyectoFieldErrors,
} from './validateProyecto'

export function useRegistrarProyecto() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [form, setForm] = useState<ProjectInput>(EMPTY_PROYECTO_FORM)
  const [fieldErrors, setFieldErrors] = useState<ProyectoFieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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
  }, [])

  const submit = useCallback(async () => {
    setSubmitError(null)
    const errors = validateProyecto(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setLoading(true)
    try {
      const payload = normalizeProyectoForm(form)
      if (!user) throw new Error('Sesión de demostración no disponible.')
      const project = simulationRepository.createProject(payload, user)
      navigate(`/proyectos/${project.id}`, {
        state: { mensaje: 'Proyecto registrado. Ya puede iniciar la evaluación económica.' },
      })
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'No se pudo registrar el proyecto.')
    } finally {
      setLoading(false)
    }
  }, [form, navigate, user])

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
