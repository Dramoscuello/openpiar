<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// State management
const activeTab = ref('sedes') // 'sedes', 'docentes', 'asignaturas', 'grupos', 'carga'
const loading = ref(false)
const errorMsg = ref<string | null>(null)
const successMsg = ref<string | null>(null)

// Data arrays from API
const sedes = ref<any[]>([])
const docentes = ref<any[]>([])
const asignaturas = ref<any[]>([])
const grupos = ref<any[]>([])
const cargas = ref<any[]>([])

// Modals visibility
const showSedeModal = ref(false)
const showDocenteModal = ref(false)
const showAsignaturaModal = ref(false)
const showGrupoModal = ref(false)
const showCargaModal = ref(false)

// Form fields
const sedeForm = ref({ nombre: '', direccion: '', telefono: '' })
const docenteForm = ref({ email: '', password: '', nombre: '', apellido: '', rol: 'docente_aula', cargo: 'Docente', sede_ids: [] as string[] })
const asignaturaForm = ref({ nombre: '' })
const grupoForm = ref({ nombre: '', grado: '', sede_id: '', director_id: '' })
const cargaForm = ref({ docente_id: '', asignatura_id: '', grupo_id: '' })

// Load all management data
const loadData = async () => {
  if (!authStore.token) return
  loading.value = true
  errorMsg.value = null
  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    
    // Fetch all in parallel
    const [sedesRes, docentesRes, asignaturasRes, gruposRes, cargasRes] = await Promise.all([
      fetch('/api/v1/gestion/sedes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/docentes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/asignaturas', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/grupos', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/carga-academica', { headers }).then(r => r.ok ? r.json() : [])
    ])

    sedes.value = sedesRes
    docentes.value = docentesRes
    asignaturas.value = asignaturasRes
    grupos.value = gruposRes
    cargas.value = cargasRes
  } catch (err: any) {
    errorMsg.value = 'Error al cargar los datos escolares. Inténtalo de nuevo.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Security guard: Only directivos can access
  if (authStore.user?.rol !== 'directivo') {
    router.push('/dashboard')
    return
  }
  await loadData()
})

// Helper for API responses
const handleResponse = async (res: Response, defaultError: string) => {
  let data
  try {
    data = await res.json()
  } catch (e) {
    if (!res.ok) {
      throw new Error(`Error del servidor (${res.status}): No se pudo procesar la solicitud.`)
    }
    throw new Error('La respuesta del servidor no tiene un formato válido.')
  }
  if (!res.ok) {
    throw new Error(data.detail || defaultError)
  }
  return data
}

