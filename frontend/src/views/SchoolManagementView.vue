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
const periodos = ref<any[]>([])

// Modals visibility
const showSedeModal = ref(false)
const showDocenteModal = ref(false)
const showAsignaturaModal = ref(false)
const showGrupoModal = ref(false)
const showCargaModal = ref(false)
const showPeriodoModal = ref(false)

// Form fields
const sedeForm = ref({ nombre: '', direccion: '', telefono: '' })
const docenteForm = ref({ email: '', password: '', nombre: '', apellido: '', rol: 'docente_aula', cargo: 'Docente', sede_ids: [] as string[] })
const asignaturaForm = ref({ nombre: '' })
const grupoForm = ref({ nombre: '', grado: '', sede_id: '', director_id: '' })
const cargaForm = ref({ docente_id: '', asignatura_id: '', grupo_id: '' })
const periodoForm = ref({ nombre: '', fecha_inicio: '', fecha_fin: '' })

// Load all management data
const loadData = async () => {
  if (!authStore.token) return
  loading.value = true
  errorMsg.value = null
  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    
    // Fetch all in parallel
    const [sedesRes, docentesRes, asignaturasRes, gruposRes, cargasRes, periodosRes] = await Promise.all([
      fetch('/api/v1/gestion/sedes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/docentes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/asignaturas', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/grupos', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/carga-academica', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/periodos', { headers }).then(r => r.ok ? r.json() : [])
    ])

    sedes.value = sedesRes
    docentes.value = docentesRes
    asignaturas.value = asignaturasRes
    grupos.value = gruposRes
    cargas.value = cargasRes
    periodos.value = periodosRes
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

// Submissions & Editing State
const editingId = ref<string | null>(null)
const isEditing = computed(() => editingId.value !== null)

const isCreatingNewGrado = ref(false)
const existingGrados = computed(() => {
  const list = grupos.value.map(g => g.grado)
  return [...new Set(list)].filter(Boolean).sort()
})

const openNewSede = () => {
  editingId.value = null
  sedeForm.value = { nombre: '', direccion: '', telefono: '' }
  showSedeModal.value = true
}

const openEditSede = (sede: any) => {
  editingId.value = sede.id
  sedeForm.value = {
    nombre: sede.nombre,
    direccion: sede.direccion || '',
    telefono: sede.telefono || ''
  }
  showSedeModal.value = true
}

const openNewDocente = () => {
  editingId.value = null
  docenteForm.value = {
    email: '',
    password: '',
    nombre: '',
    apellido: '',
    rol: 'docente_aula',
    cargo: 'Docente',
    sede_ids: []
  }
  showDocenteModal.value = true
}

const openEditDocente = (docente: any) => {
  editingId.value = docente.id
  docenteForm.value = {
    email: docente.email,
    password: '', // Leave blank by default when editing
    nombre: docente.nombre,
    apellido: docente.apellido,
    rol: docente.rol,
    cargo: docente.cargo || 'Docente',
    sede_ids: docente.sedes.map((s: any) => s.id)
  }
  showDocenteModal.value = true
}

const openNewAsignatura = () => {
  editingId.value = null
  asignaturaForm.value = { nombre: '' }
  showAsignaturaModal.value = true
}

const openEditAsignatura = (asignatura: any) => {
  editingId.value = asignatura.id
  asignaturaForm.value = { nombre: asignatura.nombre }
  showAsignaturaModal.value = true
}

const openNewGrupo = () => {
  editingId.value = null
  grupoForm.value = { nombre: '', grado: '', sede_id: '', director_id: '' }
  isCreatingNewGrado.value = existingGrados.value.length === 0
  showGrupoModal.value = true
}

const openEditGrupo = (grupo: any) => {
  editingId.value = grupo.id
  grupoForm.value = {
    nombre: grupo.nombre,
    grado: grupo.grado,
    sede_id: grupo.sede.id,
    director_id: grupo.director ? grupo.director.id : ''
  }
  isCreatingNewGrado.value = !existingGrados.value.includes(grupo.grado)
  showGrupoModal.value = true
}

const onGradoSelectChange = (e: any) => {
  if (e.target.value === '__NEW__') {
    isCreatingNewGrado.value = true
    grupoForm.value.grado = ''
  }
}

const openNewCarga = () => {
  editingId.value = null
  cargaForm.value = { docente_id: '', asignatura_id: '', grupo_id: '' }
  showCargaModal.value = true
}

const openEditCarga = (carga: any) => {
  editingId.value = carga.id
  cargaForm.value = {
    docente_id: carga.docente_id,
    asignatura_id: carga.asignatura.id,
    grupo_id: carga.grupo.id
  }
  showCargaModal.value = true
}

const openNewPeriodo = () => {
  editingId.value = null
  periodoForm.value = { nombre: '', fecha_inicio: '', fecha_fin: '' }
  showPeriodoModal.value = true
}

const openEditPeriodo = (periodo: any) => {
  editingId.value = periodo.id
  periodoForm.value = {
    nombre: periodo.nombre,
    fecha_inicio: periodo.fecha_inicio,
    fecha_fin: periodo.fecha_fin
  }
  showPeriodoModal.value = true
}

const submitSede = async () => {
  if (!sedeForm.value.nombre) {
    errorMsg.value = 'El nombre de la sede es obligatorio.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/sedes/${editingId.value}` : '/api/v1/gestion/sedes'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(sedeForm.value)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar sede' : 'Error al crear sede')
    
    if (isEdit) {
      const idx = sedes.value.findIndex(s => s.id === editingId.value)
      if (idx !== -1) sedes.value[idx] = data
    } else {
      sedes.value.push(data)
    }
    showSedeModal.value = false
    sedeForm.value = { nombre: '', direccion: '', telefono: '' }
    successMsg.value = isEdit ? 'Sede actualizada exitosamente.' : 'Sede creada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitDocente = async () => {
  const f = docenteForm.value
  if (!f.email || (!editingId.value && !f.password) || !f.nombre || !f.apellido) {
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
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/docentes/${editingId.value}` : '/api/v1/gestion/docentes'
    const method = isEdit ? 'PUT' : 'POST'
    
    const body: any = { ...f }
    if (isEdit && !body.password) {
      delete body.password
    }
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(body)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar docente' : 'Error al registrar docente')
    
    if (isEdit) {
      const idx = docentes.value.findIndex(d => d.id === editingId.value)
      if (idx !== -1) docentes.value[idx] = data
      
      // Sync names in cargas
      cargas.value.forEach(c => {
        if (c.docente_id === editingId.value) {
          c.docente_nombre = `${data.nombre} ${data.apellido}`
        }
      })
      // Sync director in groups
      grupos.value.forEach(g => {
        if (g.director && g.director.id === editingId.value) {
          g.director.nombre = data.nombre
          g.director.apellido = data.apellido
          g.director.email = data.email
        }
      })
    } else {
      docentes.value.push(data)
    }
    showDocenteModal.value = false
    docenteForm.value = { email: '', password: '', nombre: '', apellido: '', rol: 'docente_aula', cargo: 'Docente', sede_ids: [] }
    successMsg.value = isEdit ? 'Docente actualizado exitosamente.' : 'Docente registrado exitosamente.'
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
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/asignaturas/${editingId.value}` : '/api/v1/gestion/asignaturas'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(asignaturaForm.value)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar asignatura' : 'Error al registrar asignatura')
    
    if (isEdit) {
      const idx = asignaturas.value.findIndex(a => a.id === editingId.value)
      if (idx !== -1) asignaturas.value[idx] = data
      
      // Sync names in cargas
      cargas.value.forEach(c => {
        if (c.asignatura.id === editingId.value) {
          c.asignatura.nombre = data.nombre
        }
      })
    } else {
      asignaturas.value.push(data)
    }
    showAsignaturaModal.value = false
    asignaturaForm.value = { nombre: '' }
    successMsg.value = isEdit ? 'Asignatura actualizada exitosamente.' : 'Asignatura registrada exitosamente.'
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
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/grupos/${editingId.value}` : '/api/v1/gestion/grupos'
    const method = isEdit ? 'PUT' : 'POST'
    
    const body: any = {
      nombre: f.nombre,
      grado: f.grado,
      sede_id: f.sede_id,
      director_id: f.director_id || null
    }
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(body)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar grupo' : 'Error al registrar grupo')
    
    if (isEdit) {
      const idx = grupos.value.findIndex(g => g.id === editingId.value)
      if (idx !== -1) grupos.value[idx] = data
      
      // Sync in cargas
      cargas.value.forEach(c => {
        if (c.grupo.id === editingId.value) {
          c.grupo.nombre = data.nombre
          c.grupo.grado = data.grado
          c.grupo.sede = data.sede
          c.grupo.director = data.director
        }
      })
    } else {
      grupos.value.push(data)
    }
    showGrupoModal.value = false
    grupoForm.value = { nombre: '', grado: '', sede_id: '', director_id: '' }
    successMsg.value = isEdit ? 'Grupo / Grado actualizado exitosamente.' : 'Grupo / Grado registrado exitosamente.'
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
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/carga-academica/${editingId.value}` : '/api/v1/gestion/carga-academica'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(f)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar carga' : 'Error al asignar carga')
    
    if (isEdit) {
      const idx = cargas.value.findIndex(c => c.id === editingId.value)
      if (idx !== -1) cargas.value[idx] = data
    } else {
      cargas.value.push(data)
    }
    showCargaModal.value = false
    cargaForm.value = { docente_id: '', asignatura_id: '', grupo_id: '' }
    successMsg.value = isEdit ? 'Carga académica actualizada exitosamente.' : 'Carga académica asignada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const confirmDeleteEntity = ref<{
  id: string;
  name: string;
  type: 'sede' | 'docente' | 'asignatura' | 'grupo' | 'carga';
  title: string;
  warningText: string;
} | null>(null)

const deletingEntity = ref(false)

const promptDelete = (
  id: string,
  name: string,
  type: 'sede' | 'docente' | 'asignatura' | 'grupo' | 'carga',
  title: string,
  warningText: string
) => {
  confirmDeleteEntity.value = { id, name, type, title, warningText }
}

const cancelDeleteEntity = () => {
  confirmDeleteEntity.value = null
  errorMsg.value = null
}

const confirmDeleteAction = async () => {
  if (!confirmDeleteEntity.value) return
  const { id, name, type } = confirmDeleteEntity.value
  deletingEntity.value = true
  
  if (type === 'sede') await deleteSede(id, name, true)
  else if (type === 'docente') await deleteDocente(id, name, true)
  else if (type === 'asignatura') await deleteAsignatura(id, name, true)
  else if (type === 'grupo') await deleteGrupo(id, name, true)
  else if (type === 'carga') await deleteCarga(id, true)
  else if (type === 'periodo') await deletePeriodo(id, name, true)
  
  deletingEntity.value = false
  if (!errorMsg.value) {
    confirmDeleteEntity.value = null
  }
}

const deleteCarga = async (id: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, '', 'carga', 'Eliminar asignación de carga', 'Se eliminará esta asignación de carga académica de manera permanente.')
    return
  }
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

const submitPeriodo = async () => {
  if (!periodoForm.value.nombre || !periodoForm.value.fecha_inicio || !periodoForm.value.fecha_fin) {
    errorMsg.value = 'Todos los campos del periodo son obligatorios.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/periodos/${editingId.value}` : '/api/v1/gestion/periodos'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(periodoForm.value)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar periodo' : 'Error al crear periodo')
    
    if (isEdit) {
      const idx = periodos.value.findIndex(p => p.id === editingId.value)
      if (idx !== -1) periodos.value[idx] = data
    } else {
      periodos.value.unshift(data) // Ponerlo primero ya que se listan por fecha
    }
    showPeriodoModal.value = false
    periodoForm.value = { nombre: '', fecha_inicio: '', fecha_fin: '' }
    successMsg.value = isEdit ? 'Periodo actualizado exitosamente.' : 'Periodo creado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const togglePeriodoActivo = async (periodo: any) => {
  if (periodo.activo) return // No hacer nada si ya está activo (siempre debe haber uno)
  
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/periodos/${periodo.id}/toggle`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    const data = await handleResponse(res, 'Error al activar el periodo')
    
    // Desactivar todos localmente
    periodos.value.forEach(p => p.activo = false)
    
    // Actualizar el toggled
    const idx = periodos.value.findIndex(p => p.id === periodo.id)
    if (idx !== -1) periodos.value[idx] = data
    
    successMsg.value = 'Periodo activado correctamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deletePeriodo = async (id: string, nombre: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombre, 'periodo' as any, 'Eliminar Periodo Académico', 'Se eliminará este periodo y toda la configuración asociada al mismo.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/periodos/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar el periodo'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    periodos.value = periodos.value.filter(p => p.id !== id)
    successMsg.value = 'Periodo eliminado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deleteSede = async (id: string, nombre: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombre, 'sede', 'Eliminar sede', 'Se eliminarán en cascada todos los grados, grupos y cargas académicas vinculados a esta sede.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/sedes/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar la sede'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    sedes.value = sedes.value.filter(s => s.id !== id)
    const deletedGroupIds = grupos.value.filter(g => g.sede.id === id).map(g => g.id)
    grupos.value = grupos.value.filter(g => g.sede.id !== id)
    cargas.value = cargas.value.filter(c => !deletedGroupIds.includes(c.grupo.id))
    docentes.value.forEach(d => {
      d.sedes = d.sedes.filter((s: any) => s.id !== id)
    })
    successMsg.value = 'Sede eliminada exitosamente junto con sus datos relacionados.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deleteDocente = async (id: string, nombre: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombre, 'docente', 'Eliminar docente', 'Se eliminará su acceso y todas las asignaciones de carga académica que tenga asignadas. Además, si es director de algún grupo, dicho grupo quedará sin director.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/docentes/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar al docente'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    docentes.value = docentes.value.filter(d => d.id !== id)
    cargas.value = cargas.value.filter(c => c.docente_id !== id)
    grupos.value.forEach(g => {
      if (g.director && g.director.id === id) {
        g.director = null
      }
    })
    successMsg.value = 'Docente eliminado exitosamente junto con sus datos relacionados.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deleteAsignatura = async (id: string, nombre: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombre, 'asignatura', 'Eliminar asignatura', 'Se eliminarán todas las asignaciones de carga académica relacionadas con esta asignatura.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/asignaturas/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar la asignatura'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    asignaturas.value = asignaturas.value.filter(a => a.id !== id)
    cargas.value = cargas.value.filter(c => c.asignatura.id !== id)
    successMsg.value = 'Asignatura eliminada exitosamente junto con sus datos relacionados.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const deleteGrupo = async (id: string, nombreCompleto: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombreCompleto, 'grupo', 'Eliminar grupo/grado', 'Se eliminarán todas las cargas académicas vinculadas. Los estudiantes asignados a este grupo quedarán sin grupo (no serán eliminados).')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/grupos/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar el grupo'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    grupos.value = grupos.value.filter(g => g.id !== id)
    cargas.value = cargas.value.filter(c => c.grupo.id !== id)
    successMsg.value = 'Grupo / Grado eliminado exitosamente junto con sus datos relacionados.'
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
          <button
            @click="activeTab = 'periodos'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'periodos' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Periodos Académicos
          </button>
        </div>

        <!-- 1. TAB: SEDES -->
        <div v-if="activeTab === 'sedes'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Sedes Educativas</h3>
            <button
              @click="openNewSede()"
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
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="s in sedes" :key="s.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ s.nombre }}</td>
                  <td class="py-4 px-md">{{ s.direccion || '-' }}</td>
                  <td class="py-4 px-md">{{ s.telefono || '-' }}</td>
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditSede(s)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Sede"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deleteSede(s.id, s.nombre)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar Sede"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="sedes.length === 0">
                  <td colspan="4" class="py-8 text-center text-outline">No hay sedes registradas. Crea la primera sede.</td>
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
              @click="openNewDocente()"
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
                  <th class="py-4 px-md text-right">Acciones</th>
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
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditDocente(d)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Docente"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deleteDocente(d.id, `${d.nombre} ${d.apellido}`)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar Docente"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="docentes.length === 0">
                  <td colspan="5" class="py-8 text-center text-outline">No hay docentes registrados.</td>
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
              @click="openNewAsignatura()"
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
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="a in asignaturas" :key="a.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ a.nombre }}</td>
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditAsignatura(a)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Asignatura"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deleteAsignatura(a.id, a.nombre)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar Asignatura"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="asignaturas.length === 0">
                  <td colspan="2" class="py-8 text-center text-outline">No hay asignaturas registradas.</td>
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
              @click="openNewGrupo()"
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
                  <th class="py-4 px-md text-right">Acciones</th>
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
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditGrupo(g)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Grupo"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deleteGrupo(g.id, `${g.grado} - ${g.nombre}`)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar Grupo"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="grupos.length === 0">
                  <td colspan="5" class="py-8 text-center text-outline">No hay grupos registrados.</td>
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
              @click="openNewCarga()"
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
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditCarga(c)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Carga Académica"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
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

        <!-- Tab: Periodos Académicos -->
        <div v-if="activeTab === 'periodos'" class="animate-fade-in">
          <div class="flex justify-between items-center mb-md">
            <div>
              <h3 class="text-title-lg font-bold text-on-surface">Periodos Académicos</h3>
              <p class="text-body-md text-on-surface-variant">
                Gestiona los periodos escolares. Solo puede haber un periodo activo a la vez.
              </p>
            </div>
            <button
              @click="openNewPeriodo"
              class="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-xl font-label-md hover:bg-primary/90 transition-all shadow-sm cursor-pointer"
            >
              <span class="material-symbols-outlined text-[20px]">add</span>
              Nuevo Periodo
            </button>
          </div>

          <div v-if="loading" class="py-10 text-center text-outline">
            Cargando periodos...
          </div>
          <div v-else-if="periodos.length === 0" class="py-10 text-center bg-surface-container-low rounded-2xl border border-outline-variant/30 text-on-surface-variant">
            No hay periodos registrados.
          </div>
          <div v-else class="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 overflow-hidden">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-surface-container-low text-label-md text-on-surface-variant border-b border-outline-variant/30">
                  <th class="px-md py-sm font-semibold">Nombre del Periodo</th>
                  <th class="px-md py-sm font-semibold">Fecha de Inicio</th>
                  <th class="px-md py-sm font-semibold">Fecha Fin</th>
                  <th class="px-md py-sm font-semibold text-center">Estado (Activo)</th>
                  <th class="px-md py-sm font-semibold text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="periodo in periodos"
                  :key="periodo.id"
                  class="border-b border-outline-variant/20 hover:bg-surface-container-low/50 transition-colors"
                >
                  <td class="px-md py-sm text-body-md font-medium text-on-surface">
                    {{ periodo.nombre }}
                  </td>
                  <td class="px-md py-sm text-body-md text-on-surface-variant">
                    {{ periodo.fecha_inicio }}
                  </td>
                  <td class="px-md py-sm text-body-md text-on-surface-variant">
                    {{ periodo.fecha_fin }}
                  </td>
                  <td class="px-md py-sm text-center">
                    <button 
                      @click="togglePeriodoActivo(periodo)"
                      class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer"
                      :class="periodo.activo ? 'bg-primary' : 'bg-outline-variant'"
                      title="Activar periodo (desactiva los demás)"
                    >
                      <span
                        class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                        :class="periodo.activo ? 'translate-x-6' : 'translate-x-1'"
                      />
                    </button>
                    <div class="text-label-sm mt-1" :class="periodo.activo ? 'text-primary font-bold' : 'text-outline'">
                      {{ periodo.activo ? 'Activo' : 'Inactivo' }}
                    </div>
                  </td>
                  <td class="px-md py-sm text-right space-x-2">
                    <button
                      @click="openEditPeriodo(periodo)"
                      class="text-primary hover:text-primary/80 transition-colors cursor-pointer"
                      title="Editar Periodo"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deletePeriodo(periodo.id, periodo.nombre)"
                      class="text-error hover:text-error/80 transition-colors cursor-pointer"
                      title="Eliminar Periodo"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

  <!-- Modal Periodo Académico -->
  <div v-if="showPeriodoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" @click.self="showPeriodoModal = false">
    <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md animate-scale-up">
      <div class="flex justify-between items-center">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'add_circle' }}</span>
          {{ isEditing ? 'Editar Periodo Académico' : 'Nuevo Periodo Académico' }}
        </h3>
        <button @click="showPeriodoModal = false" class="text-on-surface-variant hover:text-error transition-colors cursor-pointer">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="space-y-sm">
        <div class="space-y-xs">
          <label class="font-label-md text-label-md text-on-surface-variant">Nombre del Periodo *</label>
          <input
            v-model="periodoForm.nombre"
            type="text"
            class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            placeholder="Ej: Primer Semestre 2026"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Fecha de Inicio *</label>
            <input
              v-model="periodoForm.fecha_inicio"
              type="date"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Fecha Fin *</label>
            <input
              v-model="periodoForm.fecha_fin"
              type="date"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            />
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-3 pt-4">
        <button
          @click="showPeriodoModal = false"
          class="px-5 py-2.5 text-label-lg font-bold text-on-surface-variant hover:bg-surface-container-highest rounded-full transition-colors cursor-pointer"
        >
          Cancelar
        </button>
        <button
          @click="submitPeriodo"
          class="px-5 py-2.5 bg-primary text-on-primary rounded-full font-bold text-label-lg hover:bg-primary/90 transition-all cursor-pointer"
        >
          Guardar Periodo
        </button>
      </div>
    </div>
  </div>
    </main>

    <!-- MODAL: SEDE -->
    <div v-if="showSedeModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'add_home' }}</span>
          {{ isEditing ? 'Editar Sede Educativa' : 'Nueva Sede Educativa' }}
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
          <button @click="submitSede" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar Sede' : 'Guardar Sede' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: DOCENTE -->
    <div v-if="showDocenteModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[512px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md overflow-y-auto max-h-[90vh]">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'manage_accounts' : 'person_add' }}</span>
          {{ isEditing ? 'Editar Docente' : 'Registrar Nuevo Docente' }}
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
            <label class="font-label-md text-label-md text-on-surface-variant">{{ isEditing ? 'Nueva contraseña (dejar en blanco para conservar la actual)' : 'Contraseña de acceso *' }}</label>
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
          <button @click="submitDocente" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar Docente' : 'Registrar Docente' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: ASIGNATURA -->
    <div v-if="showAsignaturaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_note' : 'book' }}</span>
          {{ isEditing ? 'Editar Asignatura / Materia' : 'Nueva Asignatura / Materia' }}
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Nombre de la Asignatura *</label>
            <input v-model="asignaturaForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: Matemáticas" />
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showAsignaturaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitAsignatura" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar Asignatura' : 'Guardar Asignatura' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: GRUPO -->
    <div v-if="showGrupoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'groups' }}</span>
          {{ isEditing ? 'Editar Grupo / Curso' : 'Nuevo Grupo / Curso' }}
        </h3>
        <div class="space-y-sm">
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs flex flex-col">
              <div class="flex justify-between items-center">
                <label class="font-label-md text-label-md text-on-surface-variant">Grado *</label>
                <button
                  v-if="isCreatingNewGrado && existingGrados.length > 0"
                  type="button"
                  @click="isCreatingNewGrado = false; grupoForm.grado = existingGrados[0]"
                  class="text-[12px] text-primary hover:underline cursor-pointer"
                >
                  Elegir existente
                </button>
              </div>
              <select
                v-if="!isCreatingNewGrado && existingGrados.length > 0"
                v-model="grupoForm.grado"
                @change="onGradoSelectChange"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
              >
                <option value="" disabled>Selecciona grado...</option>
                <option v-for="g in existingGrados" :key="g" :value="g">{{ g }}</option>
                <option value="__NEW__" class="text-primary font-bold">+ Crear nuevo grado...</option>
              </select>
              <input
                v-else
                v-model="grupoForm.grado"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
                type="text"
                placeholder="Ej: Primero, Transición"
              />
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
          <button @click="submitGrupo" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar Grupo' : 'Guardar Grupo' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: CARGA ACADÉMICA -->
    <div v-if="showCargaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">assignment_turned_in</span>
          {{ isEditing ? 'Editar Carga Académica' : 'Asignar Carga Académica' }}
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
          <button @click="submitCarga" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar Carga' : 'Asignar Carga' }}</button>
        </div>
      </div>
    </div>

  </div>
  <!-- Modal de confirmación de eliminación -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="confirmDeleteEntity"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
        style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
        @click.self="cancelDeleteEntity"
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
            <h3 style="font-size:17px; font-weight:700; color:#111827; margin:0;">{{ confirmDeleteEntity.title }}</h3>
          </div>

          <!-- Body text -->
          <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 8px 0;">
            ¿Estás seguro de que deseas eliminar <span v-if="confirmDeleteEntity.type !== 'carga'">a</span>
            <strong v-if="confirmDeleteEntity.name" style="color:#111827;">{{ confirmDeleteEntity.name }}</strong><span v-else>este elemento</span>?
          </p>
          <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 20px 0;">
            {{ confirmDeleteEntity.warningText }}
            <strong style="color:#ef4444;">Esta acción no se puede deshacer.</strong>
          </p>

          <!-- Error -->
          <div
            v-if="errorMsg"
            style="background:#fee2e2; color:#dc2626; border-radius:10px; padding:12px 16px; font-size:13px; margin-bottom:16px;"
          >
            {{ errorMsg }}
          </div>

          <!-- Actions -->
          <div style="display:flex; justify-content:flex-end; gap:12px;">
            <button
              @click="cancelDeleteEntity"
              :disabled="deletingEntity"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:500; color:#374151; background:transparent; border:1px solid #e5e7eb; cursor:pointer; transition:background .15s;"
              @mouseenter="($event.target as HTMLElement).style.background='#f9fafb'"
              @mouseleave="($event.target as HTMLElement).style.background='transparent'"
            >
              Cancelar
            </button>
            <button
              @click="confirmDeleteAction"
              :disabled="deletingEntity"
              style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:600; color:#fff; background:#ef4444; border:none; cursor:pointer; display:flex; align-items:center; gap:8px; transition:background .15s;"
              @mouseenter="($event.target as HTMLElement).style.background='#dc2626'"
              @mouseleave="($event.target as HTMLElement).style.background='#ef4444'"
            >
              <span v-if="deletingEntity" class="material-symbols-outlined" style="font-size:18px; animation:spin 1s linear infinite;">progress_activity</span>
              <span v-else class="material-symbols-outlined" style="font-size:18px;">delete</span>
              {{ deletingEntity ? 'Eliminando...' : 'Sí, eliminar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
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
.modal-enter-active > div > div {
  transition: transform 0.18s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.modal-leave-active > div > div {
  transition: transform 0.15s ease-in;
}
.modal-enter-from > div > div,
.modal-leave-to > div > div {
  transform: scale(0.95);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

input[type="checkbox"] {
  accent-color: var(--color-primary);
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
