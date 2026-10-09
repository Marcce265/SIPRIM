/** UUID PMV1 o código de expediente (EXP-XXXXXX). */

export const EXPEDIENTE_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isExpedienteUuid(value: string): boolean {
  return EXPEDIENTE_UUID_RE.test(value.trim())
}

export function normalizeExpedienteQuery(value: string): string {
  return value.trim()
}

export function isLikelyExpedienteCode(value: string): boolean {
  const q = normalizeExpedienteQuery(value)
  if (q.length < 3 || q.length > 40) return false
  return /^[A-Za-z0-9_-]+$/.test(q)
}

export function isValidExpedienteLookup(value: string): boolean {
  const q = normalizeExpedienteQuery(value)
  return isExpedienteUuid(q) || isLikelyExpedienteCode(q)
}
