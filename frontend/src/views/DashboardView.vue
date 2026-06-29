<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useDashboardStore } from '../stores/dashboard'

const router = useRouter()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()

onMounted(() => {
  dashboardStore.fetchStats()
})

const stats = computed(() => dashboardStore.stats)

const estadoLabels: Record<string, string> = {
  borrador: 'Borrador',
  generando_ia: 'Generando IA',
  en_revision: 'En revisión',
  firmado: 'Firmado',
  vencido: 'Vencido',
}

const estadoColors: Record<string, string> = {
  borrador: 'bg-slate-400',
  generando_ia: 'bg-amber-400',
  en_revision: 'bg-blue-400',
  firmado: 'bg-emerald-500',
  vencido: 'bg-red-400',
}

const maxAreaCount = computed(() =>
  Math.max(1, ...(stats.value?.ajustes_por_area.map(a => a.total) || [1]))
)

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }) + ' ' +
         d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
    <!-- Loading -->
    <div v-if="dashboardStore.loading" class="p-xl flex flex-col items-center justify-center gap-sm text-outline">
      <span class="material-symbols-outlined animate-spin text-[48px] text-primary">progress_activity</span>
      Cargando estadísticas...
    </div>

    <!-- Error -->
    <div v-else-if="dashboardStore.error" class="p-xl text-center">
      <span class="material-symbols-outlined text-[48px] text-error">error</span>
      <p class="text-error mt-sm">{{ dashboardStore.error }}</p>
      <button @click="dashboardStore.fetchStats()" class="mt-md bg-primary text-white px-lg py-2 rounded-xl font-label-md cursor-pointer">Reintentar</button>
    </div>

    <template v-else-if="stats">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- Hero Banner (Col-8) -->
        <div class="lg:col-span-8 bg-brand-periwinkle rounded-xxl p-8 md:p-10 text-white relative overflow-hidden flex items-center shadow-lg shadow-brand-periwinkle/10 min-h-[260px]">
          <div class="relative z-10 max-w-[512px]">
            <h2 class="font-headline-lg text-white text-headline-lg mb-4">
              Hola, {{ authStore.user?.nombre || 'Docente' }}.
            </h2>
            <p class="text-body-lg text-white/90 mb-8 font-body-lg">
              Gestionas <span class="font-bold">{{ stats.total_estudiantes }}</span> estudiantes.
              <template v-if="stats.piars_activos > 0">
                <span class="font-bold">{{ stats.piars_activos }} PIARs activos</span> requieren tu atención.
              </template>
              <template v-else>
                Todos los PIARs están al día.
              </template>
            </p>
            <button
              @click="router.push('/estudiantes')"
              class="bg-white text-brand-periwinkle px-8 py-3.5 rounded-xl font-bold flex items-center gap-3 hover:shadow-xl transition-all active:scale-95 group cursor-pointer"
            >
              Ver estudiantes
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

        <!-- KPI Cards (Col-4) -->
        <div class="lg:col-span-4 grid grid-cols-2 gap-gutter">
          <div class="bg-surface-container-lowest rounded-xxl p-md border border-outline-variant/30 flex flex-col justify-center transition-colors duration-300">
            <span class="text-label-sm text-outline">Estudiantes</span>
            <span class="font-headline-lg text-headline-lg text-on-surface">{{ stats.total_estudiantes }}</span>
          </div>
          <div class="bg-surface-container-lowest rounded-xxl p-md border border-outline-variant/30 flex flex-col justify-center transition-colors duration-300">
            <span class="text-label-sm text-outline">PIARs activos</span>
            <span class="font-headline-lg text-headline-lg text-primary">{{ stats.piars_activos }}</span>
          </div>
          <div class="bg-surface-container-lowest rounded-xxl p-md border border-outline-variant/30 flex flex-col justify-center transition-colors duration-300">
            <span class="text-label-sm text-outline">PIARs firmados</span>
            <span class="font-headline-lg text-headline-lg text-emerald-600">{{ stats.piars_firmados }}</span>
          </div>
          <div class="bg-surface-container-lowest rounded-xxl p-md border border-outline-variant/30 flex flex-col justify-center transition-colors duration-300">
            <span class="text-label-sm text-outline">Ajustes totales</span>
            <span class="font-headline-lg text-headline-lg text-on-surface">{{ stats.total_ajustes }}</span>
          </div>
        </div>
      </div>

      <!-- Row 2: PIARs por estado + Actas incompletas -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- PIARs por estado (Col-8) -->
        <div class="lg:col-span-8 bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 transition-colors duration-300">
          <h3 class="font-headline-md text-on-surface text-[18px] mb-4">Estado de los PIARs</h3>
          <div class="flex items-end gap-1 h-24 mb-3">
            <template v-for="e in stats.piars_por_estado" :key="e.estado">
              <div
                class="flex-1 rounded-t-md transition-all cursor-default relative group"
                :class="estadoColors[e.estado] || 'bg-slate-300'"
                :style="{ height: (e.total / Math.max(1, stats.total_piars)) * 100 + '%' }"
              >
                <div class="absolute -top-7 left-1/2 -translate-x-1/2 bg-on-surface text-surface text-label-xs px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                  {{ estadoLabels[e.estado] || e.estado }}: {{ e.total }}
                </div>
              </div>
            </template>
          </div>
          <div class="flex flex-wrap gap-md text-label-sm text-outline">
            <template v-for="e in stats.piars_por_estado" :key="e.estado">
              <div class="flex items-center gap-1">
                <span class="w-3 h-3 rounded-full inline-block" :class="estadoColors[e.estado] || 'bg-slate-300'"></span>
                {{ estadoLabels[e.estado] || e.estado }} ({{ e.total }})
              </div>
            </template>
          </div>
        </div>

        <!-- Actas incompletas (Col-4) -->
        <div class="lg:col-span-4 bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 flex flex-col justify-center items-center transition-colors duration-300">
          <div class="w-16 h-16 rounded-full flex items-center justify-center mb-3"
            :class="stats.actas_firmas_incompletas > 0 ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'">
            <span class="material-symbols-outlined text-[32px]">
              {{ stats.actas_firmas_incompletas > 0 ? 'pending_actions' : 'verified' }}
            </span>
          </div>
          <span class="font-headline-lg text-headline-lg text-on-surface">{{ stats.actas_firmas_incompletas }}</span>
          <span class="text-label-sm text-outline text-center">Actas con firmas<br>incompletas</span>
        </div>
      </div>

      <!-- Row 3: Ajustes por área + Actividad reciente -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        <!-- Ajustes por área (Col-6) -->
        <div class="lg:col-span-6 bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 transition-colors duration-300">
          <h3 class="font-headline-md text-on-surface text-[18px] mb-4">Ajustes por área</h3>
          <div v-if="stats.ajustes_por_area.length === 0" class="text-outline text-label-md py-8 text-center">
            No hay ajustes registrados aún.
          </div>
          <div v-else class="space-y-3">
            <div v-for="a in stats.ajustes_por_area" :key="a.area" class="flex items-center gap-3">
              <span class="text-label-sm text-on-surface w-32 truncate">{{ a.area }}</span>
              <div class="flex-1 h-3 bg-surface-container rounded-full overflow-hidden">
                <div class="h-full bg-primary rounded-full transition-all" :style="{ width: (a.total / maxAreaCount) * 100 + '%' }"></div>
              </div>
              <span class="text-label-sm font-bold text-on-surface w-8 text-right">{{ a.total }}</span>
            </div>
          </div>
        </div>

        <!-- Actividad reciente (Col-6) -->
        <div class="lg:col-span-6 bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 transition-colors duration-300">
          <h3 class="font-headline-md text-on-surface text-[18px] mb-4">Actividad reciente</h3>
          <div v-if="stats.actividad_reciente.length === 0" class="text-outline text-label-md py-8 text-center">
            No hay actividad registrada aún.
          </div>
          <div v-else class="space-y-3">
            <div v-for="(act, i) in stats.actividad_reciente" :key="i" class="flex items-start gap-3">
              <div class="w-2 h-2 rounded-full mt-2 flex-shrink-0" :class="act.tipo === 'piar' ? 'bg-primary' : 'bg-tertiary'"></div>
              <div class="flex-1 min-w-0">
                <p class="text-label-md text-on-surface truncate">{{ act.descripcion }}</p>
                <p class="text-label-sm text-outline">{{ act.estudiante_nombre }} — {{ formatDate(act.fecha) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 4: Periodo activo -->
      <div v-if="stats.periodo_activo_nombre" class="bg-surface-container-lowest rounded-xxl p-md md:p-lg border border-outline-variant/30 transition-colors duration-300 flex flex-col md:flex-row items-center justify-between gap-md">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined text-primary text-[28px]">calendar_today</span>
          <div>
            <p class="font-headline-md text-on-surface text-[16px]">{{ stats.periodo_activo_nombre }}</p>
            <p class="text-label-sm text-outline">
              {{ stats.ajustes_este_periodo }} ajustes creados este periodo
              <template v-if="stats.puntuacion_promedio !== null">
                · Efectividad promedio: {{ stats.puntuacion_promedio }}/5 ⭐
              </template>
            </p>
          </div>
        </div>
        <button
          @click="router.push('/estudiantes')"
          class="bg-primary/10 hover:bg-primary/20 text-primary px-lg py-2.5 rounded-xl font-label-md text-label-md cursor-pointer transition-all"
        >
          Ver PIARs activos →
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
