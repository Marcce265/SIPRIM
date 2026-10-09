import { useCallback, useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { resolveProject } from '../../api/pmv1.api'
import type { Proyecto } from '../../types/proyecto'
import { isValidExpedienteLookup, normalizeExpedienteQuery } from '../../utils/expedienteRef'
import { mapPmV1ToProyecto } from '../../utils/pmv1Mapper'
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
      const query = normalizeExpedienteQuery(rawId)
      if (!isValidExpedienteLookup(query)) {
        setError(
          'Ingrese el código de expediente (ej. EXP-A1B2C3) o el UUID técnico del proyecto.',
        )
        setProyecto(null)
        return
      }

      setLoading(true)
      setError(null)
      setSuccessMsg(null)

      try {
        const data = await resolveProject(query)
        const mapped = mapPmV1ToProyecto(data)
        setProyecto(mapped)
        rememberProject(mapped)
        setSearchParams({ id: mapped.id }, { replace: true })
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
    if (state.proyecto && state.proyecto.id === idFromUrl) return
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
