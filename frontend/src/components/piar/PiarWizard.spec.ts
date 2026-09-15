// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import PiarCompletionPanel from './PiarCompletionPanel.vue'
import PiarExportPanel from './PiarExportPanel.vue'
import SubjectCoveragePanel from './SubjectCoveragePanel.vue'
import type { PiarCompletitud } from '../../types/piar'

const completitud: PiarCompletitud = {
  porcentaje: 57,
  completa: false,
  puede_exportar_final: false,
  secciones: [
    { codigo: 'general', nombre: 'Información general', completa: true, faltantes: [] },
    { codigo: 'salud', nombre: 'Salud', completa: false, faltantes: ['EPS'] },
  ],
  asignaturas: [],
}

describe('asistente PIAR', () => {
  it('muestra el progreso y emite el paso seleccionado', async () => {
    const wrapper = mount(PiarCompletionPanel, { props: { value: completitud } })

    expect(wrapper.text()).toContain('57%')
    expect(wrapper.text()).toContain('1 pendiente(s)')
    const segundoPaso = wrapper.findAll('button')[1]
    expect(segundoPaso).toBeDefined()
    await segundoPaso!.trigger('click')
    expect(wrapper.emitted('open')).toEqual([['salud']])
  })

  it('bloquea la finalización incompleta y expone descarga de borrador', async () => {
    const wrapper = mount(PiarExportPanel, {
      props: { estado: 'borrador', versionActual: 0, puedeFinalizar: false },
    })

    const botones = wrapper.findAll('button')
    expect(botones[1]).toBeDefined()
    expect(botones[1]!.attributes('disabled')).toBeDefined()
    expect(botones[0]).toBeDefined()
    await botones[0]!.trigger('click')
    expect(wrapper.emitted('draft')).toHaveLength(1)
  })

  it('emite la justificación de una asignatura que no requiere ajuste', async () => {
    const wrapper = mount(SubjectCoveragePanel, {
      props: {
        currentUserId: 'teacher-1',
        asignaturas: [{
          id: 'coverage-1',
          asignatura_id: 'math-1',
          docente_id: 'teacher-1',
          nombre_asignatura: 'Matemáticas',
          area_nombre: 'Matemáticas',
          docente_nombre: 'Docente Uno',
          estado: 'pendiente',
          justificacion: null,
        }],
      },
    })

    await wrapper.find('input').setValue('Logra los objetivos sin apoyos adicionales.')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('resolve')).toEqual([
      ['math-1', 'no_requiere', 'Logra los objetivos sin apoyos adicionales.'],
    ])
  })

  it.each(['other-teacher', 'director', 'directivo', undefined])('oculta completamente la cobertura ajena a %s', (currentUserId) => {
    const wrapper = mount(SubjectCoveragePanel, {
      props: {
        currentUserId,
        asignaturas: [{
          id: 'coverage-1', asignatura_id: 'math-1', docente_id: 'teacher-1',
          nombre_asignatura: 'Matemáticas', area_nombre: 'Matemáticas',
          docente_nombre: 'Docente Uno', estado: 'no_requiere',
          justificacion: 'Logra los objetivos sin apoyos adicionales.',
        }],
      },
    })
    expect(wrapper.text()).toBe('')
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.emitted('resolve')).toBeUndefined()
  })

  it('bloquea también al docente asignado cuando el PIAR está finalizado', () => {
    const wrapper = mount(SubjectCoveragePanel, {
      props: {
        currentUserId: 'teacher-1', readonly: true,
        asignaturas: [{
          id: 'coverage-1', asignatura_id: 'math-1', docente_id: 'teacher-1',
          nombre_asignatura: 'Matemáticas', area_nombre: null,
          docente_nombre: 'Docente Uno', estado: 'no_requiere', justificacion: 'Sin ajuste.',
        }],
      },
    })
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.findAll('button')).toHaveLength(0)
  })
})
