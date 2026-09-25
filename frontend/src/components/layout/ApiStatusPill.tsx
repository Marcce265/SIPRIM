interface ApiStatusPillProps {
  apiOnline: boolean | null
}

export function ApiStatusPill({ apiOnline }: ApiStatusPillProps) {
  const statusClass =
    apiOnline === null ? 'pending' : apiOnline ? 'online' : 'offline'

  return (
    <div className={`api-pill ${statusClass}`} title="Estado del backend">
      <span className="api-dot" />
      {apiOnline === null && 'Conectando…'}
      {apiOnline === true && 'API en línea'}
      {apiOnline === false && 'API no disponible'}
    </div>
  )
}
