<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <aside
    class="w-64 h-screen fixed left-0 top-0 flex flex-col bg-surface-container-lowest border-r border-outline-variant z-40 transition-colors duration-300"
  >
    <div class="px-gutter py-8">
      <div class="flex items-center gap-3 mb-10">
        <span class="material-symbols-outlined text-primary text-headline-md star-icon">star</span>
        <h1 class="text-headline-md font-display font-bold text-primary">OpenPiar</h1>
      </div>
      
      <nav class="space-y-1">
        <p class="text-label-sm uppercase tracking-wider text-outline mb-4 px-4 select-none">VISTA GENERAL</p>
        <RouterLink
          to="/dashboard"
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          active-class="text-primary font-bold border-r-4 border-primary bg-primary/5 dark:bg-primary/10 rounded-r-md"
        >
          <span class="material-symbols-outlined">dashboard</span>
          <span class="font-label-md">Dashboard</span>
        </RouterLink>
        <RouterLink
          to="/estudiantes"
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          active-class="text-primary font-bold border-r-4 border-primary bg-primary/5 dark:bg-primary/10 rounded-r-md"
        >
          <span class="material-symbols-outlined">group</span>
          <span class="font-label-md">Estudiantes</span>
        </RouterLink>
        <a
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          href="#"
        >
          <span class="material-symbols-outlined">school</span>
          <span class="font-label-md">Currículo</span>
        </a>
        <RouterLink
          v-if="authStore.user?.rol === 'directivo'"
          to="/gestion-escolar"
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          active-class="text-primary font-bold border-r-4 border-primary bg-primary/5 dark:bg-primary/10 rounded-r-md"
        >
          <span class="material-symbols-outlined">domain</span>
          <span class="font-label-md">Gestión Escolar</span>
        </RouterLink>
      </nav>
    </div>

    <!-- Sidebar Footer -->
    <div class="mt-auto p-gutter">
      <div class="bg-inverse-surface rounded-xxl p-md text-white relative overflow-hidden group">
        <div class="absolute -right-4 -top-4 w-16 h-16 bg-primary/20 rounded-full transition-transform group-hover:scale-150"></div>
        <div class="relative z-10">
          <div class="w-10 h-10 bg-primary-container rounded-full flex items-center justify-center mb-3">
            <span class="material-symbols-outlined text-on-primary-container">support_agent</span>
          </div>
          <h3 class="font-headline-md text-[16px] mb-1">Centro de Soporte</h3>
          <p class="text-label-sm opacity-70 mb-4">¿Necesitas ayuda con los anexos?</p>
          <button
            class="w-full bg-white text-zinc-900 hover:bg-zinc-100 py-2.5 rounded-xl font-label-md transition-all active:scale-95 cursor-pointer"
          >
            Ayuda Offline
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>
