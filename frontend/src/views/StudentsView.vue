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

// Delete state
const confirmDeleteStudent = ref<{ id: string; nombre: string } | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const promptDelete = (student: any) => {
  deleteError.value = null
  confirmDeleteStudent.value = {
    id: student.id,
    nombre: `${student.nombres} ${student.apellidos}`,
  }
}

const cancelDelete = () => {
  confirmDeleteStudent.value = null
  deleteError.value = null
}

const confirmDelete = async () => {
  if (!confirmDeleteStudent.value) return
  deleting.value = true
  deleteError.value = null
  const ok = await studentsStore.deleteStudent(confirmDeleteStudent.value.id)
  deleting.value = false
  if (ok) {
    confirmDeleteStudent.value = null
  } else {
    deleteError.value = studentsStore.error || 'No se pudo eliminar el estudiante.'
  }
}

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
  router.push(`/estudiantes/${studentId}/piar`)
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

// Import state
const showImportModal = ref(false)
const importFile = ref<File | null>(null)
const importPassword = ref('')
const importGrupoId = ref<string | null>(null)
const isImporting = ref(false)
const importError = ref<string | null>(null)
const grupos = ref<any[]>([])
const successToast = ref('')

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function handleFileDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file && file.name.endsWith('.openpiar')) {
      importFile.value = file
      importError.value = null
    } else if (file) {
      importFile.value = null
      importError.value = 'El archivo debe tener extensión .openpiar'
    }
  }
}

function clearImportFile() {
  importFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function showNotification(msg: string) {
  successToast.value = msg
  setTimeout(() => {
    successToast.value = ''
  }, 4000)
}

async function fetchGrupos() {
  try {
    const res = await fetch('/api/v1/gestion/grupos', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      grupos.value = await res.json()
    }
  } catch (e) {
    console.error('Error fetching groups for import:', e)
  }
}

function abrirModalImportar() {
  showImportModal.value = true
  clearImportFile()
  importPassword.value = ''
  importGrupoId.value = null
  importError.value = null
  fetchGrupos()
}

function cancelarImportar() {
  showImportModal.value = false
  clearImportFile()
  importPassword.value = ''
  importGrupoId.value = null
  importError.value = null
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    importFile.value = target.files[0] || null
    importError.value = null
  } else {
    importFile.value = null
  }
}

async function ejecutarImportar() {
  if (!importFile.value) {
    importError.value = 'Por favor selecciona un archivo .openpiar'
    return
  }
  if (!importPassword.value || importPassword.value.length < 6) {
    importError.value = 'La contraseña debe tener al menos 6 caracteres.'
    return
  }

  isImporting.value = true
  importError.value = null
  try {
    const ok = await studentsStore.importStudent(
      importFile.value,
      importPassword.value,
      importGrupoId.value
    )
    if (ok) {
      showNotification('Estudiante importado exitosamente.')
      showImportModal.value = false
    } else {
      importError.value = studentsStore.error || 'Error al importar el estudiante.'
    }
  } catch (e: any) {
    importError.value = e.message || 'Error al importar el estudiante.'
  } finally {
    isImporting.value = false
  }
}
</script>

