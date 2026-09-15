// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0

export type EstadoCobertura = 'pendiente' | 'con_ajuste' | 'no_requiere'

export interface PiarAsignaturaCobertura {
  id: string
  asignatura_id: string
  docente_id: string | null
  nombre_asignatura: string
  area_nombre: string | null
  docente_nombre: string | null
  estado: EstadoCobertura
  justificacion: string | null
}

export interface PiarSeccionCompletitud {
  codigo: string
  nombre: string
  completa: boolean
  faltantes: string[]
}

export interface PiarCompletitud {
  porcentaje: number
  completa: boolean
  puede_exportar_final: boolean
  secciones: PiarSeccionCompletitud[]
  asignaturas: PiarAsignaturaCobertura[]
}

export interface PiarVersion {
  id: string
  numero: number
  sha256: string
  creado_por: string | null
  created_at: string
}
