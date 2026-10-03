// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
/**
 * Utilidades para el lugar de nacimiento (departamento/municipio DANE).
 */

import type { Departamento } from '../data/colombia'

export function municipiosDe(
  deptoId: string,
  departamentos: Departamento[],
): Departamento['municipios'] {
  if (!deptoId) return []
  const depto = departamentos.find(d => d.id === deptoId)
  return depto ? depto.municipios.slice().sort((a, b) => a.nombre.localeCompare(b.nombre)) : []
}

export function componerLugarNacimiento(municipio: string, deptoNombre: string): string {
  return [municipio, deptoNombre].filter(Boolean).join(', ')
}

export interface LugarNacimiento {
  depto: Departamento
  municipio: string | null
}

/**
 * Reconstruye departamento y municipio desde un lugar de nacimiento guardado
 * con el formato "Municipio, Departamento". Devuelve null si no se reconoce.
 */
export function parsearLugarNacimiento(
  valor: string | null | undefined,
  departamentos: Departamento[],
): LugarNacimiento | null {
  if (!valor || !valor.trim()) return null

  const normalizado = valor.trim().toLowerCase()
  const depto = [...departamentos]
    .filter(d => normalizado.endsWith(d.nombre.toLowerCase()))
    .sort((a, b) => b.nombre.length - a.nombre.length)[0]
  if (!depto) return null

  const corte = normalizado.lastIndexOf(depto.nombre.toLowerCase())
  const sinDepto = valor.slice(0, corte).replace(/[,\s]+$/, '').trim()
  const municipio = depto.municipios.find(
    m => m.nombre.toLowerCase() === sinDepto.toLowerCase(),
  )

  return { depto, municipio: municipio ? municipio.nombre : null }
}
