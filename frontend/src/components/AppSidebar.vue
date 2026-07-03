<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const authStore = useAuthStore()

function isActive(...names: string[]): boolean {
  return names.includes(route.name as string)
}
</script>

<template>
  <aside
    class="w-64 h-screen fixed left-0 top-0 flex flex-col bg-surface-container-lowest border-r border-outline-variant z-40 transition-colors duration-300"
  >
    <div class="px-4 py-6">
      <div class="flex items-center gap-3 mb-8 px-2">
        <h1 class="text-headline-md font-display font-bold text-primary">OpenPiar</h1>
      </div>
      
      <nav class="space-y-1">
        <p class="text-label-sm uppercase tracking-wider text-outline mb-3 px-3 select-none">Vista general</p>
        <RouterLink
          to="/dashboard"
          class="flex items-center gap-3 px-3 py-3 w-full rounded-xl transition-colors font-medium text-[14px] leading-none"
          :class="isActive('dashboard') ? 'text-on-primary-container bg-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'"
        >
          <span class="material-symbols-outlined text-[22px] shrink-0">dashboard</span>
          <span>Dashboard</span>
        </RouterLink>
        <RouterLink
          to="/estudiantes"
          class="flex items-center gap-3 px-3 py-3 w-full rounded-xl transition-colors font-medium text-[14px] leading-none"
          :class="isActive('estudiantes', 'estudiante-form') ? 'text-on-primary-container bg-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'"
        >
          <span class="material-symbols-outlined text-[22px] shrink-0">group</span>
          <span>Estudiantes</span>
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.rol === 'directivo' || authStore.user?.es_director"
          to="/directorio"
          class="flex items-center gap-3 px-3 py-3 w-full rounded-xl transition-colors font-medium text-[14px] leading-none"
          :class="isActive('directorio') ? 'text-on-primary-container bg-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'"
        >
          <span class="material-symbols-outlined text-[22px] shrink-0">contacts</span>
          <span>Directorio</span>
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.rol === 'directivo'"
          to="/gestion-escolar"
          class="flex items-center gap-3 px-3 py-3 w-full rounded-xl transition-colors font-medium text-[14px] leading-none"
          :class="isActive('gestion-escolar') ? 'text-on-primary-container bg-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'"
        >
          <span class="material-symbols-outlined text-[22px] shrink-0">domain</span>
          <span>Gestión escolar</span>
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.rol === 'directivo'"
          to="/gestion-directiva"
          class="flex items-center gap-3 px-3 py-3 w-full rounded-xl transition-colors font-medium text-[14px] leading-none"
          :class="isActive('gestion-directiva') ? 'text-on-primary-container bg-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'"
        >
          <span class="material-symbols-outlined text-[22px] shrink-0">admin_panel_settings</span>
          <span>Gestión directiva</span>
        </RouterLink>
      </nav>
    </div>
    <div class="p-3 border-t border-outline-variant/30 mt-auto">
      <span class="text-[11px] text-on-surface-variant/60 block text-center">OpenPiar v0.1.0</span>
    </div>
  </aside>
</template>