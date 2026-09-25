export interface ProyectoCreate {
  nombre: string
  descripcion: string
  ubicacion: string
  presupuesto: number
  beneficiarios: number
  tipo_proyecto: string
}

export interface Proyecto extends ProyectoCreate {
  id: number
  estado: string
  fecha_creacion: string
}

export interface RegistrarProyectoResponse {
  mensaje: string
  proyecto: Proyecto
}

export interface ApiErrorBody {
  detail: string | { msg: string; loc: string[] }[]
}
