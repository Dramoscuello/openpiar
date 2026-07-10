<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const noLeidas = ref(0)
let intervalId: ReturnType<typeof setInterval> | null = null

async function fetchCount() {
  try {
    const res = await fetch('/api/v1/notificaciones/no-leidas/count', {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    if (res.ok) {
      const data = await res.json()
      noLeidas.value = data.no_leidas || 0
    }
  } catch (_) {
    /* silent */
  }
}

onMounted(() => {
  fetchCount()
  intervalId = setInterval(fetchCount, 60000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})

const emit = defineEmits<{ (e: 'toggle'): void }>()

defineExpose({ refresh: fetchCount })
</script>

<template>
  <button
    @click="emit('toggle')"
    class="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-full transition-all relative cursor-pointer"
    title="Notificaciones"
  >
    <span class="material-symbols-outlined">notifications</span>
    <span
      v-if="noLeidas > 0"
      class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-error text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none"
    >
      {{ noLeidas > 99 ? '99+' : noLeidas }}
    </span>
  </button>
</template>
