// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { computed } from 'vue'
import type { PiarAsignaturaCobertura } from '../types/piar'

interface AjusteVisible {
  asignatura_id?: string | null
  area: string
  creado_por?: string | null
}

export function usePiarVisibility<T extends AjusteVisible>(options: {
  usuario: () => { id: string; rol: string } | null | undefined
  directorId: () => string | null | undefined
  asignaturas: () => PiarAsignaturaCobertura[]
  ajustes: () => T[]
}) {
  const coberturaVisible = computed(() => {
    const usuario = options.usuario()
    return usuario ? options.asignaturas().filter(item => item.docente_id === usuario.id) : []
  })

  const ajustesVisibles = computed(() => {
    const usuario = options.usuario()
    if (!usuario) return []
    const ajustes = options.ajustes()
    if (usuario.rol === 'directivo' || options.directorId() === usuario.id) return ajustes
    return ajustes.filter(ajuste => {
      if (ajuste.creado_por !== usuario.id) return false
      const coincidencias = options.asignaturas().filter(item => ajuste.asignatura_id
        ? item.asignatura_id === ajuste.asignatura_id
        : item.nombre_asignatura.trim().toLocaleLowerCase() === ajuste.area.trim().toLocaleLowerCase())
      return coincidencias.length === 1 && coincidencias[0]?.docente_id === usuario.id
    })
  })

  return { coberturaVisible, ajustesVisibles }
}
