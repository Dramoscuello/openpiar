<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<template>
  <div class="min-h-screen bg-surface-container-lowest flex flex-col items-center justify-center p-4">
    <!-- Loading -->
    <div v-if="loading" class="text-center">
      <span class="material-symbols-outlined animate-spin text-primary text-5xl mb-4">progress_activity</span>
      <p class="text-on-surface-variant">Cargando información del PIAR...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="bg-error-container text-on-error-container p-6 rounded-2xl max-w-md text-center shadow-md border border-error/20">
      <span class="material-symbols-outlined text-4xl text-error mb-3">error</span>
      <h2 class="font-bold text-headline-md mb-2">Código no válido</h2>
      <p class="text-body-md">{{ error }}</p>
    </div>

    <!-- PIAR View -->
    <div v-else-if="piar" class="w-full max-w-2xl space-y-4 pb-12">
      <!-- Header -->
      <div class="bg-primary text-on-primary rounded-2xl p-lg shadow-lg">
        <div class="flex items-center gap-3 mb-3">
          <span class="material-symbols-outlined text-4xl">school</span>
          <div>
            <h1 class="text-headline-lg font-bold">{{ piar.estudiante_nombre }}</h1>
            <p class="text-body-md opacity-80">
              {{ piar.grado ? piar.grado + ' — ' : '' }}Año lectivo {{ piar.anio_lectivo }}
            </p>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap">
          <span class="bg-white/20 px-3 py-1 rounded-full text-label-sm font-bold">
            {{ piar.periodo_activo || 'Sin periodo activo' }}
          </span>
          <span class="bg-white/20 px-3 py-1 rounded-full text-label-sm font-bold uppercase">
            {{ piar.estado }}
          </span>
        </div>
      </div>

      <!-- Ajustes DUA -->
      <section class="bg-surface rounded-2xl p-lg shadow-sm border border-outline-variant/20">
        <h2 class="text-headline-md font-bold text-primary flex items-center gap-2 mb-4">
          <span class="material-symbols-outlined">grid_on</span>
          Ajustes Razonables DUA
        </h2>
        <div v-if="piar.ajustes.length === 0" class="text-center py-6 text-on-surface-variant">
          <span class="material-symbols-outlined text-3xl mb-2">grid_off</span>
          <p>No se han registrado ajustes DUA para este periodo.</p>
        </div>
        <div v-else class="space-y-3">
          <div v-for="(a, idx) in piar.ajustes" :key="idx" class="bg-surface-container-low rounded-xl p-4 border border-outline-variant/20">
            <div class="flex items-center gap-2 mb-2">
              <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-sm font-bold">
                {{ a.area }}
              </span>
              <span v-if="a.titulo_tema" class="text-label-sm text-on-surface-variant">
                Tema: {{ a.titulo_tema }}
              </span>
            </div>
            <p class="text-body-sm text-on-surface-variant mb-2">
              <span class="font-bold text-on-surface">Objetivos:</span> {{ a.objetivos_propositos }}
            </p>
            <p class="text-body-sm text-on-surface-variant">
              <span class="font-bold text-on-surface">Estrategias DUA:</span> {{ a.ajustes_estrategias }}
            </p>
            <div v-if="a.puntuacion" class="mt-2 flex items-center gap-1">
              <span class="text-label-xs text-on-surface-variant">Efectividad:</span>
              <span v-for="s in 5" :key="s" class="material-symbols-outlined text-sm" :class="s <= a.puntuacion! ? 'text-amber-500' : 'text-outline-variant'">
                {{ s <= a.puntuacion! ? 'star' : 'star' }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Compromisos de Casa -->
      <section v-if="piar.compromisos_casa.length > 0" class="bg-surface rounded-2xl p-lg shadow-sm border border-outline-variant/20">
        <h2 class="text-headline-md font-bold text-primary flex items-center gap-2 mb-4">
          <span class="material-symbols-outlined">home</span>
          Compromisos en Casa
        </h2>
        <div class="space-y-3">
          <div v-for="(c, idx) in piar.compromisos_casa" :key="idx" class="bg-surface-container-low rounded-xl p-4 border border-outline-variant/20">
            <p class="font-bold text-on-surface text-body-md">{{ c.nombre_actividad }}</p>
            <p class="text-body-sm text-on-surface-variant mt-1">{{ c.descripcion_estrategia }}</p>
            <span class="inline-block mt-2 bg-tertiary-container text-on-tertiary-container px-2.5 py-0.5 rounded-full text-label-xs font-bold uppercase">
              {{ c.frecuencia }}
            </span>
          </div>
        </div>
      </section>

      <!-- Firmas del Acta -->
      <section class="bg-surface rounded-2xl p-lg shadow-sm border border-outline-variant/20">
        <h2 class="text-headline-md font-bold text-primary flex items-center gap-2 mb-4">
          <span class="material-symbols-outlined">assignment_turned_in</span>
          Acta de Acuerdo
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="flex items-center gap-3 p-3 rounded-xl border border-outline-variant/20" :class="piar.firmado_estudiante ? 'bg-emerald-50 border-emerald-300' : 'bg-surface-container-low'">
            <span class="material-symbols-outlined" :class="piar.firmado_estudiante ? 'text-emerald-600' : 'text-outline-variant'">
              {{ piar.firmado_estudiante ? 'check_circle' : 'radio_button_unchecked' }}
            </span>
            <div>
              <p class="font-bold text-body-sm text-on-surface">Estudiante</p>
              <button
                v-if="!piar.firmado_estudiante"
                @click="firmar('estudiante')"
                :disabled="isFirmando"
                class="text-label-xs text-primary font-bold hover:underline cursor-pointer disabled:opacity-40"
              >
                {{ isFirmandoTipo === 'estudiante' && isFirmando ? 'Firmando...' : 'Firmar' }}
              </button>
              <span v-else class="text-label-xs text-emerald-600 font-bold">Firmado</span>
            </div>
          </div>

          <div class="flex items-center gap-3 p-3 rounded-xl border border-outline-variant/20" :class="piar.firmado_acudiente ? 'bg-emerald-50 border-emerald-300' : 'bg-surface-container-low'">
            <span class="material-symbols-outlined" :class="piar.firmado_acudiente ? 'text-emerald-600' : 'text-outline-variant'">
              {{ piar.firmado_acudiente ? 'check_circle' : 'radio_button_unchecked' }}
            </span>
            <div>
              <p class="font-bold text-body-sm text-on-surface">Acudiente / Familia</p>
              <button
                v-if="!piar.firmado_acudiente"
                @click="firmar('acudiente')"
                :disabled="isFirmando"
                class="text-label-xs text-primary font-bold hover:underline cursor-pointer disabled:opacity-40"
              >
                {{ isFirmandoTipo === 'acudiente' && isFirmando ? 'Firmando...' : 'Firmar' }}
              </button>
              <span v-else class="text-label-xs text-emerald-600 font-bold">Firmado</span>
            </div>
          </div>

          <div class="flex items-center gap-3 p-3 rounded-xl border border-outline-variant/20 bg-surface-container-low">
            <span class="material-symbols-outlined" :class="piar.firmado_docentes_aula ? 'text-emerald-600' : 'text-outline-variant'">
              {{ piar.firmado_docentes_aula ? 'check_circle' : 'radio_button_unchecked' }}
            </span>
            <div>
              <p class="font-bold text-body-sm text-on-surface">Docentes de Aula</p>
              <span class="text-label-xs text-on-surface-variant">{{ piar.firmado_docentes_aula ? 'Firmado' : 'Pendiente' }}</span>
            </div>
          </div>

          <div class="flex items-center gap-3 p-3 rounded-xl border border-outline-variant/20 bg-surface-container-low">
            <span class="material-symbols-outlined" :class="piar.firmado_directivo ? 'text-emerald-600' : 'text-outline-variant'">
              {{ piar.firmado_directivo ? 'check_circle' : 'radio_button_unchecked' }}
            </span>
            <div>
              <p class="font-bold text-body-sm text-on-surface">Directivo</p>
              <span class="text-label-xs text-on-surface-variant">{{ piar.firmado_directivo ? 'Firmado' : 'Pendiente' }}</span>
            </div>
          </div>
        </div>

        <div v-if="firmaOk" class="mt-4 bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-emerald-700 text-label-sm font-bold flex items-center gap-2">
          <span class="material-symbols-outlined">check_circle</span>
          {{ firmaOk }}
        </div>
      </section>

      <!-- Descargar PDF -->
      <a
        :href="`/api/v1/familia/${codigo}/acta/pdf`"
        class="w-full flex items-center justify-center gap-2 py-3.5 bg-primary text-on-primary rounded-xl font-bold text-body-md hover:opacity-90 transition-all shadow-md"
      >
        <span class="material-symbols-outlined">download</span>
        Descargar PDF oficial del PIAR
      </a>

      <p class="text-center text-label-xs text-outline-variant pt-2">
        OpenPiar — Decreto 1421 de 2017
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

interface FamiliaPIAR {
  estudiante_nombre: string
  grado: string | null
  anio_lectivo: number
  estado: string
  periodo_activo: string | null
  caracteristicas_descripcion: string | null
  ajustes: Array<{
    area: string
    titulo_tema: string | null
    objetivos_propositos: string
    ajustes_estrategias: string
    puntuacion: number | null
  }>
  compromisos_casa: Array<{
    nombre_actividad: string
    descripcion_estrategia: string
    frecuencia: string
  }>
  firmado_estudiante: boolean
  firmado_acudiente: boolean
  firmado_docente_apoyo: boolean
  firmado_docentes_aula: boolean
  firmado_directivo: boolean
}

const route = useRoute()
const codigo = route.params.codigo as string

const piar = ref<FamiliaPIAR | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const isFirmando = ref(false)
const isFirmandoTipo = ref<string | null>(null)
const firmaOk = ref<string | null>(null)

async function fetchPIAR() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`/api/v1/familia/${codigo}`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Código de acceso no válido o PIAR no disponible.')
    }
    piar.value = await res.json()
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function firmar(rol: string) {
  isFirmando.value = true
  isFirmandoTipo.value = rol
  firmaOk.value = null
  try {
    const res = await fetch(`/api/v1/familia/${codigo}/firmar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rol }),
    })
    if (res.ok) {
      firmaOk.value = `Firma como ${rol} registrada correctamente.`
      if (rol === 'estudiante') piar.value!.firmado_estudiante = true
      else if (rol === 'acudiente') piar.value!.firmado_acudiente = true
    } else {
      const err = await res.json()
      throw new Error(err.detail || 'Error al firmar.')
    }
  } catch (e: any) {
    firmaOk.value = null
    alert(e.message)
  } finally {
    isFirmando.value = false
    isFirmandoTipo.value = null
  }
}

onMounted(() => {
  fetchPIAR()
})
</script>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
