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
        <h1 class="text-headline-md font-display font-bold text-primary">OpenPiar</h1>
      </div>
      
      <nav class="space-y-1">
        <p class="text-label-sm uppercase tracking-wider text-outline mb-4 px-4 select-none">Vista general</p>
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
        <RouterLink
          v-if="authStore.user?.rol === 'directivo' || authStore.user?.es_director"
          to="/directorio"
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          active-class="text-primary font-bold border-r-4 border-primary bg-primary/5 dark:bg-primary/10 rounded-r-md"
        >
          <span class="material-symbols-outlined">contacts</span>
          <span class="font-label-md">Directorio</span>
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.rol === 'directivo'"
          to="/gestion-escolar"
          class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
          active-class="text-primary font-bold border-r-4 border-primary bg-primary/5 dark:bg-primary/10 rounded-r-md"
        >
          <span class="material-symbols-outlined">domain</span>
          <span class="font-label-md">Gestión escolar</span>
        </RouterLink>
      </nav>
    </div>


  </aside>
</template>
