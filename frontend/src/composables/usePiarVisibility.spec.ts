// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { usePiarVisibility } from './usePiarVisibility'
import type { PiarAsignaturaCobertura } from '../types/piar'

const asignaturas: PiarAsignaturaCobertura[] = [
  { id: 'c1', asignatura_id: 'math', docente_id: 'teacher', nombre_asignatura: 'Matemáticas',
    area_nombre: null, docente_nombre: null, estado: 'con_ajuste', justificacion: null },
  { id: 'c2', asignatura_id: 'art', docente_id: 'other', nombre_asignatura: 'Arte',
    area_nombre: null, docente_nombre: null, estado: 'no_requiere', justificacion: 'Participa sin apoyos.' },
]
const ajustes = [
  { id: 'own', asignatura_id: 'math', creado_por: 'teacher', area: 'Matemáticas' },
  { id: 'other-author', asignatura_id: 'math', creado_por: 'other', area: 'Matemáticas' },
  { id: 'other-subject', asignatura_id: 'art', creado_por: 'teacher', area: 'Arte' },
  { id: 'legacy', asignatura_id: null, creado_por: 'teacher', area: ' MATEMÁTICAS ' },
]

describe('visibilidad de cobertura y malla PIAR', () => {
  it('limita al docente a su cobertura y sus ajustes en asignaturas propias', () => {
    const result = usePiarVisibility({
      usuario: () => ({ id: 'teacher', rol: 'docente' }), directorId: () => 'director',
      asignaturas: () => asignaturas, ajustes: () => ajustes,
    })
    expect(result.coberturaVisible.value.map(item => item.asignatura_id)).toEqual(['math'])
    expect(result.ajustesVisibles.value.map(item => item.id)).toEqual(['own', 'legacy'])
  })

  it.each(['director', 'directivo'])('muestra al %s la malla completa, sin cobertura ajena', (id) => {
    const result = usePiarVisibility({
      usuario: () => ({ id, rol: id === 'directivo' ? 'directivo' : 'docente' }),
      directorId: () => 'director', asignaturas: () => asignaturas, ajustes: () => ajustes,
    })
    expect(result.coberturaVisible.value).toEqual([])
    expect(result.ajustesVisibles.value).toEqual(ajustes)
  })

  it('recalcula al cambiar la dirección del estudiante o cerrar la sesión', () => {
    const usuario = ref<{ id: string; rol: string } | null>({ id: 'teacher', rol: 'docente' })
    const directorId = ref('teacher')
    const result = usePiarVisibility({
      usuario: () => usuario.value, directorId: () => directorId.value,
      asignaturas: () => asignaturas, ajustes: () => ajustes,
    })
    expect(result.ajustesVisibles.value).toHaveLength(4)
    expect(result.coberturaVisible.value).toHaveLength(1)
    directorId.value = 'director-otro-grupo'
    expect(result.ajustesVisibles.value).toHaveLength(2)
    usuario.value = null
    expect(result.ajustesVisibles.value).toEqual([])
    expect(result.coberturaVisible.value).toEqual([])
  })
})
