// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'

export interface EstadoCount {
  estado: string
  total: number
}

export interface AreaCount {
  area: string
  total: number
}

export interface GradoCount {
  grado: string
  total: number
}

export interface ActividadItem {
  tipo: string
  descripcion: string
  estudiante_nombre: string
  fecha: string
}

export interface DashboardStats {
  total_estudiantes: number
  total_piars: number
  total_ajustes: number
  piars_activos: number
  piars_firmados: number
  piars_vencidos: number
  actas_firmas_incompletas: number
  piars_por_estado: EstadoCount[]
  ajustes_por_area: AreaCount[]
  estudiantes_por_grado: GradoCount[]
  periodo_activo_nombre: string | null
  ajustes_este_periodo: number
  puntuacion_promedio: number | null
  actividad_reciente: ActividadItem[]
}

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    const authStore = useAuthStore()
    try {
      const res = await fetch('/api/v1/dashboard', {
        headers: { Authorization: `Bearer ${authStore.token}` },
      })
      if (!res.ok) throw new Error('Error al cargar estadísticas')
      stats.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, error, fetchStats }
})
