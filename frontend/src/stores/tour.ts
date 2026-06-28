// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'

export const useTourStore = defineStore('tour', () => {
  const isActive = ref(false)
  const wasSkipped = ref(false)

  async function checkAndStart() {
    const authStore = useAuthStore()
    if (!authStore.user) return false

    if (authStore.user.tour_completado) {
      isActive.value = false
      return false
    }

    isActive.value = true
    wasSkipped.value = false
    return true
  }

  async function markCompleted() {
    const authStore = useAuthStore()
    isActive.value = false
    try {
      await fetch('/api/v1/auth/tour-completado', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (authStore.user) {
        authStore.user.tour_completado = true
      }
    } catch (e) {
      console.error('Error marcando tour como completado', e)
    }
  }

  function skip() {
    isActive.value = false
    wasSkipped.value = true
    markCompleted()
  }

  function stop() {
    isActive.value = false
  }

  return {
    isActive,
    wasSkipped,
    checkAndStart,
    markCompleted,
    skip,
    stop,
  }
})
