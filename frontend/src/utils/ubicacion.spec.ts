// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { describe, expect, it } from 'vitest'
import type { Departamento } from '../data/colombia'
import {
  componerLugarNacimiento,
  municipiosDe,
  parsearLugarNacimiento,
} from './ubicacion'

const DEPARTAMENTOS: Departamento[] = [
  {
    id: '1', nombre: 'CAUCA',
    municipios: [{ id: '101', nombre: 'POPAYÁN' }, { id: '102', nombre: 'CALI' }],
  },
  {
    id: '2', nombre: 'VALLE DEL CAUCA',
    municipios: [{ id: '201', nombre: 'CALI' }, { id: '202', nombre: 'BUENAVENTURA' }],
  },
]

describe('ubicación — lugar de nacimiento', () => {
  it('compone municipio y departamento', () => {
    expect(componerLugarNacimiento('POPAYÁN', 'CAUCA')).toBe('POPAYÁN, CAUCA')
    expect(componerLugarNacimiento('', 'CAUCA')).toBe('CAUCA')
    expect(componerLugarNacimiento('POPAYÁN', '')).toBe('POPAYÁN')
  })

  it('municipiosDe filtra y ordena', () => {
    expect(municipiosDe('1', DEPARTAMENTOS).map(m => m.nombre)).toEqual(['CALI', 'POPAYÁN'])
    expect(municipiosDe('', DEPARTAMENTOS)).toEqual([])
    expect(municipiosDe('99', DEPARTAMENTOS)).toEqual([])
  })

  it('parsea un valor guardado', () => {
    const resultado = parsearLugarNacimiento('POPAYÁN, CAUCA', DEPARTAMENTOS)

    expect(resultado?.depto.id).toBe('1')
    expect(resultado?.municipio).toBe('POPAYÁN')
  })

  it('prefiere el departamento con nombre más largo', () => {
    const resultado = parsearLugarNacimiento('CALI, VALLE DEL CAUCA', DEPARTAMENTOS)

    expect(resultado?.depto.id).toBe('2')
    expect(resultado?.municipio).toBe('CALI')
  })

  it('devuelve null si no reconoce el texto', () => {
    expect(parsearLugarNacimiento('', DEPARTAMENTOS)).toBeNull()
    expect(parsearLugarNacimiento('BOGOTÁ D.C.', DEPARTAMENTOS)).toBeNull()
    expect(parsearLugarNacimiento(null, DEPARTAMENTOS)).toBeNull()
  })
})
