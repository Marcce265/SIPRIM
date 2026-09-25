import type { ProyectoCreate } from '../../types/proyecto'

export const TIPOS_PROYECTO_SUGERIDOS = [
  'Infraestructura urbana',
  'Saneamiento',
  'Vialidad',
  'Espacio público',
  'Equipamiento social',
  'Ambiental',
] as const

export const EMPTY_PROYECTO_FORM: ProyectoCreate = {
  nombre: '',
  descripcion: '',
  ubicacion: '',
  presupuesto: 0,
  beneficiarios: 0,
  tipo_proyecto: TIPOS_PROYECTO_SUGERIDOS[0],
}
