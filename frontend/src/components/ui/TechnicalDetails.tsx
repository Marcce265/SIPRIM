interface TechnicalDetailsProps {
  data: unknown
  label?: string
}

export function TechnicalDetails({ data, label = 'Detalle técnico' }: TechnicalDetailsProps) {
  return (
    <details className="tech-details">
      <summary>{label}</summary>
      <pre className="flow-json">{JSON.stringify(data, null, 2)}</pre>
    </details>
  )
}
