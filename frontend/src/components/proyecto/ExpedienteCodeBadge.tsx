import { useState } from 'react'

interface ExpedienteCodeBadgeProps {
  code: string
  projectId?: string
  compact?: boolean
}

export function ExpedienteCodeBadge({
  code,
  projectId,
  compact = false,
}: ExpedienteCodeBadgeProps) {
  const [copied, setCopied] = useState<'code' | 'id' | null>(null)

  const copy = async (text: string, kind: 'code' | 'id') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(kind)
      window.setTimeout(() => setCopied(null), 2000)
    } catch {
      /* portapapeles no disponible */
    }
  }

  return (
    <div className={`expediente-ref ${compact ? 'compact' : ''}`}>
      <div className="expediente-ref-row">
        <span className="expediente-ref-label">Código de expediente</span>
        <code className="expediente-ref-code">{code}</code>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => void copy(code, 'code')}
        >
          {copied === 'code' ? 'Copiado' : 'Copiar código'}
        </button>
      </div>
      {!compact && projectId && (
        <div className="expediente-ref-row muted">
          <span className="expediente-ref-label">UUID técnico</span>
          <code className="expediente-ref-uuid">{projectId}</code>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void copy(projectId, 'id')}
          >
            {copied === 'id' ? 'Copiado' : 'Copiar UUID'}
          </button>
        </div>
      )}
      {!compact && (
        <p className="expediente-ref-hint">
          Use el <strong>código</strong> en Consultar e Integración IA. El UUID es para integraciones
          técnicas.
        </p>
      )}
    </div>
  )
}
