import { useCallback, useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { obtenerProyecto } from '../../api/proyectos.api'
import type { Proyecto } from '../../types/proyecto'
import { rememberProject } from '../../utils/recentProjects'

export interface ConsultarLocationState {
  mensaje?: string
  proyecto?: Proyecto
}

export function useConsultarProyecto() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const state = (location.state as ConsultarLocationState | null) ?? {}

  const idFromUrl = searchParams.get('id')
  const [inputId, setInputId] = useState(idFromUrl ?? '')
  const [proyecto, setProyecto] = useState<Proyecto | null>(state.proyecto ?? null)
  const [successMsg, setSuccessMsg] = useState<string | null>(state.mensaje ?? null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchById = useCallback(
    async (rawId: string) => {
      const id = Number.parseInt(rawId, 10)
      if (!Number.isFinite(id) || id <= 0) {
        setError('Ingrese un identificador numérico válido.')
        setProyecto(null)
        return
      }

      setLoading(true)
      setError(null)
      setSuccessMsg(null)

      try {
        const data = await obtenerProyecto(id)
        setProyecto(data)
        rememberProject(data)
        setSearchParams({ id: String(id) }, { replace: true })
      } catch (err) {
        setProyecto(null)
        setError(err instanceof Error ? err.message : 'No se pudo consultar el proyecto.')
      } finally {
        setLoading(false)
      }
    },
    [setSearchParams],
  )

  useEffect(() => {
    if (!idFromUrl) return
    if (state.proyecto && String(state.proyecto.id) === idFromUrl) return
    void fetchById(idFromUrl)
  }, [idFromUrl, state.proyecto, fetchById])

  const search = useCallback(() => {
    void fetchById(inputId.trim())
  }, [fetchById, inputId])

  return {
    inputId,
    setInputId,
    proyecto,
    successMsg,
    error,
    loading,
    search,
  }
}
