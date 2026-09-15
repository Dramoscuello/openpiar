// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { ref, type Ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import type { PiarCompletitud, PiarVersion } from '../types/piar'

export function usePiarWorkflow(piarId: Ref<string | null>) {
  const auth = useAuthStore()
  const completitud = ref<PiarCompletitud | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const headers = () => ({ 'Authorization': `Bearer ${auth.token}` })

  async function refresh(): Promise<PiarCompletitud | null> {
    if (!piarId.value) return null
    loading.value = true
    error.value = null
    try {
      const response = await fetch(`/api/v1/piars/${piarId.value}/completitud`, { headers: headers() })
      if (!response.ok) throw new Error('No fue posible consultar el progreso del PIAR.')
      completitud.value = await response.json() as PiarCompletitud
      return completitud.value
    } catch (reason: any) {
      error.value = reason.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function finalizar(): Promise<PiarVersion> {
    if (!piarId.value) throw new Error('No hay PIAR activo.')
    const response = await fetch(`/api/v1/piars/${piarId.value}/finalizar`, {
      method: 'POST',
      headers: headers(),
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const detalle = body.detail?.mensaje || body.detail || 'El PIAR aún no puede finalizarse.'
      throw new Error(typeof detalle === 'string' ? detalle : 'El PIAR aún no puede finalizarse.')
    }
    return await response.json() as PiarVersion
  }

  async function reabrir(): Promise<void> {
    if (!piarId.value) throw new Error('No hay PIAR activo.')
    const response = await fetch(`/api/v1/piars/${piarId.value}/reabrir`, {
      method: 'POST',
      headers: headers(),
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || 'No fue posible reabrir el PIAR.')
    }
  }

  async function descargar(modo: 'borrador' | 'final'): Promise<void> {
    if (!piarId.value) return
    const response = await fetch(`/api/v1/piars/${piarId.value}/pdf?modo=${modo}`, { headers: headers() })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail?.mensaje || body.detail || 'No fue posible generar el PDF.')
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `PIAR_${piarId.value}_${modo}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  return { completitud, loading, error, refresh, finalizar, reabrir, descargar }
}
