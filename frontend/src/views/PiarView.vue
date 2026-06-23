<template>
  <div class="flex flex-col h-full bg-[#F3F4F6] overflow-hidden">
    <!-- TopAppBar -->
    <header class="h-20 w-full flex-shrink-0 bg-surface flex justify-between items-center px-lg border-b border-outline-variant/30">
      <div class="flex items-center gap-4 bg-surface-container-low px-4 py-2 rounded-full border border-outline-variant w-1/3">
        <span class="material-symbols-outlined text-outline">search</span>
        <input class="bg-transparent border-none focus:ring-0 text-body-md w-full outline-none" placeholder="Buscar en PIARs o estudiantes..." type="text" />
      </div>
      <div class="flex items-center gap-sm">
        <button class="hover:bg-surface-container-high rounded-full p-2 transition-all active:scale-95 duration-150">
          <span class="material-symbols-outlined text-on-surface-variant">cloud_done</span>
        </button>
        <button class="hover:bg-surface-container-high rounded-full p-2 transition-all active:scale-95 duration-150 relative">
          <span class="material-symbols-outlined text-on-surface-variant">notifications</span>
          <span class="absolute top-2 right-2 w-2 h-2 bg-error rounded-full"></span>
        </button>
        <div class="w-10 h-10 rounded-full overflow-hidden border-2 border-primary-container">
          <img class="object-cover w-full h-full" src="https://ui-avatars.com/api/?name=User&background=6366F1&color=fff" />
        </div>
      </div>
    </header>

    <!-- Dynamic Content Canvas -->
    <div class="flex-1 p-lg overflow-y-auto">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center h-64">
        <span class="material-symbols-outlined animate-spin text-primary text-4xl mb-4">progress_activity</span>
        <p class="text-on-surface-variant font-medium">Cargando PIAR y contexto del estudiante...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="bg-error-container text-on-error-container p-6 rounded-2xl">
        <h3 class="font-bold flex items-center gap-2"><span class="material-symbols-outlined">error</span> Error</h3>
        <p>{{ error }}</p>
      </div>

      <!-- No PIAR State -->
      <div v-else-if="!activePiar" class="flex flex-col items-center justify-center h-64 space-y-4">
        <span class="material-symbols-outlined text-6xl text-outline-variant">description</span>
        <h2 class="text-headline-sm font-bold text-on-surface">No hay un PIAR activo para este estudiante</h2>
        <button @click="iniciarPiar" class="px-6 py-3 bg-primary text-on-primary rounded-xl font-bold flex items-center gap-2 hover:opacity-90 transition-all cursor-pointer">
          <span class="material-symbols-outlined">add</span>
          Iniciar PIAR
        </button>
      </div>

      <!-- Active PIAR State -->
      <div v-else class="grid grid-cols-12 gap-lg">
        <!-- Left Panel (Student Context) - 40% -->
        <div class="col-span-12 lg:col-span-5 space-y-lg">
          <!-- Student Summary Card -->
          <section class="glass-card bg-surface/80 rounded-2xl p-lg space-y-sm shadow-sm border border-outline-variant/30">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-4">
                <div class="w-16 h-16 rounded-2xl overflow-hidden bg-primary-fixed flex items-center justify-center text-on-primary-fixed text-2xl font-bold uppercase">
                  {{ estudiante?.nombres?.charAt(0) }}{{ estudiante?.apellidos?.charAt(0) }}
                </div>
                <div>
                  <h2 class="text-headline-md font-bold text-on-surface">{{ estudiante?.nombres }} {{ estudiante?.apellidos }}</h2>
                  <p class="text-body-md text-on-surface-variant">ID: {{ estudiante?.numero_documento }}</p>
                </div>
              </div>
              <span v-if="estudiante?.entorno_salud?.diagnostico_medico" class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-label-md font-bold uppercase tracking-wider">
                DIAGNÓSTICO MÉDICO
              </span>
            </div>
            
            <div class="grid grid-cols-2 gap-md pt-md">
              <div class="space-y-xs">
                <h3 class="text-label-md font-bold text-tertiary-container flex items-center gap-1">
                  <span class="material-symbols-outlined text-[18px]">verified</span> Habilidades
                </h3>
                <ul class="space-y-2">
                  <li class="text-body-md text-on-surface-variant bg-tertiary/10 p-2 rounded-xl flex items-center gap-2">
                    <span class="w-1.5 h-1.5 bg-tertiary rounded-full flex-shrink-0"></span> {{ activePiar.caracteristicas?.descripcion_habilidades || 'No registradas' }}
                  </li>
                </ul>
              </div>
              <div class="space-y-xs">
                <h3 class="text-label-md font-bold text-error flex items-center gap-1">
                  <span class="material-symbols-outlined text-[18px]">warning</span> Gustos / Intereses
                </h3>
                <ul class="space-y-2">
                  <li class="text-body-md text-on-surface-variant bg-error/5 p-2 rounded-xl flex items-center gap-2">
                    <span class="w-1.5 h-1.5 bg-error rounded-full flex-shrink-0"></span> {{ activePiar.caracteristicas?.descripcion_gustos_intereses || 'No registrados' }}
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <!-- Curricular Target Card -->
          <section class="glass-card bg-surface/80 rounded-2xl p-lg border-l-4 border-[#6366F1] shadow-sm border-r border-t border-b border-outline-variant/30">
            <div class="flex items-center justify-between mb-sm">
              <h3 class="text-label-md font-bold text-primary flex items-center gap-2 uppercase tracking-wide">
                <span class="material-symbols-outlined">target</span> Meta de Aprendizaje / Área
              </h3>
              <select v-model="aiForm.area" class="text-label-sm text-outline bg-transparent border-none outline-none font-bold cursor-pointer">
                <option value="Matemáticas">Matemáticas</option>
                <option value="Lenguaje">Lenguaje</option>
                <option value="Ciencias">Ciencias</option>
                <option value="Convivencia">Convivencia</option>
              </select>
            </div>
            <textarea 
              v-model="aiForm.objetivos"
              class="w-full text-body-md font-semibold text-on-surface leading-tight bg-transparent border-none outline-none resize-none p-0 focus:ring-0"
              placeholder="Ej: DBA 3: Resolución de sumas y restas con decimales en contextos cotidianos."
              rows="2"
            ></textarea>
          </section>

          <!-- Barrier Definition -->
          <div class="bg-surface-container-high/50 p-md rounded-2xl border border-dashed border-error/50 flex flex-col gap-2">
            <h3 class="text-label-md font-bold text-error flex items-center gap-2 uppercase tracking-wide">
              <span class="material-symbols-outlined">warning</span> Barreras Identificadas
            </h3>
            <textarea 
              v-model="aiForm.barreras"
              class="w-full text-body-md text-on-surface-variant bg-transparent border-none outline-none resize-none p-0 focus:ring-0"
              placeholder="Describa la barrera que el estudiante presenta frente a esta meta de aprendizaje..."
              rows="2"
            ></textarea>
          </div>
        </div>

        <!-- Right Panel (AI Agent & Matrix) - 60% -->
        <div class="col-span-12 lg:col-span-7 flex flex-col gap-lg">
          <!-- AI Prompt Widget -->
          <section class="glass-card bg-surface/80 rounded-2xl p-lg shadow-sm border border-outline-variant/30">
            <div class="flex items-center gap-3 mb-md">
              <div class="w-10 h-10 bg-[#6366F1] rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
                <span class="material-symbols-outlined text-white" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
              </div>
              <h2 class="text-headline-md font-bold text-on-surface">Agente Pedagógico DUA</h2>
            </div>
            <div class="relative">
              <textarea
                v-model="aiForm.instrucciones"
                class="w-full h-32 bg-surface-container-lowest border border-outline-variant rounded-xl p-md text-body-md focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none outline-none"
                placeholder="Instrucciones adicionales para la IA... (ej: 'Considera usar su interés en la botánica y pide apoyos visuales')"
              ></textarea>
              <div class="absolute bottom-4 right-4 flex gap-2">
                <button
                  @click="solicitarIA"
                  :disabled="isGeneratingAI || !aiForm.barreras || !aiForm.objetivos"
                  class="bg-[#6366F1] text-white py-2 px-4 rounded-xl font-bold flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all shadow-md shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span class="material-symbols-outlined" :class="{ 'animate-spin': isGeneratingAI }">
                    {{ isGeneratingAI ? 'progress_activity' : 'auto_awesome' }}
                  </span>
                  {{ isGeneratingAI ? 'Generando...' : 'Generar Ajustes' }}
                </button>
              </div>
            </div>
            
            <!-- AI Response Proposal (Temporal) -->
            <div v-if="propuestaIA" class="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-xl relative animate-fade-in">
              <button @click="propuestaIA = ''" class="absolute top-2 right-2 text-outline hover:text-error transition-colors cursor-pointer">
                <span class="material-symbols-outlined text-[20px]">close</span>
              </button>
              <h4 class="font-bold text-primary mb-2 flex items-center gap-2"><span class="material-symbols-outlined text-[18px]">lightbulb</span> Propuesta DUA</h4>
              <p class="text-body-md text-on-surface-variant whitespace-pre-wrap mb-4">{{ propuestaIA }}</p>
              <div class="flex justify-end">
                <button @click="guardarPropuestaEnMatriz" class="bg-primary text-on-primary px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:opacity-90 transition-all cursor-pointer">
                  <span class="material-symbols-outlined text-[18px]">add_task</span> Añadir a Matriz
                </button>
              </div>
            </div>
          </section>

          <!-- DUA Adjustments Grid (The Matrix) -->
          <section class="glass-card bg-surface/80 rounded-2xl flex-1 flex flex-col overflow-hidden shadow-sm border border-outline-variant/30 max-h-[500px]">
            <div class="p-md bg-surface-container-low border-b border-outline-variant flex justify-between items-center">
              <h3 class="font-bold text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">grid_view</span>
                Matriz de Ajustes (Anexo 2)
              </h3>
            </div>
            <div class="flex-1 overflow-auto">
              <table class="w-full text-left border-collapse">
                <thead class="sticky top-0 bg-surface-container-lowest/90 backdrop-blur z-10">
                  <tr class="border-b border-outline-variant/50">
                    <th class="px-md py-4 text-label-md font-bold text-on-surface-variant bg-surface-container-low/50">Área</th>
                    <th class="px-md py-4 text-label-md font-bold text-on-surface-variant bg-surface-container-low/50">Barrera</th>
                    <th class="px-md py-4 text-label-md font-bold text-on-surface-variant bg-surface-container-low/50">Ajuste Propuesto (DUA)</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-outline-variant/30">
                  <tr v-if="!activePiar.ajustes_razonables || activePiar.ajustes_razonables.length === 0">
                    <td colspan="3" class="px-md py-8 text-center text-outline">No hay ajustes registrados. Usa el Agente DUA para generar el primero.</td>
                  </tr>
                  <tr v-for="ajuste in activePiar.ajustes_razonables" :key="ajuste.id" class="hover:bg-primary/5 transition-colors group">
                    <td class="px-md py-4 align-top">
                      <span class="bg-primary-container text-on-primary-container px-2 py-1 rounded text-xs font-bold">{{ ajuste.area }}</span>
                    </td>
                    <td class="px-md py-4 align-top">
                      <p class="text-body-md text-on-surface font-medium">{{ ajuste.barreras_evidenciadas }}</p>
                    </td>
                    <td class="px-md py-4 align-top">
                      <p class="text-body-md text-on-surface-variant leading-relaxed whitespace-pre-wrap">{{ ajuste.ajustes_estrategias }}</p>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePiarStore } from '../stores/piar'
