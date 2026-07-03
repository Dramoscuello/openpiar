<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/AppSidebar.vue'
import AppTopBar from './components/AppTopBar.vue'
import AppTour from './components/AppTour.vue'

const authStore = useAuthStore()
const route = useRoute()

/* Rutas que NO usan el layout compartido (sin sidebar ni topbar) */
const ROUTES_SIN_LAYOUT = ['login', 'setup', 'familia']

const showLayout = computed(() => {
  return !ROUTES_SIN_LAYOUT.includes(route.name as string)
})

onMounted(async () => {
  /* Inicializar estado de autenticación y setup al arrancar */
  await authStore.initAuth()
})
</script>

<template>
  <div v-if="!showLayout" class="min-h-screen">
    <RouterView />
  </div>

  <div v-else class="flex bg-background text-on-background min-h-screen transition-colors duration-300">
    <AppSidebar />
    <main class="ml-64 flex-1 min-h-screen flex flex-col">
      <AppTopBar />
      <AppTour />
      <RouterView />
    </main>
  </div>
</template>
