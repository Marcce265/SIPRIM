import type { ProyectoCreate } from '../../types/proyecto'

export type ProyectoFieldErrors = Partial<Record<keyof ProyectoCreate, string>>

export function validateProyecto(form: ProyectoCreate): ProyectoFieldErrors {
  const errors: ProyectoFieldErrors = {}

  if (!form.nombre.trim()) errors.nombre = 'El nombre es obligatorio.'
  else if (form.nombre.length > 200) errors.nombre = 'Máximo 200 caracteres.'

  if (!form.descripcion.trim()) errors.descripcion = 'La descripción es obligatoria.'
  else if (form.descripcion.length > 2000) errors.descripcion = 'Máximo 2000 caracteres.'

  if (!form.ubicacion.trim()) errors.ubicacion = 'La ubicación es obligatoria.'
  else if (form.ubicacion.length > 300) errors.ubicacion = 'Máximo 300 caracteres.'

  if (!form.tipo_proyecto.trim()) errors.tipo_proyecto = 'Indique el tipo de proyecto.'
  else if (form.tipo_proyecto.length > 150) errors.tipo_proyecto = 'Máximo 150 caracteres.'

  if (!Number.isFinite(form.presupuesto) || form.presupuesto <= 0) {
    errors.presupuesto = 'Ingrese un presupuesto mayor a cero.'
  }

  if (!Number.isInteger(form.beneficiarios) || form.beneficiarios <= 0) {
    errors.beneficiarios = 'Ingrese un número entero de beneficiarios mayor a cero.'
  }

  return errors
}

export function normalizeProyectoForm(form: ProyectoCreate): ProyectoCreate {
  return {
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim(),
    ubicacion: form.ubicacion.trim(),
    tipo_proyecto: form.tipo_proyecto.trim(),
    presupuesto: Number(form.presupuesto),
    beneficiarios: Number(form.beneficiarios),
  }
}
