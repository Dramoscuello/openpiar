<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // Aplicar tema oscuro si está guardado en localStorage
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }

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
