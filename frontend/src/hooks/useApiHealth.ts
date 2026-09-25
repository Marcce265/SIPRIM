import { useEffect, useState } from 'react'
import { checkHealth } from '../api/proyectos.api'

const POLL_INTERVAL_MS = 30_000

export function useApiHealth() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false

    const tick = async () => {
      const ok = await checkHealth()
      if (!cancelled) setApiOnline(ok)
    }

    void tick()
    const id = window.setInterval(tick, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  return apiOnline
}
