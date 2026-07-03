<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface Notificacion {
  id: string
  tipo: string
  titulo: string
  mensaje: string
  recurso_url: string | null
  leida: boolean
  fecha_creacion: string
}

const router = useRouter()
const authStore = useAuthStore()

const notifications = ref<Notificacion[]>([])
const total = ref(0)
const loading = ref(false)
const allLoaded = ref(false)
const limit = 20
const panelRef = ref<HTMLElement | null>(null)

const emit = defineEmits<{ (e: 'close'): void; (e: 'count-update', count: number): void }>()

async function fetchNotifications(reset: boolean = false) {
  if (loading.value) return
  if (allLoaded.value && !reset) return
  loading.value = true
  const skip = reset ? 0 : notifications.value.length
  try {
    const res = await fetch(`/api/v1/notificaciones?skip=${skip}&limit=${limit}`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    if (res.ok) {
      const data = await res.json()
      total.value = data.total
      if (reset) {
        notifications.value = data.items
      } else {
        notifications.value.push(...data.items)
      }
      if (notifications.value.length >= data.total) {
        allLoaded.value = true
      }
      emit('count-update', data.no_leidas)
    }
  } catch (_) {
    /* silent */
  } finally {
    loading.value = false
  }
}

async function handleClick(notif: Notificacion) {
  try {
    await fetch(`/api/v1/notificaciones/${notif.id}/leer`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    notif.leida = true
    emit('count-update', total.value - 1)
  } catch (_) {
    /* if entity already deleted, still redirect */
  }

  if (notif.recurso_url) {
    try {
      await router.push(notif.recurso_url)
    } catch (_) {
      /* invalid route — stay on current page */
    }
  }
  emit('close')
}

async function marcarTodasLeidas() {
  try {
    await fetch('/api/v1/notificaciones/leer-todas', {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    notifications.value.forEach(n => n.leida = true)
    emit('count-update', 0)
  } catch (_) {
    /* silent */
  }
}

function onScroll() {
  const el = panelRef.value
  if (!el || loading.value || allLoaded.value) return
  const threshold = 50
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold) {
    fetchNotifications()
  }
}

function formatFecha(fecha: string): string {
  const d = new Date(fecha)
  const hoy = new Date()
  const ayer = new Date(hoy)
  ayer.setDate(ayer.getDate() - 1)

  const time = d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })

  if (d.toDateString() === hoy.toDateString()) {
    return `Hoy · ${time}`
  } else if (d.toDateString() === ayer.toDateString()) {
    return `Ayer · ${time}`
  } else {
    return `${d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })} · ${time}`
  }
}

const tipoIcono: Record<string, string> = {
  inicio_periodo: 'calendar_today',
  piar_sin_actualizar: 'update_disabled',
  ajuste_sin_puntuacion: 'star_half',
  piar_estancado: 'hourglass_empty',
  firma_pendiente: 'edit_note',
  estudiante_sin_piar: 'person_add_disabled',
  resumen_semanal: 'bar_chart',
}

onMounted(() => {
  fetchNotifications(true)
})

defineExpose({ refresh: () => fetchNotifications(true) })
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-outline-variant/20 shrink-0">
      <h3 class="font-bold text-on-surface text-body-lg">Notificaciones</h3>
      <button
        @click="marcarTodasLeidas"
        class="text-label-xs text-primary font-bold hover:underline cursor-pointer"
      >
        Todas leídas
      </button>
    </div>

    <!-- List with scroll -->
    <div
      ref="panelRef"
      @scroll="onScroll"
      class="flex-1 overflow-y-auto"
    >
      <div v-if="notifications.length === 0 && !loading" class="text-center py-12 text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl mb-3">notifications_off</span>
        <p class="text-body-sm">No hay notificaciones</p>
      </div>

      <div
        v-for="notif in notifications"
        :key="notif.id"
        @click="handleClick(notif)"
        class="px-4 py-3 border-b border-outline-variant/10 hover:bg-surface-container-low/50 transition-colors cursor-pointer"
        :class="notif.leida ? '' : 'bg-primary/5'"
      >
        <div class="flex items-start gap-3">
          <span
            class="material-symbols-outlined text-xl mt-0.5 shrink-0"
            :class="notif.leida ? 'text-outline-variant' : 'text-primary'"
          >
            {{ tipoIcono[notif.tipo] || 'notifications' }}
          </span>
          <div class="min-w-0 flex-1">
            <p
              class="text-body-sm leading-snug"
              :class="notif.leida ? 'text-on-surface-variant font-normal' : 'text-on-surface font-bold'"
            >
              {{ notif.titulo }}
            </p>
            <p
              class="text-label-xs mt-0.5 leading-snug"
              :class="notif.leida ? 'text-outline-variant' : 'text-on-surface-variant'"
            >
              {{ notif.mensaje }}
            </p>
            <p class="text-[10px] text-outline-variant mt-1">
              {{ formatFecha(notif.fecha_creacion) }}
            </p>
          </div>
          <span
            v-if="!notif.leida"
            class="w-2 h-2 rounded-full bg-primary shrink-0 mt-2"
          ></span>
        </div>
      </div>

      <div v-if="loading" class="text-center py-4 text-outline-variant">
        <span class="material-symbols-outlined animate-spin text-lg">progress_activity</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
