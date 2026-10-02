import { useEffect, useSyncExternalStore } from 'react'
import { simulationRepository } from './repository'

export function useSimulation() {
  const state = useSyncExternalStore(
    simulationRepository.subscribe,
    simulationRepository.getSnapshot,
    simulationRepository.getSnapshot,
  )

  useEffect(() => {
    simulationRepository.advanceEvaluations()
    const timer = window.setInterval(() => simulationRepository.advanceEvaluations(), 250)
    return () => window.clearInterval(timer)
  }, [])

  return {
    state,
    recoveryNotice: simulationRepository.getRecoveryNotice(),
    clearRecoveryNotice: simulationRepository.clearRecoveryNotice,
  }
}