<template>
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
          <div class="flex items-center gap-sm">
            <div class="flex items-center gap-xs text-label-sm text-outline">
              Total: <span class="font-bold text-on-surface">{{ filteredStudents.length }}</span> estudiantes
            </div>
            <button
              v-if="authStore.canCreateStudent"
              @click="goToAddStudent"
              class="bg-primary hover:bg-primary-dark text-white px-md py-2 rounded-xl font-label-md text-label-md inline-flex items-center gap-xs cursor-pointer transition-all active:scale-95 shadow-sm"
            >
              <span class="material-symbols-outlined text-[20px]">person_add</span>
              Nuevo estudiante
            </button>
            <button
              v-if="authStore.canCreateStudent"
              @click="abrirModalImportar"
              class="bg-secondary hover:bg-secondary-dark text-white px-md py-2 rounded-xl font-label-md text-label-md inline-flex items-center gap-xs cursor-pointer transition-all active:scale-95 shadow-sm"
            >
              <span class="material-symbols-outlined text-[20px]">upload_file</span>
              Importar
            </button>
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
                  <th class="py-4 px-md">Fecha registro</th>
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
                        v-if="authStore.canCreateStudent"
                        @click="goToEditStudent(student.id)"
                        class="p-2 text-primary hover:bg-primary/5 rounded-full transition-all cursor-pointer"
                        title="Editar Registro Pedagógico (Anexo 1)"
                      >
                        <span class="material-symbols-outlined text-[20px]">edit_note</span>
                      </button>

                    <!-- Delete -->
                      <button
                        v-if="authStore.canCreateStudent"
                        @click="promptDelete(student)"
                        class="p-2 text-error hover:bg-error/5 rounded-full transition-all cursor-pointer"
                        title="Eliminar estudiante"
                      >
                        <span class="material-symbols-outlined text-[20px]">delete</span>
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
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="confirmDeleteStudent"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
        style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
        @click.self="cancelDelete"
      >
        <!-- Dialog -->
        <div
          style="background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.25); width:100%; max-width:440px; padding:28px; box-sizing:border-box;"
        >
          <!-- Icon + Title row -->
          <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
            <div style="flex-shrink:0; width:44px; height:44px; border-radius:50%; background:#fee2e2; display:flex; align-items:center; justify-content:center;">
              <span class="material-symbols-outlined" style="color:#ef4444; font-size:22px;">warning</span>
            </div>
            <h3 style="font-size:17px; font-weight:700; color:#111827; margin:0;">Eliminar estudiante</h3>
          </div>

          <!-- Body text -->
          <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 8px 0;">
            ¿Estás seguro de que deseas eliminar a
            <strong style="color:#111827;">{{ confirmDeleteStudent?.nombre }}</strong>?
          </p>
          <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 20px 0;">
            Se eliminará también toda la información de salud, hogar, trayectoria y matrícula.
            <strong style="color:#ef4444;">Esta acción no se puede deshacer.</strong>
          </p>

          <!-- Error -->
          <div
            v-if="deleteError"
            style="background:#fee2e2; color:#dc2626; border-radius:10px; padding:12px 16px; font-size:13px; margin-bottom:16px;"
          >
            {{ deleteError }}
          </div>

          <!-- Actions -->
          <div style="display:flex; justify-content:flex-end; gap:12px;">
            <button
              @click="cancelDelete"
              :disabled="deleting"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:500; color:#374151; background:transparent; border:1px solid #e5e7eb; cursor:pointer; transition:background .15s;"
              @mouseenter="($event.target as HTMLElement).style.background='#f9fafb'"
              @mouseleave="($event.target as HTMLElement).style.background='transparent'"
            >
              Cancelar
            </button>
            <button
              @click="confirmDelete"
              :disabled="deleting"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:600; color:#fff; background:#ef4444; border:none; cursor:pointer; display:flex; align-items:center; gap:8px; transition:background .15s;"
              @mouseenter="($event.target as HTMLElement).style.background='#dc2626'"
              @mouseleave="($event.target as HTMLElement).style.background='#ef4444'"
            >
              <span v-if="deleting" class="material-symbols-outlined" style="font-size:18px; animation:spin 1s linear infinite;">progress_activity</span>
              <span v-else class="material-symbols-outlined" style="font-size:18px;">delete</span>
              {{ deleting ? 'Eliminando...' : 'Sí, eliminar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Modal de importar estudiante -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="showImportModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
        style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
        @click.self="cancelarImportar"
      >
        <div
          style="background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.25); width:100%; max-width:480px; padding:28px; box-sizing:border-box;"
        >
          <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
            <div style="flex-shrink:0; width:44px; height:44px; border-radius:50%; background:#e0e7ff; display:flex; align-items:center; justify-content:center;">
              <span class="material-symbols-outlined" style="color:#4f46e5; font-size:22px;">upload_file</span>
            </div>
            <h3 style="font-size:17px; font-weight:700; color:#111827; margin:0;">Importar estudiante</h3>
          </div>

          <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 20px 0;">
            Sube un archivo <code style="background:#f3f4f6; padding:2px 4px; border-radius:4px;">.openpiar</code> y escribe la contraseña de cifrado original para restaurar la historia escolar del estudiante.
          </p>

          <!-- File selector (Dropzone style) -->
          <div style="margin-bottom:16px;">
            <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:6px;">Archivo portable (.openpiar)</label>
            
            <div
              @click="triggerFileSelect"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleFileDrop"
              style="border: 2px dashed #d1d5db; border-radius: 12px; padding: 24px; text-align: center; cursor: pointer; transition: all 0.2s; position: relative;"
              :style="{
                background: isDragging ? '#f5f3ff' : (importFile ? '#f0fdf4' : '#fafafa'),
                borderColor: isDragging ? '#4f46e5' : (importFile ? '#22c55e' : '#d1d5db')
              }"
              @mouseenter="($event.currentTarget as HTMLElement).style.borderColor = importFile ? '#22c55e' : '#4f46e5'"
              @mouseleave="($event.currentTarget as HTMLElement).style.borderColor = isDragging ? '#4f46e5' : (importFile ? '#22c55e' : '#d1d5db')"
            >
              <!-- Hidden input -->
              <input
                ref="fileInputRef"
                type="file"
                accept=".openpiar"
                @change="handleFileChange"
                style="display: none;"
              />
              
              <!-- Content when no file -->
              <div v-if="!importFile" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;">
                <span class="material-symbols-outlined" style="font-size: 36px; color: #4f46e5;">cloud_upload</span>
                <span style="font-size: 14px; font-weight: 600; color: #111827;">Arrastra el archivo aquí o haz clic para buscarlo</span>
                <span style="font-size: 11px; color: #6b7280;">Solo archivos .openpiar encriptados</span>
              </div>
              
              <!-- Content when file selected -->
              <div v-else style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
                <span class="material-symbols-outlined" style="font-size: 36px; color: #22c55e;">check_circle</span>
                <div style="font-size: 14px; font-weight: 600; color: #111827; word-break: break-all; max-width: 100%;">
                  {{ importFile.name }}
                </div>
                <div style="font-size: 11px; color: #6b7280;">
                  Tamaño: {{ (importFile.size / 1024).toFixed(1) }} KB
                </div>
                <button
                  type="button"
                  @click.stop="clearImportFile"
                  style="margin-top: 8px; font-size: 12px; color: #ef4444; background: transparent; border: none; font-weight: 600; cursor: pointer; text-decoration: underline;"
                >
                  Cambiar archivo
                </button>
              </div>
            </div>
          </div>

          <!-- Password input -->
          <div style="margin-bottom:16px;">
            <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:6px;">Contraseña de cifrado</label>
            <input
              type="password"
              v-model="importPassword"
              placeholder="••••••"
              style="width:100%; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; box-sizing:border-box;"
            />
          </div>

          <!-- Optional Group selection -->
          <div style="margin-bottom:20px;">
            <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:6px;">Asignar a Grupo (Opcional)</label>
            <select
              v-model="importGrupoId"
              style="width:100%; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; background:#fff; box-sizing:border-box;"
            >
              <option :value="null">Ningún grupo (Sin grupo asignado)</option>
              <option v-for="g in grupos" :key="g.id" :value="g.id">
                {{ g.grado }} - {{ g.nombre }} ({{ g.sede?.nombre }})
              </option>
            </select>
          </div>

          <!-- Error -->
          <div
            v-if="importError"
            style="background:#fee2e2; color:#dc2626; border-radius:10px; padding:12px 16px; font-size:13px; margin-bottom:16px;"
          >
            {{ importError }}
          </div>

          <!-- Actions -->
          <div style="display:flex; justify-content:flex-end; gap:12px;">
            <button
              @click="cancelarImportar"
              :disabled="isImporting"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:500; color:#374151; background:transparent; border:1px solid #e5e7eb; cursor:pointer; transition:background .15s;"
              @mouseenter="($event.target as HTMLElement).style.background='#f9fafb'"
              @mouseleave="($event.target as HTMLElement).style.background='transparent'"
            >
              Cancelar
            </button>
            <button
              @click="ejecutarImportar"
              :disabled="isImporting || !importFile || importPassword.length < 6"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:600; color:#fff; background:#4f46e5; border:none; cursor:pointer; transition:opacity .15s; display:flex; align-items:center; gap:8px;"
              :style="{ opacity: (isImporting || !importFile || importPassword.length < 6) ? 0.6 : 1 }"
            >
              <span v-if="isImporting" class="material-symbols-outlined" style="font-size:18px; animation:spin 1s linear infinite;">progress_activity</span>
              <span>{{ isImporting ? 'Importando...' : 'Desempaquetar e Importar' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Success Toast -->
  <div v-if="successToast" class="fixed bottom-6 right-6 z-[9999] max-w-[28rem] animate-fade-in">
    <div class="bg-[#caead6] text-[#042014] p-4 pr-6 rounded-xl shadow-lg border border-[#afceba] flex items-center gap-3">
      <span class="material-symbols-outlined text-green-700 shrink-0">check_circle</span>
      <span class="font-semibold text-body-md">{{ successToast }}</span>
    </div>
  </div>
</template>

<style scoped>
.star-icon {
  font-variation-settings: 'FILL' 1;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.18s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active > div,
.modal-leave-active > div {
  transition: transform 0.18s ease, opacity 0.18s ease;
}
.modal-enter-from > div {
  transform: scale(0.95);
  opacity: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.25s ease-out forwards;
}
</style>
