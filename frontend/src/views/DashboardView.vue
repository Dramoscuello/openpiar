<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F8F9FD] p-6 md:p-12">
    <!-- Topbar (Dynamic Institution Name) -->
    <header class="flex justify-between items-center mb-12 max-w-[1200px] mx-auto w-full">
      <div class="flex items-center gap-xs">
        <span class="material-symbols-outlined text-primary text-[32px] star-icon">star</span>
        <span class="font-display text-headline-md text-primary tracking-tight">OpenPiar</span>
      </div>
      
      <div class="flex items-center gap-md">
        <div class="text-right">
          <p class="font-label-md text-label-md text-on-surface">
            {{ authStore.user?.nombre }} {{ authStore.user?.apellido }}
          </p>
          <p class="font-label-sm text-label-sm text-on-surface-variant capitalize">
            {{ authStore.user?.rol.replace('_', ' ') }}
          </p>
        </div>
        <button
          @click="handleLogout"
          class="flex items-center gap-xs px-sm py-2 bg-surface border border-outline-variant hover:bg-error/5 hover:text-error hover:border-error/20 rounded-input font-label-md text-label-md transition-all cursor-pointer"
        >
          <span class="material-symbols-outlined text-[20px]">logout</span>
          Cerrar Sesión
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-[1200px] mx-auto w-full flex-grow flex items-center justify-center">
      <div class="glass-card max-w-[600px] w-full p-xl bg-white space-y-md text-center">
        <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
          <span class="material-symbols-outlined text-primary text-[32px]">dashboard</span>
        </div>
        
        <h2 class="font-headline-md text-headline-md text-on-surface">
          ¡Bienvenido a OpenPiar!
        </h2>
        
        <p class="font-body-lg text-body-lg text-on-surface-variant">
          Estás ingresando al portal docente para la gestión del PIAR en la institución
          <strong class="text-primary">{{ authStore.nombreInstitucion }}</strong>.
        </p>

        <div class="pt-md border-t border-outline-variant/30 text-left space-y-sm">
          <h3 class="font-label-md text-label-md text-on-surface">Datos de la sesión activa:</h3>
          <div class="grid grid-cols-2 gap-sm text-body-md font-body-md text-on-surface-variant">
            <span class="font-label-md">Correo:</span>
            <span>{{ authStore.user?.email }}</span>
            <span class="font-label-md">Rol:</span>
            <span class="capitalize">{{ authStore.user?.rol.replace('_', ' ') }}</span>
            <span class="font-label-md">ID de Usuario:</span>
            <span class="font-mono text-xs overflow-hidden text-ellipsis">{{ authStore.user?.id }}</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
