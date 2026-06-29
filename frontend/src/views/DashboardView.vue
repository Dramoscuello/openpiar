<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <!-- Page Content: Bento Grid Layout -->
      <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
          
          <!-- Hero Banner (Col-8) -->
          <div
            class="lg:col-span-8 bg-brand-periwinkle rounded-xxl p-8 md:p-10 text-white relative overflow-hidden flex items-center shadow-lg shadow-brand-periwinkle/10 min-h-[260px]"
          >
            <div class="relative z-10 max-w-[512px]">
              <h2 class="font-headline-lg text-white text-headline-lg mb-4">
                Hola, {{ authStore.user?.nombre || 'Docente' }}.
              </h2>
              <p class="text-body-lg text-white/90 mb-8 font-body-lg">
                Tienes <span class="font-bold">3 PIARs pendientes</span> de firma este trimestre. No dejes que el proceso se detenga.
              </p>
              <button
                class="bg-white text-brand-periwinkle px-8 py-3.5 rounded-xl font-bold flex items-center gap-3 hover:shadow-xl transition-all active:scale-95 group cursor-pointer"
              >
                Ver pendientes
                <span class="material-symbols-outlined group-hover:translate-x-1 transition-transform">arrow_forward</span>
              </button>
            </div>
            <div class="absolute right-0 top-0 h-full w-1/2 opacity-25 pointer-events-none">
              <svg class="h-full w-full" fill="none" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
                <circle cx="200" cy="200" r="150" stroke="white" stroke-dasharray="10 10" stroke-width="2"></circle>
                <circle cx="200" cy="200" r="100" stroke="white" stroke-width="4"></circle>
                <path d="M200 50V350M50 200H350" stroke="white" stroke-linecap="round" stroke-width="2"></path>
              </svg>
            </div>
          </div>

          <!-- Activity & Sync Widget (Col-4) -->
          <div class="lg:col-span-4 bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 flex flex-col justify-between transition-colors duration-300">
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-headline-md text-on-surface text-[18px]">Horas de trabajo</h3>
              <div class="flex items-center gap-1 text-label-sm text-outline px-3 py-1 bg-surface-container-low rounded-full">
                Año <span class="material-symbols-outlined text-[16px]">expand_more</span>
              </div>
            </div>
            
            <div class="flex items-end gap-2 h-28 mb-6">
              <div class="flex-1 bg-surface-container-high rounded-full h-[40%] hover:bg-primary/20 transition-all cursor-pointer"></div>
              <div class="flex-1 bg-surface-container-high rounded-full h-[60%] hover:bg-primary/20 transition-all cursor-pointer"></div>
              <div class="flex-1 bg-surface-container-high rounded-full h-[85%] hover:bg-primary/20 transition-all cursor-pointer"></div>
              <div class="flex-1 bg-primary rounded-full h-[100%] shadow-md shadow-primary/20"></div>
              <div class="flex-1 bg-surface-container-high rounded-full h-[55%] hover:bg-primary/20 transition-all cursor-pointer"></div>
              <div class="flex-1 bg-surface-container-high rounded-full h-[45%] hover:bg-primary/20 transition-all cursor-pointer"></div>
            </div>
            
            <div class="mt-auto space-y-4">
              <div class="flex justify-between items-end mb-2">
                <span class="font-headline-lg text-headline-lg leading-none text-on-surface">3.5h</span>
                <div class="bg-primary/10 text-primary px-3 py-1 rounded-lg text-label-sm font-bold">
                  ¡Buen ritmo! 👋
                </div>
              </div>
              
              <div class="space-y-2">
                <div class="flex justify-between text-label-sm">
                  <span class="text-outline">Sincronización local</span>
                  <span class="text-primary font-bold">85%</span>
                </div>
                <div class="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                  <div class="h-full bg-primary rounded-full" style="width: 85%"></div>
                </div>
                <button class="w-full text-center text-primary font-bold text-label-sm pt-2 hover:underline cursor-pointer">
                  Sincronizar ahora
                </button>
              </div>
            </div>
          </div>

          <!-- Student Highlight (Col-4) -->
          <div
            class="lg:col-span-4 bg-surface-container-lowest border border-outline-variant/30 rounded-xxl p-md md:p-lg group cursor-pointer hover:border-primary-container/40 transition-all duration-300"
          >
            <div class="relative mb-6">
              <div class="w-full h-52 rounded-xl overflow-hidden bg-primary/5 flex items-center justify-center">
                <!-- Fallback Icon since image requires offline asset -->
                <span class="material-symbols-outlined text-[64px] text-outline">school</span>
              </div>
              <div
                class="absolute top-4 right-4 bg-tertiary text-on-tertiary px-4 py-1.5 rounded-full font-label-md shadow-md flex items-center gap-1 text-label-sm"
              >
                <span class="material-symbols-outlined text-[16px]" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                Completo
              </div>
            </div>
            <div>
              <h3 class="font-headline-md text-headline-md text-on-surface mb-1">Mateo Gómez</h3>
              <p class="text-body-md text-outline mb-4 font-body-md">Grado 4°A • PIAR Activo</p>
              <div class="flex items-center gap-4">
                <div class="flex -space-x-3">
                  <div class="w-8 h-8 rounded-full border-2 border-white dark:border-zinc-800 bg-surface-dim flex items-center justify-center text-[10px] font-bold text-on-surface">MG</div>
                  <div class="w-8 h-8 rounded-full border-2 border-white dark:border-zinc-800 bg-primary-fixed flex items-center justify-center text-[10px] font-bold text-primary">+2</div>
                </div>
                <div class="flex-1">
                  <div class="h-1.5 w-full bg-surface-container rounded-full">
                    <div class="h-full bg-primary rounded-full" style="width: 100%"></div>
                  </div>
                </div>
                <span class="text-label-sm font-bold text-primary">100%</span>
              </div>
            </div>
          </div>

          <!-- Processes active timeline (Col-5) -->
          <div class="lg:col-span-5 bg-surface-container-lowest border border-outline-variant/30 rounded-xxl p-md md:p-lg transition-colors duration-300">
            <div class="flex justify-between items-center mb-8">
              <h3 class="font-headline-md text-headline-md text-on-surface">Procesos activos</h3>
              <button class="text-primary font-bold text-label-sm flex items-center gap-1 cursor-pointer hover:underline">
                Ver historial <span class="material-symbols-outlined text-[16px]">open_in_new</span>
              </button>
            </div>
            
            <div class="space-y-6 relative pl-2">
              <div class="absolute left-6 top-2 bottom-2 w-px bg-outline-variant/30"></div>
              
              <!-- Item 1 -->
              <div class="flex gap-4 relative">
                <div class="w-10 h-10 rounded-full bg-primary-fixed border-4 border-white dark:border-zinc-800 flex items-center justify-center z-10 shadow-sm">
                  <span class="material-symbols-outlined text-primary text-[18px]" style="font-variation-settings: 'FILL' 1;">psychology</span>
                </div>
                <div class="flex-1">
                  <div class="flex justify-between items-start mb-1">
                    <h4 class="font-bold text-on-surface text-body-md">Sofía Castro</h4>
                    <span class="text-label-sm text-outline">9 Oct, 23</span>
                  </div>
                  <p class="text-body-md text-on-surface-variant font-body-md mb-2">IA DUA: Sugerencias de ajustes generadas</p>
                  <div class="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div class="h-full bg-primary/40 rounded-full" style="width: 65%"></div>
                  </div>
                </div>
              </div>

              <!-- Item 2 -->
              <div class="flex gap-4 relative">
                <div class="w-10 h-10 rounded-full bg-secondary-fixed border-4 border-white dark:border-zinc-800 flex items-center justify-center z-10 shadow-sm">
                  <span class="material-symbols-outlined text-on-secondary-fixed-variant text-[18px]" style="font-variation-settings: 'FILL' 1;">draw</span>
                </div>
                <div class="flex-1">
                  <div class="flex justify-between items-start mb-1">
                    <h4 class="font-bold text-on-surface text-body-md">Juan Pérez</h4>
                    <span class="text-label-sm text-outline">Hoy, 10:30</span>
                  </div>
                  <p class="text-body-md text-on-surface-variant font-body-md mb-2">Pendiente: Firmas de directivos</p>
                  <div class="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div class="h-full bg-secondary rounded-full" style="width: 40%"></div>
                  </div>
                </div>
              </div>

              <!-- Item 3 -->
              <div class="flex gap-4 relative">
                <div class="w-10 h-10 rounded-full bg-tertiary-fixed border-4 border-white dark:border-zinc-800 flex items-center justify-center z-10 shadow-sm">
                  <span class="material-symbols-outlined text-on-tertiary-fixed-variant text-[18px]" style="font-variation-settings: 'FILL' 1;">verified</span>
                </div>
                <div class="flex-1">
                  <div class="flex justify-between items-start mb-1">
                    <h4 class="font-bold text-on-surface text-body-md">Daniela Ortiz</h4>
                    <span class="text-label-sm text-outline">Ayer</span>
                  </div>
                  <p class="text-body-md text-on-surface-variant font-body-md mb-2">Anexo 2 Completado y Archivado</p>
                  <div class="h-1.5 w-full bg-surface-container rounded-full overflow-hidden">
                    <div class="h-full bg-tertiary rounded-full" style="width: 100%"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agenda (Col-3) -->
          <div class="lg:col-span-3 bg-surface-container-lowest border border-outline-variant/30 rounded-xxl p-md md:p-lg transition-colors duration-300">
            <div class="flex justify-between items-center mb-8">
              <h3 class="font-headline-md text-headline-md text-on-surface">Agenda</h3>
              <div class="p-1 bg-surface-container-low rounded-lg shadow-sm border border-outline-variant/20">
                <span class="material-symbols-outlined text-outline">calendar_today</span>
              </div>
            </div>
            
            <div class="space-y-6">
              <div class="relative pl-6 border-l-4 border-secondary-container">
                <div class="text-label-sm text-outline mb-1 font-label-sm">10:00 AM - 11:30 AM</div>
                <h4 class="font-bold text-on-surface text-body-md mb-2">Reunión familiar</h4>
                <div class="bg-secondary-container text-on-secondary-container px-3 py-2 rounded-xl text-label-sm inline-flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]">family_restroom</span>
                  Est. Juan Pérez
                </div>
              </div>

              <div class="relative pl-6 border-l-4 border-tertiary-fixed">
                <div class="text-label-sm text-outline mb-1 font-label-sm">03:00 PM - 04:00 PM</div>
                <h4 class="font-bold text-on-surface text-body-md mb-2">Ajustes matemáticas</h4>
                <div class="bg-tertiary-fixed text-on-tertiary-fixed-variant px-3 py-2 rounded-xl text-label-sm inline-flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]">calculate</span>
                  Grado 4°A
                </div>
              </div>

              <div
                class="p-4 bg-surface-container-low rounded-xl border border-dashed border-outline-variant/60 text-center cursor-pointer hover:bg-surface-container-high transition-all"
              >
                <span class="material-symbols-outlined text-primary mb-1">add_circle</span>
                <p class="text-label-sm font-bold text-primary">Agendar actividad</p>
              </div>
            </div>
          </div>

        </div>
      </div>
</template>

<style scoped>
/* Transiciones de hover adicionales */
.lg\:col-span-8, .lg\:col-span-4, .lg\:col-span-3, .lg\:col-span-5 {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s ease, box-shadow 0.3s ease;
}

.lg\:col-span-8:hover, .lg\:col-span-4:hover, .lg\:col-span-3:hover, .lg\:col-span-5:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 36px rgba(0,0,0,0.06);
}
</style>