import { storeToRefs } from 'pinia'

const route = useRoute()
const piarStore = usePiarStore()
const { activePiar, isGeneratingAI, isLoading, error } = storeToRefs(piarStore)

const estudianteId = route.params.id as string
const estudiante = ref<any>(null)

// Formulario reactivo para la IA
const aiForm = ref({
  area: 'Matemáticas',
  objetivos: '',
  barreras: '',
  instrucciones: ''
})

const propuestaIA = ref('')

onMounted(async () => {
  // Cargar estudiante y luego PIAR
  try {
    const res = await fetch(`http://localhost:8000/api/v1/estudiantes/${estudianteId}`)
    if (res.ok) {
      estudiante.value = await res.json()
    }
  } catch (e) {
    console.error("Error fetching student", e)
  }
  
  await piarStore.fetchPiarForStudent(estudianteId)
})

const iniciarPiar = async () => {
  await piarStore.createPiar(estudianteId)
}

const solicitarIA = async () => {
  try {
    const recomendacion = await piarStore.generateAIAjustes(
      aiForm.value.barreras,
      aiForm.value.objetivos,
      aiForm.value.area,
      aiForm.value.instrucciones
    )
    propuestaIA.value = recomendacion
  } catch (e) {
    console.error(e)
  }
}

const guardarPropuestaEnMatriz = async () => {
  try {
    await piarStore.saveAjuste(
      aiForm.value.area,
      aiForm.value.objetivos,
      aiForm.value.barreras,
      propuestaIA.value
    )
    // Limpiar después de guardar
    propuestaIA.value = ''
    aiForm.value.barreras = ''
    aiForm.value.objetivos = ''
  } catch (e) {
    alert(error.value) // Mostrar error (ej: si no hay periodo activo)
  }
}
</script>

<style scoped>
.glass-card {
  backdrop-filter: blur(12px);
}
/* Tailwind animate plugin fallback */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}
</style>
