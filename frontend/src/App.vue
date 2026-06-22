<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // Inicializar estado de autenticación y setup al arrancar
  await authStore.initAuth()
})
</script>

<template>
  <RouterView />
</template>

<style>
/* Estilos globales */
</style>
