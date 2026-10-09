const KEY_PREFIX = 'siprim-physical-expediente:'
const MAX_BYTES = 8 * 1024 * 1024

export interface StoredPhysicalExpediente {
  fileName: string
  mimeType: string
  size: number
  uploadedAt: string
  dataUrl: string
}

function storageKey(projectId: string): string {
  return `${KEY_PREFIX}${projectId}`
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('No se pudo leer el archivo.'))
    reader.readAsDataURL(file)
  })
}

export function getPhysicalExpediente(projectId: string): StoredPhysicalExpediente | null {
  try {
    const raw = localStorage.getItem(storageKey(projectId))
    if (!raw) return null
    return JSON.parse(raw) as StoredPhysicalExpediente
  } catch {
    return null
  }
}

export async function savePhysicalExpediente(projectId: string, file: File): Promise<void> {
  if (file.size > MAX_BYTES) {
    throw new Error(`El archivo supera el límite de ${MAX_BYTES / (1024 * 1024)} MB para almacenamiento local.`)
  }
  const dataUrl = await readFileAsDataUrl(file)
  const record: StoredPhysicalExpediente = {
    fileName: file.name,
    mimeType: file.type || 'application/octet-stream',
    size: file.size,
    uploadedAt: new Date().toISOString(),
    dataUrl,
  }
  localStorage.setItem(storageKey(projectId), JSON.stringify(record))
}

export const PHYSICAL_EXPEDIENTE_MAX_BYTES = MAX_BYTES

export const PHYSICAL_EXPEDIENTE_ACCEPT =
  '.pdf,.doc,.docx,.zip,.rar,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/zip'
