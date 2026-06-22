<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStudentsStore } from '../stores/students'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const studentsStore = useStudentsStore()
const authStore = useAuthStore()

// State
const searchQuery = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Load data on mount
onMounted(async () => {
  await loadStudents()
})

const loadStudents = async () => {
  await studentsStore.fetchStudents()
}

// Search and filter logic
const filteredStudents = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) return studentsStore.students

  return studentsStore.students.filter(student => 
    student.nombres.toLowerCase().includes(query) ||
    student.apellidos.toLowerCase().includes(query) ||
    student.numero_documento.includes(query)
  )
})

// Pagination
const totalPages = computed(() => {
  return Math.ceil(filteredStudents.value.length / itemsPerPage.value) || 1
})

const paginatedStudents = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredStudents.value.slice(start, end)
})

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

// Navigation helpers
const goToAddStudent = () => {
  studentsStore.clearDraft()
  router.push('/estudiantes/formulario')
}

const goToEditStudent = (id: string) => {
  router.push(`/estudiantes/formulario/${id}`)
}

const goToCreatePiar = (studentId: string) => {
  // Enrutado temporal a Dashboard por ahora (Módulo 2)
  router.push(`/dashboard?action=create-piar&student_id=${studentId}`)
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div class="flex bg-background text-on-background min-h-screen transition-colors duration-300">
    <!-- SideNavBar -->
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
            <span class="material-symbols-outlined">description</span>
            <span class="font-label-md">PIARs (Anexo 2)</span>
          </a>
          <a
            class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-primary transition-colors hover:bg-surface-container-low rounded-md"
            href="#"
          >
            <span class="material-symbols-outlined">history_edu</span>
            <span class="font-label-md">Actas (Anexo 3)</span>
          </a>
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

    <!-- Main Content Area -->
    <main class="ml-64 flex-1 min-h-screen flex flex-col">
      <!-- Header -->
      <header
        class="h-20 w-full sticky top-0 z-30 bg-background/85 backdrop-blur-md flex justify-between items-center px-gutter border-b border-outline-variant/30 transition-colors duration-300"
      >
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined text-primary text-[28px]">group</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">Gestión de Estudiantes</h2>
        </div>

        <div class="flex items-center gap-4">
          <!-- Add Student Button -->
          <button
            @click="goToAddStudent"
            class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
          >
            <span class="material-symbols-outlined text-[20px]">person_add</span>
            Registrar Estudiante
          </button>
        </div>
      </header>

      <!-- Content Grid -->
      <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
        <!-- Controls Bar -->
        <div class="flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container-lowest p-md border border-outline-variant/30 rounded-xxl shadow-sm transition-colors duration-300">
          <div class="relative w-full md:max-w-[448px] flex items-center">
            <span class="material-symbols-outlined absolute left-4 text-outline">search</span>
            <input
              v-model="searchQuery"
              class="w-full bg-surface border border-outline-variant rounded-full py-2.5 pl-12 pr-4 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-body-md outline-none focus:outline-none dark:text-white"
              placeholder="Buscar por nombre, apellido o documento..."
              type="text"
            />
          </div>
          <div class="flex items-center gap-xs text-label-sm text-outline">
            Total: <span class="font-bold text-on-surface">{{ filteredStudents.length }}</span> estudiantes
          </div>
        </div>

        <!-- Table Card -->
        <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
          <div v-if="studentsStore.loading" class="p-xl flex flex-col items-center justify-center gap-sm text-outline">
            <span class="material-symbols-outlined animate-spin text-[48px] text-primary">progress_activity</span>
            Cargando base de datos escolar...
          </div>

          <div v-else-if="filteredStudents.length === 0" class="p-xl text-center space-y-sm">
            <span class="material-symbols-outlined text-[64px] text-outline">group_off</span>
            <h3 class="font-headline-md text-[20px] text-on-surface">No se encontraron estudiantes</h3>
            <p class="text-body-md text-outline max-w-[448px] mx-auto">
              Si es la primera vez que ingresas, registra un nuevo estudiante para comenzar su Plan Individual de Ajustes Razonables (PIAR).
            </p>
            <button
              @click="goToAddStudent"
              class="bg-primary/10 hover:bg-primary/20 text-primary px-lg py-3 rounded-xl font-label-md text-label-md inline-flex items-center gap-xs cursor-pointer transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">person_add</span>
              Crear primer estudiante
            </button>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold select-none">
                  <th class="py-4 px-md">Estudiante</th>
                  <th class="py-4 px-md">Identificación</th>
                  <th class="py-4 px-md">Edad</th>
                  <th class="py-4 px-md">Residencia</th>
                  <th class="py-4 px-md">Fecha Registro</th>
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr
                  v-for="student in paginatedStudents"
                  :key="student.id"
                  class="hover:bg-surface-container-low/40 transition-colors duration-200"
                >
                  <td class="py-4 px-md flex items-center gap-xs">
                    <div class="w-9 h-9 bg-primary/10 text-primary rounded-full flex items-center justify-center font-bold text-headline-md text-[14px]">
                      {{ student.nombres.substring(0, 1).toUpperCase() }}
                    </div>
                    <div>
                      <div class="font-bold">{{ student.nombres }} {{ student.apellidos }}</div>
                    </div>
                  </td>
                  <td class="py-4 px-md">
                    <span class="bg-surface-container-high text-on-surface-variant px-2 py-1 rounded text-label-sm font-mono mr-1">
                      {{ student.tipo_documento }}
                    </span>
                    <span class="font-mono text-label-md">{{ student.numero_documento }}</span>
                  </td>
                  <td class="py-4 px-md">
                    {{ student.edad }} años
                  </td>
                  <td class="py-4 px-md text-outline">
                    {{ student.municipio_residencia }}, {{ student.departamento_residencia }}
                  </td>
                  <td class="py-4 px-md text-outline text-[13px]">
                    {{ formatDate(student.created_at) }}
                  </td>
                  <td class="py-4 px-md text-right">
                    <div class="flex items-center justify-end gap-xs">
                      <!-- Edit Anexo 1 -->
                      <button
                        @click="goToEditStudent(student.id)"
                        class="p-2 text-primary hover:bg-primary/5 rounded-full transition-all cursor-pointer"
                        title="Editar Registro Pedagógico (Anexo 1)"
                      >
                        <span class="material-symbols-outlined text-[20px]">edit_note</span>
                      </button>

                      <!-- Create PIAR (Anexo 2) -->
                      <button
                        @click="goToCreatePiar(student.id)"
                        class="p-2 text-tertiary hover:bg-tertiary/5 rounded-full transition-all cursor-pointer"
                        title="Diseñar PIAR (Anexo 2)"
                      >
                        <span class="material-symbols-outlined text-[20px]">assignment</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination Bar -->
          <div
            v-if="filteredStudents.length > 0"
            class="flex justify-between items-center p-md bg-surface-container border-t border-outline-variant/30 text-label-sm text-outline"
          >
            <div>
              Mostrando del {{ (currentPage - 1) * itemsPerPage + 1 }} al 
              {{ Math.min(currentPage * itemsPerPage, filteredStudents.length) }} de 
              {{ filteredStudents.length }}
            </div>
            <div class="flex items-center gap-xs">
              <button
                @click="prevPage"
                :disabled="currentPage === 1"
                class="p-1.5 rounded-lg border border-outline-variant/40 hover:bg-surface-container-high transition-all cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
              >
                <span class="material-symbols-outlined text-[18px]">chevron_left</span>
              </button>
              <span class="font-bold px-2">Página {{ currentPage }} de {{ totalPages }}</span>
              <button
                @click="nextPage"
                :disabled="currentPage === totalPages"
                class="p-1.5 rounded-lg border border-outline-variant/40 hover:bg-surface-container-high transition-all cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
              >
                <span class="material-symbols-outlined text-[18px]">chevron_right</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.star-icon {
  font-variation-settings: 'FILL' 1;
}
</style>