// Submissions
const submitSede = async () => {
  if (!sedeForm.value.nombre) {
    errorMsg.value = 'El nombre de la sede es obligatorio.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch('/api/v1/gestion/sedes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(sedeForm.value)
    })
    const data = await handleResponse(res, 'Error al crear sede')
    
    sedes.value.push(data)
    showSedeModal.value = false
    sedeForm.value = { nombre: '', direccion: '', telefono: '' }
    successMsg.value = 'Sede creada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitDocente = async () => {
  const f = docenteForm.value
  if (!f.email || !f.password || !f.nombre || !f.apellido) {
    errorMsg.value = 'Completa todos los campos obligatorios.'
    return
  }
  if (f.sede_ids.length === 0) {
    errorMsg.value = 'Debes asignar el docente a al menos una sede.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch('/api/v1/gestion/docentes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(f)
    })
    const data = await handleResponse(res, 'Error al registrar docente')
    
    docentes.value.push(data)
    showDocenteModal.value = false
    docenteForm.value = { email: '', password: '', nombre: '', apellido: '', rol: 'docente_aula', cargo: 'Docente', sede_ids: [] }
    successMsg.value = 'Docente registrado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitAsignatura = async () => {
  if (!asignaturaForm.value.nombre) {
    errorMsg.value = 'El nombre de la asignatura es obligatorio.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch('/api/v1/gestion/asignaturas', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(asignaturaForm.value)
    })
    const data = await handleResponse(res, 'Error al registrar asignatura')
    
    asignaturas.value.push(data)
    showAsignaturaModal.value = false
    asignaturaForm.value = { nombre: '' }
    successMsg.value = 'Asignatura registrada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitGrupo = async () => {
  const f = grupoForm.value
  if (!f.nombre || !f.grado || !f.sede_id) {
    errorMsg.value = 'Completa los campos obligatorios del grupo.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const body: any = {
      nombre: f.nombre,
      grado: f.grado,
      sede_id: f.sede_id,
      director_id: f.director_id || null
    }
    const res = await fetch('/api/v1/gestion/grupos', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(body)
    })
    const data = await handleResponse(res, 'Error al registrar grupo')
    
    grupos.value.push(data)
    showGrupoModal.value = false
    grupoForm.value = { nombre: '', grado: '', sede_id: '', director_id: '' }
    successMsg.value = 'Grupo / Grado registrado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitCarga = async () => {
  const f = cargaForm.value
  if (!f.docente_id || !f.asignatura_id || !f.grupo_id) {
    errorMsg.value = 'Completa todos los campos obligatorios de la carga.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch('/api/v1/gestion/carga-academica', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(f)
    })
    const data = await handleResponse(res, 'Error al asignar carga')
    
    cargas.value.push(data)
    showCargaModal.value = false
    cargaForm.value = { docente_id: '', asignatura_id: '', grupo_id: '' }
    successMsg.value = 'Carga académica asignada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deleteCarga = async (id: string) => {
  if (!confirm('¿Estás seguro de eliminar esta asignación de carga académica?')) return
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/carga-academica/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar la carga'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    cargas.value = cargas.value.filter(c => c.id !== id)
    successMsg.value = 'Carga académica removida exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
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
          <span class="material-symbols-outlined text-primary text-[28px]">domain</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">Gestión Escolar (Administración)</h2>
        </div>
      </header>

      <!-- Content Grid -->
      <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
        
        <!-- Alerts -->
        <div v-if="errorMsg" class="p-sm bg-error-container text-on-error-container rounded-xl text-body-md border border-error/20 flex gap-xs items-start">
          <span class="material-symbols-outlined text-error">error</span>
          <span>{{ errorMsg }}</span>
        </div>
        <div v-if="successMsg" class="p-sm bg-tertiary-container text-on-tertiary-container rounded-xl text-body-md border border-tertiary/20 flex gap-xs items-start">
          <span class="material-symbols-outlined text-tertiary">check_circle</span>
          <span>{{ successMsg }}</span>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex border-b border-outline-variant/30 gap-sm select-none">
          <button
            @click="activeTab = 'sedes'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'sedes' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Sedes
          </button>
          <button
            @click="activeTab = 'docentes'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'docentes' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Docentes
          </button>
          <button
            @click="activeTab = 'asignaturas'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'asignaturas' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Asignaturas
          </button>
          <button
            @click="activeTab = 'grupos'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'grupos' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Grados y Grupos
          </button>
          <button
            @click="activeTab = 'carga'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'carga' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Carga Académica
          </button>
        </div>

        <!-- 1. TAB: SEDES -->
        <div v-if="activeTab === 'sedes'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Sedes Educativas</h3>
            <button
              @click="showSedeModal = true"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">add_home</span>
              Nueva Sede
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre</th>
                  <th class="py-4 px-md">Dirección</th>
                  <th class="py-4 px-md">Teléfono</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="s in sedes" :key="s.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ s.nombre }}</td>
                  <td class="py-4 px-md">{{ s.direccion || '-' }}</td>
                  <td class="py-4 px-md">{{ s.telefono || '-' }}</td>
                </tr>
                <tr v-if="sedes.length === 0">
                  <td colspan="3" class="py-8 text-center text-outline">No hay sedes registradas. Crea la primera sede.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 2. TAB: DOCENTES -->
        <div v-if="activeTab === 'docentes'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Docentes Registrados</h3>
            <button
              @click="showDocenteModal = true"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">person_add</span>
              Registrar Docente
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre</th>
                  <th class="py-4 px-md">Email</th>
                  <th class="py-4 px-md">Rol / Cargo</th>
                  <th class="py-4 px-md">Sedes Asignadas</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="d in docentes" :key="d.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ d.apellido }}, {{ d.nombre }}</td>
                  <td class="py-4 px-md font-mono text-[13px]">{{ d.email }}</td>
                  <td class="py-4 px-md">
                    <span class="bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded text-label-sm font-bold mr-2 uppercase">
                      {{ d.rol.replace('docente_', '') }}
                    </span>
                    <span class="text-outline text-[13px]">{{ d.cargo }}</span>
                  </td>
                  <td class="py-4 px-md">
                    <div class="flex flex-wrap gap-1">
                      <span v-for="s in d.sedes" :key="s.id" class="bg-primary/10 text-primary px-2 py-0.5 rounded text-label-sm font-medium">
                        {{ s.nombre }}
                      </span>
                      <span v-if="d.sedes.length === 0" class="text-outline text-[13px]">-</span>
                    </div>
                  </td>
                </tr>
                <tr v-if="docentes.length === 0">
                  <td colspan="4" class="py-8 text-center text-outline">No hay docentes registrados.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 3. TAB: ASIGNATURAS -->
        <div v-if="activeTab === 'asignaturas'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Asignaturas / Materias</h3>
            <button
              @click="showAsignaturaModal = true"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">book</span>
              Nueva Asignatura
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre de la Asignatura</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="a in asignaturas" :key="a.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ a.nombre }}</td>
                </tr>
                <tr v-if="asignaturas.length === 0">
                  <td class="py-8 text-center text-outline">No hay asignaturas registradas.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 4. TAB: GRUPOS -->
        <div v-if="activeTab === 'grupos'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Grados y Grupos</h3>
            <button
              @click="showGrupoModal = true"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">groups</span>
              Nuevo Grupo / Curso
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Grado</th>
                  <th class="py-4 px-md">Nombre Grupo</th>
                  <th class="py-4 px-md">Sede</th>
                  <th class="py-4 px-md">Director de Grupo</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="g in grupos" :key="g.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ g.grado }}</td>
                  <td class="py-4 px-md">{{ g.nombre }}</td>
                  <td class="py-4 px-md">{{ g.sede.nombre }}</td>
                  <td class="py-4 px-md">
                    <span v-if="g.director" class="font-semibold text-primary">
                      {{ g.director.apellido }}, {{ g.director.nombre }}
                    </span>
                    <span v-else class="text-outline text-[13px]">Sin asignar director</span>
                  </td>
                </tr>
                <tr v-if="grupos.length === 0">
                  <td colspan="4" class="py-8 text-center text-outline">No hay grupos registrados.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 5. TAB: CARGA ACADÉMICA -->
        <div v-if="activeTab === 'carga'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Carga Académica (Docentes - Materia - Grado)</h3>
            <button
              @click="showCargaModal = true"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">assignment_turned_in</span>
              Asignar Carga
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Docente</th>
                  <th class="py-4 px-md">Asignatura</th>
                  <th class="py-4 px-md">Grado / Grupo</th>
                  <th class="py-4 px-md">Sede</th>
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="c in cargas" :key="c.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ c.docente_nombre }}</td>
                  <td class="py-4 px-md font-semibold text-primary">{{ c.asignatura.nombre }}</td>
                  <td class="py-4 px-md">{{ c.grupo.grado }} - {{ c.grupo.nombre }}</td>
                  <td class="py-4 px-md text-outline">{{ c.grupo.sede.nombre }}</td>
                  <td class="py-4 px-md text-right">
                    <button
                      @click="deleteCarga(c.id)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar asignación de carga"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="cargas.length === 0">
                  <td colspan="5" class="py-8 text-center text-outline">No hay carga académica asignada.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </main>

    <!-- MODAL: SEDE -->
    <div v-if="showSedeModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">add_home</span>
          Nueva Sede Educativa
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Nombre de la Sede *</label>
            <input v-model="sedeForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: Sede Principal" />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Dirección</label>
            <input v-model="sedeForm.direccion" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: Calle 45 # 12-34" />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Teléfono</label>
            <input v-model="sedeForm.telefono" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: 3001234567" />
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showSedeModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitSede" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Guardar Sede</button>
        </div>
      </div>
    </div>

    <!-- MODAL: DOCENTE -->
    <div v-if="showDocenteModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[512px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md overflow-y-auto max-h-[90vh]">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">person_add</span>
          Registrar Nuevo Docente
        </h3>
        <div class="space-y-sm">
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Nombres *</label>
              <input v-model="docenteForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Apellidos *</label>
              <input v-model="docenteForm.apellido" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Email *</label>
            <input v-model="docenteForm.email" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="email" placeholder="docente@gmail.com" />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Contraseña de acceso *</label>
            <input v-model="docenteForm.password" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="password" />
          </div>
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Rol de inclusión *</label>
              <select v-model="docenteForm.rol" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
                <option value="docente_aula">Docente de Aula</option>
                <option value="docente_apoyo">Docente de Apoyo</option>
                <option value="orientador">Docente Orientador</option>
              </select>
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Cargo Escolar</label>
              <input v-model="docenteForm.cargo" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant font-bold">Asignar Sedes *</label>
            <div class="grid grid-cols-2 gap-xs bg-surface p-sm border border-outline-variant rounded-input">
              <div v-for="s in sedes" :key="s.id" class="flex items-center gap-xs">
                <input :id="'sede-check-' + s.id" v-model="docenteForm.sede_ids" :value="s.id" type="checkbox" class="w-4 h-4" />
                <label :for="'sede-check-' + s.id" class="font-label-md text-[13px] text-on-surface select-none cursor-pointer">{{ s.nombre }}</label>
              </div>
              <p v-if="sedes.length === 0" class="text-outline text-label-sm col-span-2">Crea una sede antes de agregar un docente.</p>
            </div>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showDocenteModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitDocente" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Registrar Docente</button>
        </div>
      </div>
    </div>

    <!-- MODAL: ASIGNATURA -->
    <div v-if="showAsignaturaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">book</span>
          Nueva Asignatura / Materia
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Nombre de la Asignatura *</label>
            <input v-model="asignaturaForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: Matemáticas" />
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showAsignaturaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitAsignatura" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Guardar Asignatura</button>
        </div>
      </div>
    </div>

    <!-- MODAL: GRUPO -->
    <div v-if="showGrupoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">groups</span>
          Nuevo Grupo / Curso
        </h3>
        <div class="space-y-sm">
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Grado *</label>
              <input v-model="grupoForm.grado" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: Primero, Transición" />
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Grupo *</label>
              <input v-model="grupoForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: A, B, 101" />
            </div>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Sede Escolar *</label>
            <select v-model="grupoForm.sede_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Selecciona sede...</option>
              <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Director de Grupo (Opcional)</label>
            <select v-model="grupoForm.director_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Sin asignar director</option>
              <option v-for="d in docentes" :key="d.id" :value="d.id">{{ d.apellido }}, {{ d.nombre }}</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showGrupoModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitGrupo" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Guardar Grupo</button>
        </div>
      </div>
    </div>

    <!-- MODAL: CARGA ACADÉMICA -->
    <div v-if="showCargaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">assignment_turned_in</span>
          Asignar Carga Académica
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar Docente *</label>
            <select v-model="cargaForm.docente_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Selecciona docente...</option>
              <option v-for="d in docentes" :key="d.id" :value="d.id">{{ d.apellido }}, {{ d.nombre }} ({{ d.rol.replace('docente_','') }})</option>
            </select>
          </div>

          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar Asignatura *</label>
            <select v-model="cargaForm.asignatura_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Selecciona asignatura...</option>
              <option v-for="a in asignaturas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
            </select>
          </div>

          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar Grupo / Grado *</label>
            <select v-model="cargaForm.grupo_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Selecciona grado y grupo...</option>
              <option v-for="g in grupos" :key="g.id" :value="g.id">{{ g.grado }} - {{ g.nombre }} ({{ g.sede.nombre }})</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showCargaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitCarga" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Asignar Carga</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.star-icon {
  font-variation-settings: 'FILL' 1;
}
input[type="checkbox"] {
  accent-color: var(--color-primary);
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
