<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// State management
const activeTab = ref('sedes') // 'sedes', 'docentes', 'grados', 'grupos', 'asignaturas', 'carga', 'periodos', 'configuracion'
const loading = ref(false)
const isSubmitting = ref(false)
const errorMsg = ref<string | null>(null)
const successMsg = ref<string | null>(null)

// Data arrays from API
const sedes = ref<any[]>([])
const docentes = ref<any[]>([])
const grados = ref<any[]>([])
const areas = ref<any[]>([])
const asignaturas = ref<any[]>([])
const grupos = ref<any[]>([])
const cargas = ref<any[]>([])
const periodos = ref<any[]>([])

// Modals visibility
const showSedeModal = ref(false)
const showDocenteModal = ref(false)
const showGradoModal = ref(false)
const showAreaModal = ref(false)
const showAsignaturaModal = ref(false)
const showGrupoModal = ref(false)
const showCargaModal = ref(false)
const showPeriodoModal = ref(false)

// Form fields
const sedeForm = ref({ nombre: '', direccion: '', telefono: '' })
const docenteForm = ref({ email: '', password: '', nombre: '', apellido: '', rol: 'docente_aula', cargo: 'Docente', sede_ids: [] as string[] })
const gradoForm = ref({ nombre: '' })
const areaForm = ref({ nombre: '' })
const customAreaName = ref('')
const asignaturaForm = ref({ nombre: '', area_id: '' })
const grupoForm = ref({ nombre: '', grado_id: '', sede_id: '', director_id: '' })
const cargaForm = ref({ docente_id: '', asignatura_id: '', grupo_ids: [] as string[] })
const periodoForm = ref({ nombre: '', fecha_inicio: '', fecha_fin: '' })

const configForm = ref({ gemini_api_key: '', contexto_institucion: '' })
const configSaving = ref(false)

const passwordSecured = ref(false)

const hasMinLength = computed(() => docenteForm.value.password.length >= 8)
const hasLetter = computed(() => /[A-Za-z]/.test(docenteForm.value.password))
const hasNumber = computed(() => /\d/.test(docenteForm.value.password))
const hasSpecialChar = computed(() => /[^A-Za-z0-9]/.test(docenteForm.value.password))
const passwordIsValid = computed(() => hasMinLength.value && hasLetter.value && hasNumber.value && hasSpecialChar.value)

const puedeRegistrarDocente = computed(() => {
  if (editingId.value) return true
  return passwordIsValid.value && passwordSecured.value
})

// Computed properties for grouping
const groupedCargas = computed(() => {
  const groups = new Map<string, any>()
  for (const c of cargas.value) {
    const key = `${c.docente_id}_${c.asignatura.id}`
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        docente_id: c.docente_id,
        docente_nombre: c.docente_nombre,
        asignatura: c.asignatura,
        grupos: [],
        cargas: [] // Store original records
      })
    }
    const group = groups.get(key)
    // Avoid duplicate groups in case of DB inconsistency
    if (!group.grupos.find((g: any) => g.id === c.grupo.id)) {
      group.grupos.push(c.grupo)
    }
    group.cargas.push(c)
  }
  // Sort groups naturally by degree/name for better UX
  Array.from(groups.values()).forEach(group => {
    group.grupos.sort((a: any, b: any) => {
      const aName = `${a.grado} - ${a.nombre}`
      const bName = `${b.grado} - ${b.nombre}`
      return aName.localeCompare(bName)
    })
  })
  return Array.from(groups.values())
})

// Load all management data
const loadData = async () => {
  if (!authStore.token) return
  loading.value = true
  errorMsg.value = null
  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    
    // Fetch all in parallel
    const [sedesRes, docentesRes, gradosRes, areasRes, asignaturasRes, gruposRes, cargasRes, periodosRes] = await Promise.all([
      fetch('/api/v1/gestion/sedes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/docentes', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/grados', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/areas', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/asignaturas', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/grupos', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/carga-academica', { headers }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/gestion/periodos', { headers }).then(r => r.ok ? r.json() : [])
    ])

    sedes.value = sedesRes
    docentes.value = docentesRes
    grados.value = gradosRes
    areas.value = areasRes
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

const loadConfig = async () => {
  if (!authStore.token) return
  loading.value = true
  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    const res = await fetch('/api/v1/configuracion', { headers })
    if (res.ok) {
      const data = await res.json()
      configForm.value = {
        gemini_api_key: data.gemini_api_key || '',
        contexto_institucion: data.contexto_institucion || ''
      }
    }
  } catch {
    errorMsg.value = 'Error al cargar la configuración del sistema.'
  } finally {
    loading.value = false
  }
}

const submitConfig = async () => {
  if (!authStore.token) return
  configSaving.value = true
  errorMsg.value = null
  successMsg.value = null
  try {
    const headers = {
      'Authorization': `Bearer ${authStore.token}`,
      'Content-Type': 'application/json'
    }
    const body: any = {
      gemini_api_key: configForm.value.gemini_api_key || null,
      contexto_institucion: configForm.value.contexto_institucion.trim() || null
    }
    const res = await fetch('/api/v1/configuracion', {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body)
    })
    await handleResponse(res, 'Error al actualizar la configuración.')
    await loadConfig()
    successMsg.value = 'Configuración actualizada correctamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  } finally {
    configSaving.value = false
  }
}

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
const isEditing = ref(false)



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
  passwordSecured.value = false
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

const generarContrasenaAleatoria = () => {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const lower = 'abcdefghijkmnpqrstuvwxyz'
  const digits = '23456789'
  const specials = '!@#$%&*_-+=?'
  const all = upper + lower + digits + specials

  const pool = [
    upper[Math.floor(Math.random() * upper.length)],
    lower[Math.floor(Math.random() * lower.length)],
    digits[Math.floor(Math.random() * digits.length)],
    specials[Math.floor(Math.random() * specials.length)],
  ]
  for (let i = pool.length; i < 12; i++) {
    pool.push(all[Math.floor(Math.random() * all.length)])
  }
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]]
  }
  docenteForm.value.password = pool.join('')
}

const copiarContrasena = async () => {
  try {
    const f = docenteForm.value
    const nombreCompleto = [f.nombre, f.apellido].filter(Boolean).join(' ') || 'Docente'
    const texto = `Email: ${f.email}\nContraseña: ${f.password}\nAccede en: ${window.location.origin}/login`
    await navigator.clipboard.writeText(texto)
    passwordSecured.value = true
  } catch {
    const f = docenteForm.value
    const nombreCompleto = [f.nombre, f.apellido].filter(Boolean).join(' ') || 'Docente'
    const texto = `Email: ${f.email}\nContraseña: ${f.password}\nAccede en: ${window.location.origin}/login`
    const ta = document.createElement('textarea')
    ta.value = texto
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    passwordSecured.value = true
  }
}

const descargarContrasenaTxt = () => {
  const f = docenteForm.value
  const nombreCompleto = [f.nombre, f.apellido].filter(Boolean).join(' ') || 'Docente'
  const contenido = [
    'Credenciales de acceso — OpenPiar',
    '',
    `Nombre:   ${nombreCompleto}`,
    `Email:    ${f.email || 'No especificado'}`,
    `Contraseña: ${f.password}`,
    '',
    `Accede en: ${window.location.origin}/login`,
  ].join('\n')
  const blob = new Blob([contenido], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `credenciales-${nombreCompleto.toLowerCase().replace(/\s+/g, '-')}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  passwordSecured.value = true
}

const STANDARD_AREAS_SUBJECTS: Record<string, string[]> = {
  "Ciencias Naturales y Educación Ambiental": ["Ciencias Naturales", "Física", "Química", "Procesos Fisicoquímicos"],
  "Matemáticas": ["Matemáticas", "Geometría", "Estadística"],
  "Ciencias Sociales": ["Ciencias Sociales", "Historia", "Geografía"],
  "Humanidades, Lengua Castellana e Idiomas Extranjeros": ["Humanidades / Lengua Castellana (Español)", "Inglés"],
  "Educación Física, Recreación y Deportes": ["Educación Física"],
  "Educación Artística y Cultural": ["Educación Artística y Cultural"],
  "Educación Ética y en Valores Humanos": ["Ética y Valores"],
  "Educación Religiosa": ["Educación Religiosa"],
  "Tecnología e Informática": ["Tecnología e Informática"],
  "Filosofía": ["Filosofía"],
  "Ciencias Económicas y Políticas": ["Ciencias Económicas y Políticas"],
  "Dimensiones": ["Socio afectiva", "Corporal", "Comunicativa", "Cognitiva", "Ética", "Estética", "Espiritual"]
}

const selectedStandardSubject = ref('')
const recommendedSubjects = ref<string[]>([])
const hasStandardSubjects = ref(false)

const availableGradosOptions = computed(() => {
  const standardGrados = ['Pre-jardín', 'Jardín', 'Preescolar', '1°', '2°', '3°', '4°', '5°', '6°', '7°', '8°', '9°', '10°', '11°']
  const existingNames = new Set(grados.value.map(g => g.nombre))
  return standardGrados.filter(name => !existingNames.has(name))
})

const availableAreasOptions = computed(() => {
  const standardAreas = [
    'Ciencias Naturales y Educación Ambiental',
    'Matemáticas',
    'Ciencias Sociales',
    'Humanidades, Lengua Castellana e Idiomas Extranjeros',
    'Educación Física, Recreación y Deportes',
    'Educación Artística y Cultural',
    'Educación Ética y en Valores Humanos',
    'Educación Religiosa',
    'Tecnología e Informática',
    'Filosofía',
    'Ciencias Económicas y Políticas',
    'Dimensiones'
  ]
  const existingNames = new Set(areas.value.map(a => a.nombre))
  return standardAreas.filter(name => !existingNames.has(name))
})

const onAreaChange = () => {
  const selectedArea = areas.value.find(ar => ar.id === asignaturaForm.value.area_id)
  if (selectedArea && STANDARD_AREAS_SUBJECTS[selectedArea.nombre]) {
    const allSubjects = STANDARD_AREAS_SUBJECTS[selectedArea.nombre] || []
    
    // Filter out subjects already registered in this area
    const existingSubsInArea = new Set(
      asignaturas.value
        .filter(asig => asig.area_id === selectedArea.id)
        .map(asig => asig.nombre)
    )
    
    recommendedSubjects.value = allSubjects.filter(sub => !existingSubsInArea.has(sub))
    hasStandardSubjects.value = true
    selectedStandardSubject.value = ''
    asignaturaForm.value.nombre = ''
  } else {
    recommendedSubjects.value = []
    hasStandardSubjects.value = false
    selectedStandardSubject.value = '__CUSTOM__'
  }
}

const onStandardSubjectChange = () => {
  if (selectedStandardSubject.value !== '__CUSTOM__') {
    asignaturaForm.value.nombre = selectedStandardSubject.value
  } else {
    asignaturaForm.value.nombre = ''
  }
}

const openNewAsignatura = () => {
  editingId.value = null
  asignaturaForm.value = { nombre: '', area_id: '' }
  selectedStandardSubject.value = ''
  recommendedSubjects.value = []
  hasStandardSubjects.value = false
  showAsignaturaModal.value = true
}

const openEditAsignatura = (asignatura: any) => {
  editingId.value = asignatura.id
  asignaturaForm.value = { nombre: asignatura.nombre, area_id: asignatura.area_id }
  
  const selectedArea = areas.value.find(ar => ar.id === asignatura.area_id)
  if (selectedArea && STANDARD_AREAS_SUBJECTS[selectedArea.nombre]) {
    const allSubjects = STANDARD_AREAS_SUBJECTS[selectedArea.nombre] || []
    
    // Existing subjects in the area, except the current one being edited
    const existingSubsInArea = new Set(
      asignaturas.value
        .filter(asig => asig.area_id === selectedArea.id && asig.id !== asignatura.id)
        .map(asig => asig.nombre)
    )
    
    recommendedSubjects.value = allSubjects.filter(sub => !existingSubsInArea.has(sub))
    hasStandardSubjects.value = true
    
    if (recommendedSubjects.value.includes(asignatura.nombre)) {
      selectedStandardSubject.value = asignatura.nombre
    } else {
      selectedStandardSubject.value = '__CUSTOM__'
    }
  } else {
    recommendedSubjects.value = []
    hasStandardSubjects.value = false
    selectedStandardSubject.value = '__CUSTOM__'
  }
  showAsignaturaModal.value = true
}

const openNewArea = () => {
  editingId.value = null
  areaForm.value = { nombre: '' }
  customAreaName.value = ''
  showAreaModal.value = true
}

const openNewGrado = () => {
  editingId.value = null
  gradoForm.value = { nombre: 'Preescolar' }
  showGradoModal.value = true
}

const openNewGrupo = () => {
  editingId.value = null
  grupoForm.value = { nombre: '', grado_id: '', sede_id: '', director_id: '' }
  showGrupoModal.value = true
}

const openEditGrupo = (grupo: any) => {
  editingId.value = grupo.id
  const matchGrado = grados.value.find((gr: any) => gr.nombre === grupo.grado)
  grupoForm.value = {
    nombre: grupo.nombre,
    grado_id: matchGrado ? matchGrado.id : '',
    sede_id: grupo.sede.id,
    director_id: grupo.director ? grupo.director.id : ''
  }
  showGrupoModal.value = true
}

const openNewCarga = () => {
  isEditing.value = false
  cargaForm.value = { docente_id: '', asignatura_id: '', grupo_ids: [] }
  showCargaModal.value = true
}

const openEditCarga = (groupedCarga: any) => {
  isEditing.value = true
  editingId.value = groupedCarga.key
  cargaForm.value = {
    docente_id: groupedCarga.docente_id,
    asignatura_id: groupedCarga.asignatura.id,
    grupo_ids: groupedCarga.grupos.map((g: any) => g.id)
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
  if (!editingId.value && !passwordIsValid.value) {
    errorMsg.value = 'La contraseña no cumple con los requisitos mínimos de seguridad.'
    return
  }
  if (!editingId.value && !passwordSecured.value) {
    errorMsg.value = 'Debes copiar o descargar la contraseña antes de registrar.'
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
  if (!asignaturaForm.value.nombre || !asignaturaForm.value.area_id) {
    errorMsg.value = 'El nombre de la asignatura y el área son obligatorios.'
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
          c.asignatura.area_id = data.area_id
          c.asignatura.area_nombre = data.area_nombre
        }
      })
    } else {
      asignaturas.value.push(data)
    }
    showAsignaturaModal.value = false
    asignaturaForm.value = { nombre: '', area_id: '' }
    successMsg.value = isEdit ? 'Asignatura actualizada exitosamente.' : 'Asignatura registrada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitArea = async () => {
  const nombreFinal = areaForm.value.nombre === '__CUSTOM__' ? customAreaName.value : areaForm.value.nombre
  if (!nombreFinal) {
    errorMsg.value = 'El nombre del área es obligatorio.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/areas/${editingId.value}` : '/api/v1/gestion/areas'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({ nombre: nombreFinal })
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar área' : 'Error al registrar área')
    
    if (isEdit) {
      const idx = areas.value.findIndex(a => a.id === editingId.value)
      if (idx !== -1) areas.value[idx] = data
    } else {
      areas.value.push(data)
    }
    showAreaModal.value = false
    areaForm.value = { nombre: '' }
    customAreaName.value = ''
    successMsg.value = isEdit ? 'Área de aprendizaje actualizada exitosamente.' : 'Área de aprendizaje registrada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitGrado = async () => {
  if (!gradoForm.value.nombre) {
    errorMsg.value = 'El nombre del grado es obligatorio.'
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const isEdit = editingId.value !== null
    const url = isEdit ? `/api/v1/gestion/grados/${editingId.value}` : '/api/v1/gestion/grados'
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify(gradoForm.value)
    })
    const data = await handleResponse(res, isEdit ? 'Error al actualizar grado' : 'Error al registrar grado')
    
    if (isEdit) {
      const idx = grados.value.findIndex(g => g.id === editingId.value)
      if (idx !== -1) grados.value[idx] = data
    } else {
      grados.value.push(data)
    }
    showGradoModal.value = false
    gradoForm.value = { nombre: '' }
    successMsg.value = isEdit ? 'Grado actualizado exitosamente.' : 'Grado registrado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitGrupo = async () => {
  const f = grupoForm.value
  if (!f.nombre || !f.grado_id || !f.sede_id) {
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
      grado_id: f.grado_id,
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
    grupoForm.value = { nombre: '', grado_id: '', sede_id: '', director_id: '' }
    successMsg.value = isEdit ? 'Grupo actualizado exitosamente.' : 'Grupo registrado exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

const submitCarga = async () => {
  const f = cargaForm.value
  if (!f.docente_id || !f.asignatura_id || f.grupo_ids.length === 0) {
    errorMsg.value = 'Completa todos los campos y selecciona al menos un grupo.'
    return
  }

  isSubmitting.value = true
  errorMsg.value = ''

  try {
    const headers = {
      'Authorization': `Bearer ${authStore.token}`,
      'Content-Type': 'application/json'
    }

    if (isEditing.value) {
      const groupedCarga = groupedCargas.value.find(g => g.key === editingId.value)
      if (!groupedCarga) throw new Error("Carga original no encontrada.")

      const oldGroupIds = groupedCarga.grupos.map((g: any) => g.id)
      const newGroupIds = f.grupo_ids

      const toAdd = newGroupIds.filter((id: string) => !oldGroupIds.includes(id))
      const toRemove = oldGroupIds.filter((id: string) => !newGroupIds.includes(id))

      // Delete removed
      for (const removedGroupId of toRemove) {
        const cargaRecord = groupedCarga.cargas.find((c: any) => c.grupo.id === removedGroupId)
        if (cargaRecord) {
          const delRes = await fetch(`/api/v1/gestion/carga-academica/${cargaRecord.id}`, { method: 'DELETE', headers })
          if (delRes.ok) {
            cargas.value = cargas.value.filter(c => c.id !== cargaRecord.id)
          }
        }
      }

      // Add new
      for (const addedGroupId of toAdd) {
        const payload = { docente_id: f.docente_id, asignatura_id: f.asignatura_id, grupo_id: addedGroupId }
        const addRes = await fetch('/api/v1/gestion/carga-academica', { method: 'POST', headers, body: JSON.stringify(payload) })
        if (addRes.ok) {
          const data = await addRes.json()
          cargas.value.push(data)
        }
      }

    } else {
      // Create new for all selected groups
      for (const groupId of f.grupo_ids) {
        const payload = { docente_id: f.docente_id, asignatura_id: f.asignatura_id, grupo_id: groupId }
        const res = await fetch('/api/v1/gestion/carga-academica', { method: 'POST', headers, body: JSON.stringify(payload) })
        if (res.ok) {
          const data = await res.json()
          cargas.value.push(data)
        } else {
          const errData = await res.json()
          console.error("Error al asignar carga:", errData)
          // We don't abort, just log. Some might succeed, some might fail if already exists.
        }
      }
    }

    showCargaModal.value = false
    cargaForm.value = { docente_id: '', asignatura_id: '', grupo_ids: [] }
    successMsg.value = isEditing.value ? 'Carga académica actualizada exitosamente.' : 'Carga académica asignada exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message || 'Error al procesar la carga'
  } finally {
    isSubmitting.value = false
  }
}

const confirmDeleteEntity = ref<{
  id: string;
  name: string;
  type: 'sede' | 'docente' | 'grado' | 'area' | 'asignatura' | 'grupo' | 'carga' | 'periodo';
  title: string;
  warningText: string;
} | null>(null)

const deletingEntity = ref(false)

const promptDelete = (
  id: string,
  name: string,
  type: 'sede' | 'docente' | 'grado' | 'area' | 'asignatura' | 'grupo' | 'carga' | 'periodo',
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
  else if (type === 'grado') await deleteGrado(id, name, true)
  else if (type === 'area') await deleteArea(id, name, true)
  else if (type === 'asignatura') await deleteAsignatura(id, name, true)
  else if (type === 'grupo') await deleteGrupo(id, name, true)
  else if (type === 'carga') await deleteCarga(id, true)
  else if (type === 'periodo') await deletePeriodo(id, name, true)
  
  deletingEntity.value = false
  if (!errorMsg.value) {
    confirmDeleteEntity.value = null
  }
}

const deleteCarga = async (groupedKey: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(groupedKey, '', 'carga', 'Eliminar asignación de carga', 'Se eliminará esta asignación de carga académica de manera permanente para todos los grupos seleccionados.')
    return
  }
  
  const groupedCarga = groupedCargas.value.find(g => g.key === groupedKey)
  if (!groupedCarga) return

  isSubmitting.value = true
  errorMsg.value = ''

  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    for (const cargaRecord of groupedCarga.cargas) {
      await fetch(`/api/v1/gestion/carga-academica/${cargaRecord.id}`, {
        method: 'DELETE',
        headers
      })
      // Even if one fails, we proceed with others
    }
    
    const idsToRemove = groupedCarga.cargas.map((c: any) => c.id)
    cargas.value = cargas.value.filter(c => !idsToRemove.includes(c.id))
    successMsg.value = 'Carga académica removida exitosamente.'
  } catch (err: any) {
    errorMsg.value = err.message || 'Error al eliminar la carga'
  } finally {
    isSubmitting.value = false
    confirmDeleteEntity.value = null
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

const deleteArea = async (id: string, nombre: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombre, 'area', 'Eliminar área', 'Se eliminarán todas las asignaturas asociadas a esta área de aprendizaje y sus correspondientes cargas académicas.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/areas/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar el área'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    areas.value = areas.value.filter(a => a.id !== id)
    asignaturas.value = asignaturas.value.filter(a => a.area_id !== id)
    cargas.value = cargas.value.filter(c => c.asignatura.area_id !== id)
    successMsg.value = 'Área de aprendizaje eliminada exitosamente junto con sus datos relacionados.'
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

const deleteGrado = async (id: string, nombreCompleto: string, confirmed: boolean = false) => {
  if (!confirmed) {
    promptDelete(id, nombreCompleto, 'grado', 'Eliminar grado', 'Se eliminarán todos los grupos vinculados a este grado y sus cargas académicas relacionadas.')
    return
  }
  errorMsg.value = null
  successMsg.value = null
  try {
    const res = await fetch(`/api/v1/gestion/grados/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      let detail = 'No se pudo eliminar el grado'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (_) {}
      throw new Error(detail)
    }
    
    await loadData()
    successMsg.value = 'Grado eliminado exitosamente junto con sus datos relacionados.'
  } catch (err: any) {
    errorMsg.value = err.message
  }
}
</script>

<template>
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
            @click="activeTab = 'grados'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'grados' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Grados
          </button>
          <button
            @click="activeTab = 'grupos'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'grupos' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Grupos
          </button>
          <button
            @click="activeTab = 'areas'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'areas' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Áreas
          </button>
          <button
            @click="activeTab = 'asignaturas'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'asignaturas' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Asignaturas
          </button>
          <button
            @click="activeTab = 'carga'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'carga' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Carga académica
          </button>
          <button
            @click="activeTab = 'periodos'"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'periodos' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Periodos académicos
          </button>
          <button
            @click="activeTab = 'configuracion'; loadConfig()"
            class="pb-sm px-2 font-label-md text-label-md transition-all relative cursor-pointer"
            :class="activeTab === 'configuracion' ? 'text-primary border-b-2 border-primary font-bold' : 'text-outline hover:text-on-surface'"
          >
            Configuración
          </button>
        </div>

        <!-- 1. TAB: SEDES -->
        <div v-if="activeTab === 'sedes'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Sedes educativas</h3>
            <button
              @click="openNewSede()"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">add_home</span>
              Nueva sede
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
            <h3 class="font-headline-md text-[20px]">Docentes registrados</h3>
            <button
              @click="openNewDocente()"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">person_add</span>
              Registrar docente
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre</th>
                  <th class="py-4 px-md">Email</th>
                  <th class="py-4 px-md">Rol / Cargo</th>
                  <th class="py-4 px-md">Sedes asignadas</th>
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

        <!-- 3. TAB: GRADOS -->
        <div v-if="activeTab === 'grados'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Grados escolares</h3>
            <button
              @click="openNewGrado()"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">school</span>
              Nuevo grado
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre</th>
                  <th class="py-4 px-md">Fecha registro</th>
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md">
                <tr v-if="grados.length === 0">
                  <td colspan="3" class="py-8 text-center text-outline">
                    No hay grados registrados. Registra un grado para poder crear grupos.
                  </td>
                </tr>
                <tr v-else v-for="gr in grados" :key="gr.id" class="hover:bg-surface-container-low/50 transition-colors">
                  <td class="py-4 px-md font-medium text-on-surface">{{ gr.nombre }}</td>
                  <td class="py-4 px-md text-on-surface-variant">{{ new Date(gr.created_at).toLocaleDateString() }}</td>
                  <td class="py-4 px-md text-right">
                    <button
                      @click="promptDelete(gr.id, gr.nombre, 'grado', 'Eliminar grado', 'Se eliminarán todos los grupos vinculados a este grado y sus cargas académicas relacionadas.')"
                      class="text-outline hover:text-error transition-colors p-1 cursor-pointer"
                      title="Eliminar"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- TAB: GRUPOS -->
        <div v-if="activeTab === 'grupos'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Grupos escolares</h3>
            <button
              @click="openNewGrupo()"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">groups</span>
              Nuevo grupo / curso
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Grado</th>
                  <th class="py-4 px-md">Nombre grupo</th>
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

        <!-- TAB: AREAS -->
        <div v-if="activeTab === 'areas'" class="space-y-md">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-[20px]">Áreas de aprendizaje</h3>
            <button
              @click="openNewArea()"
              class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
            >
              <span class="material-symbols-outlined text-[20px]">category</span>
              Nueva área
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre de la área</th>
                  <th class="py-4 px-md">Fecha registro</th>
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md">
                <tr v-if="areas.length === 0">
                  <td colspan="3" class="py-8 text-center text-outline">
                    No hay áreas de aprendizaje registradas. Registra una para poder crear asignaturas.
                  </td>
                </tr>
                <tr v-else v-for="ar in areas" :key="ar.id" class="hover:bg-surface-container-low/50 transition-colors">
                  <td class="py-4 px-md font-medium text-on-surface">{{ ar.nombre }}</td>
                  <td class="py-4 px-md text-on-surface-variant">{{ new Date(ar.created_at).toLocaleDateString() }}</td>
                  <td class="py-4 px-md text-right">
                    <button
                      @click="promptDelete(ar.id, ar.nombre, 'area', 'Eliminar área de aprendizaje', 'Se eliminarán todas las asignaturas vinculadas a esta área y sus cargas académicas relacionadas.')"
                      class="text-outline hover:text-error transition-colors p-1 cursor-pointer"
                      title="Eliminar"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
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
              Nueva asignatura
            </button>
          </div>

          <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm transition-colors duration-300">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
                  <th class="py-4 px-md">Nombre de la Asignatura</th>
                  <th class="py-4 px-md">Área de Aprendizaje</th>
                  <th class="py-4 px-md text-right">Acciones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
                <tr v-for="a in asignaturas" :key="a.id" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-semibold text-primary">{{ a.nombre }}</td>
                  <td class="py-4 px-md text-on-surface-variant">{{ a.area_nombre }}</td>
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
                  <td colspan="3" class="py-8 text-center text-outline">No hay asignaturas registradas.</td>
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
              Asignar carga
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
                <tr v-for="c in groupedCargas" :key="c.key" class="hover:bg-surface-container-low/40">
                  <td class="py-4 px-md font-bold">{{ c.docente_nombre }}</td>
                  <td class="py-4 px-md font-semibold text-primary">{{ c.asignatura.nombre }}</td>
                  <td class="py-4 px-md">
                    <div class="flex flex-wrap gap-1">
                      <span v-for="g in c.grupos" :key="g.id" class="bg-surface-container-high px-2 py-1 rounded-md text-sm font-medium border border-outline-variant/50">
                        {{ g.grado }} - {{ g.nombre }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-md text-outline">
                    <span v-if="c.grupos.length > 0">{{ c.grupos[0].sede?.nombre || 'Varias' }}</span>
                  </td>
                  <td class="py-4 px-md text-right flex justify-end gap-xs">
                    <button
                      @click="openEditCarga(c)"
                      class="text-primary hover:bg-primary/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Editar Carga Académica"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deleteCarga(c.key)"
                      class="text-error hover:bg-error/10 p-2 rounded-full cursor-pointer transition-all"
                      title="Eliminar asignación de carga"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
                <tr v-if="groupedCargas.length === 0">
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
              <h3 class="text-title-lg font-bold text-on-surface">Periodos académicos</h3>
              <p class="text-body-md text-on-surface-variant">
                Gestiona los periodos escolares. Solo puede haber un periodo activo a la vez.
              </p>
            </div>
            <button
              @click="openNewPeriodo"
              class="flex items-center gap-2 bg-primary text-on-primary px-4 py-2 rounded-xl font-label-md hover:bg-primary/90 transition-all shadow-sm cursor-pointer"
            >
              <span class="material-symbols-outlined text-[20px]">add</span>
              Nuevo periodo
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
                  <th class="px-md py-sm font-semibold">Nombre del periodo</th>
                  <th class="px-md py-sm font-semibold">Fecha de inicio</th>
                  <th class="px-md py-sm font-semibold">Fecha fin</th>
                  <th class="px-md py-sm font-semibold text-center">Estado (activo)</th>
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
                       title="Editar periodo"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button
                      @click="deletePeriodo(periodo.id, periodo.nombre)"
                      class="text-error hover:text-error/80 transition-colors cursor-pointer"
                       title="Eliminar periodo"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- CONFIGURACIÓN DEL SISTEMA -->
        <div v-if="activeTab === 'configuracion'" class="animate-fade-in">
          <div class="mb-md">
            <h3 class="text-title-lg font-bold text-on-surface">Configuración del sistema</h3>
            <p class="text-body-md text-on-surface-variant">
              Ajusta el contexto institucional y la clave de IA. Estos datos se utilizan para que el Asistente de IA genere ajustes razonables acordes a la realidad de tu institución.
            </p>
          </div>

          <div v-if="loading" class="py-10 text-center text-outline">
            Cargando configuración...
          </div>
          <div v-else class="bg-surface-container-lowest rounded-2xl border border-outline-variant/30 p-md space-y-md">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="config-gemini">
                Gemini API Key
              </label>
              <input
                id="config-gemini"
                v-model="configForm.gemini_api_key"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ingresa tu API Key de Gemini"
                type="password"
              />
              <p class="font-label-sm text-label-sm text-on-surface-variant">
                La API Key se usa para que el asistente de IA genere sugerencias de ajustes razonables. Puedes obtener una gratuita en <a href="https://aistudio.google.com/" target="_blank" class="text-primary underline">Google AI Studio</a>.
              </p>
            </div>

            <div class="space-y-xs">
              <div class="flex justify-between items-center">
                <label class="font-label-md text-label-md text-on-surface-variant" for="config-contexto">
                  Contexto de la institución <span class="text-on-surface-variant/60 font-normal">(opcional)</span>
                </label>
                <span class="font-label-sm text-label-sm" :class="configForm.contexto_institucion.length > 0 && configForm.contexto_institucion.length < 100 ? 'text-error' : 'text-on-surface-variant'">
                  {{ configForm.contexto_institucion.length }}/100 caracteres mínimo
                </span>
              </div>
              <textarea
                id="config-contexto"
                v-model="configForm.contexto_institucion"
                rows="5"
                class="w-full px-4 py-3 bg-surface border rounded-input font-body-md focus:outline-none focus:ring-4 resize-y"
                :class="configForm.contexto_institucion && configForm.contexto_institucion.length < 100 ? 'border-error ring-error/10 focus:ring-error/10' : 'border-outline-variant focus:border-primary focus:ring-primary/10'"
                placeholder="Describe el contexto de tu institución para que la IA pueda sugerir ajustes razonables realistas. Por ejemplo: Institución rural ubicada en el municipio de San Vicente de Ferrer, con limitada conectividad a internet. Cuenta con una sola sede, 8 docentes y no dispone de sala de tecnología ni laboratorio. Los estudiantes son mayoritariamente de familias campesinas con acceso limitado a útiles escolares especializados."
              ></textarea>
              <p class="font-label-sm text-label-sm text-on-surface-variant">
                Este contexto ayudará al Asistente de IA a proponer ajustes razonables viables, evitando sugerir estrategias que no se ajusten a la realidad de tu institución. El contexto no se usa directamente para formular los ajustes, sino para saber qué recursos y estrategias son pertinentes.
              </p>
            </div>

            <div class="flex justify-end pt-sm border-t border-outline-variant/30">
              <button
                @click="submitConfig"
                :disabled="configSaving || (configForm.contexto_institucion.trim() !== '' && configForm.contexto_institucion.trim().length < 100)"
                class="px-lg py-3 bg-primary text-on-primary font-label-md text-label-md rounded-xl shadow-md flex items-center gap-xs cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:bg-primary/90 active:scale-95"
              >
                <span v-if="configSaving" class="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
                <span v-else class="material-symbols-outlined text-[20px]">save</span>
                {{ configSaving ? 'Guardando...' : 'Guardar configuración' }}
              </button>
            </div>
          </div>
        </div>

  <!-- Modal Periodo Académico -->
  <div v-if="showPeriodoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" @click.self="showPeriodoModal = false">
    <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md animate-scale-up">
      <div class="flex justify-between items-center">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'add_circle' }}</span>
          {{ isEditing ? 'Editar periodo académico' : 'Nuevo periodo académico' }}
        </h3>
        <button @click="showPeriodoModal = false" class="text-on-surface-variant hover:text-error transition-colors cursor-pointer">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="space-y-sm">
        <div class="space-y-xs">
          <label class="font-label-md text-label-md text-on-surface-variant">Nombre del periodo *</label>
          <input
            v-model="periodoForm.nombre"
            type="text"
            class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            placeholder="Ej: Primer Semestre 2026"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Fecha de inicio *</label>
            <input
              v-model="periodoForm.fecha_inicio"
              type="date"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Fecha fin *</label>
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
          Guardar periodo
        </button>
      </div>
    </div>
  </div>

    <!-- MODAL: SEDE -->
    <div v-if="showSedeModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'add_home' }}</span>
          {{ isEditing ? 'Editar sede educativa' : 'Nueva sede educativa' }}
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Nombre de la sede *</label>
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
          <button @click="submitSede" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar sede' : 'Guardar sede' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: DOCENTE -->
    <div v-if="showDocenteModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[512px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md overflow-y-auto max-h-[90vh]">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'manage_accounts' : 'person_add' }}</span>
          {{ isEditing ? 'Editar docente' : 'Registrar nuevo docente' }}
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
            <input v-model="docenteForm.password" class="w-full px-4 py-3 bg-surface border rounded-input font-body-md focus:outline-none focus:ring-4 dark:text-white" :class="!isEditing && docenteForm.password && !passwordIsValid ? 'border-error ring-error/10 focus:ring-error/10' : 'border-outline-variant focus:border-primary focus:ring-primary/10'" type="password" />

            <div v-if="!isEditing && docenteForm.password" class="pt-1 grid grid-cols-2 gap-xs">
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasMinLength ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasMinLength ? 'check_circle' : 'circle' }}</span> Mín. 8 caracteres
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasLetter ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasLetter ? 'check_circle' : 'circle' }}</span> Al menos una letra
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasNumber ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasNumber ? 'check_circle' : 'circle' }}</span> Al menos un número
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasSpecialChar ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasSpecialChar ? 'check_circle' : 'circle' }}</span> Un carácter especial
              </span>
            </div>

            <button
              v-if="!isEditing"
              @click="generarContrasenaAleatoria"
              class="text-label-sm text-primary font-bold flex items-center gap-1 hover:underline cursor-pointer select-none"
              type="button"
            >
              <span class="material-symbols-outlined text-[16px]">casino</span> Generar contraseña aleatoria
            </button>

            <div v-if="!isEditing && passwordIsValid" class="flex gap-sm pt-1">
              <button
                @click="copiarContrasena"
                class="px-3 py-2 bg-surface border border-outline-variant rounded-lg text-label-sm flex items-center gap-1 hover:bg-secondary-container transition-all cursor-pointer font-bold"
                type="button"
              >
                <span class="material-symbols-outlined text-[16px]">content_copy</span> Copiar
              </button>
              <button
                @click="descargarContrasenaTxt"
                class="px-3 py-2 bg-surface border border-outline-variant rounded-lg text-label-sm flex items-center gap-1 hover:bg-secondary-container transition-all cursor-pointer font-bold"
                type="button"
              >
                <span class="material-symbols-outlined text-[16px]">download</span> Descargar TXT
              </button>
            </div>
            <p v-if="!isEditing && passwordIsValid && !passwordSecured" class="text-amber-700 font-label-sm text-label-sm">
              Copia o descarga la contraseña para habilitar el registro.
            </p>
          </div>
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Rol de inclusión *</label>
              <select v-model="docenteForm.rol" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
                <option value="docente_aula">Docente de aula</option>
                <option value="docente_apoyo">Docente de apoyo</option>
                <option value="orientador">Docente orientador</option>
              </select>
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Cargo escolar</label>
              <input v-model="docenteForm.cargo" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant font-bold">Asignar sedes *</label>
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
          <button @click="submitDocente" :disabled="!puedeRegistrarDocente" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md transition-all active:scale-95" :class="puedeRegistrarDocente ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'">{{ isEditing ? 'Actualizar docente' : 'Registrar docente' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: ASIGNATURA -->
    <div v-if="showAsignaturaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_note' : 'book' }}</span>
          {{ isEditing ? 'Editar asignatura / materia' : 'Nueva asignatura / materia' }}
        </h3>
        <div class="space-y-sm">
          <!-- Selector de Área -->
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Área de aprendizaje *</label>
            <select
              v-model="asignaturaForm.area_id"
              @change="onAreaChange"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
            >
              <option value="" disabled>Selecciona un área...</option>
              <option v-if="areas.length === 0" disabled value="">No hay áreas registradas. Créalas primero.</option>
              <option v-for="ar in areas" :key="ar.id" :value="ar.id">{{ ar.nombre }}</option>
            </select>
          </div>

          <!-- Selector de Asignatura Estándar o Personalizada -->
          <div v-if="asignaturaForm.area_id" class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Asignatura *</label>
            
            <select
              v-if="hasStandardSubjects"
              v-model="selectedStandardSubject"
              @change="onStandardSubjectChange"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white mb-xs"
            >
              <option value="" disabled>Selecciona una asignatura recomendada...</option>
              <option v-for="sub in recommendedSubjects" :key="sub" :value="sub">{{ sub }}</option>
              <option value="__CUSTOM__" class="text-primary font-bold">+ Crear asignatura personalizada...</option>
            </select>

            <input
              v-if="!hasStandardSubjects || selectedStandardSubject === '__CUSTOM__'"
              v-model="asignaturaForm.nombre"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
              type="text"
              placeholder="Nombre de la asignatura (ej: Robótica, Alemán)"
            />
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showAsignaturaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitAsignatura" :disabled="!asignaturaForm.nombre || !asignaturaForm.area_id" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">{{ isEditing ? 'Guardar' : 'Guardar' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: AREA -->
    <div v-if="showAreaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">category</span>
          {{ isEditing ? 'Editar área' : 'Registrar nueva área' }}
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Selecciona el área *</label>
            
            <select
              v-model="areaForm.nombre"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white mb-xs"
            >
              <option value="" disabled>Selecciona una área estándar...</option>
              <option v-for="val in availableAreasOptions" :key="val" :value="val">{{ val }}</option>
              <option value="__CUSTOM__" class="text-primary font-bold">+ Crear área personalizada...</option>
            </select>

            <input
              v-if="areaForm.nombre === '__CUSTOM__'"
              type="text"
              v-model="customAreaName"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
              placeholder="Nombre del área personalizada (ej: Robótica)"
            />
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showAreaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitArea" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Guardar área</button>
        </div>
      </div>
    </div>

    <!-- MODAL: GRUPO -->
    <!-- MODAL: GRADO -->
    <div v-if="showGradoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">school</span>
          {{ isEditing ? 'Editar grado' : 'Registrar nuevo grado' }}
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Selecciona el grado *</label>
            <select v-model="gradoForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="" disabled>Selecciona un grado estándar...</option>
              <option v-for="val in availableGradosOptions" :key="val" :value="val">{{ val }}</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showGradoModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitGrado" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Guardar grado</button>
        </div>
      </div>
    </div>

    <!-- MODAL: GRUPO -->
    <div v-if="showGrupoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ isEditing ? 'edit_square' : 'groups' }}</span>
          {{ isEditing ? 'Editar grupo' : 'Nuevo grupo' }}
        </h3>
        <div class="space-y-sm">
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs flex flex-col">
              <label class="font-label-md text-label-md text-on-surface-variant">Grado *</label>
              <select
                v-model="grupoForm.grado_id"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white"
              >
                <option value="" disabled>Selecciona grado...</option>
                <option v-if="grados.length === 0" disabled value="">No hay grados registrados. Créalos primero en la pestaña de Grados.</option>
                <option v-for="gr in grados" :key="gr.id" :value="gr.id">{{ gr.nombre }}</option>
              </select>
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Grupo *</label>
              <input v-model="grupoForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" placeholder="Ej: A, B, 101" />
            </div>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Sede escolar *</label>
            <select v-model="grupoForm.sede_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Selecciona sede...</option>
              <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </div>
          
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Director de grupo (Opcional)</label>
            <select v-model="grupoForm.director_id" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="">Sin asignar director</option>
              <option v-for="d in docentes" :key="d.id" :value="d.id">{{ d.apellido }}, {{ d.nombre }}</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showGrupoModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitGrupo" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar grupo' : 'Guardar grupo' }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: CARGA ACADÉMICA -->
    <div v-if="showCargaModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[448px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">assignment_turned_in</span>
          {{ isEditing ? 'Editar carga académica' : 'Asignar carga académica' }}
        </h3>
        <div class="space-y-sm">
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar docente *</label>
            <select v-model="cargaForm.docente_id" :disabled="isEditing" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none disabled:opacity-60 disabled:bg-surface-variant dark:text-white">
              <option value="">Selecciona docente...</option>
              <option v-for="d in docentes" :key="d.id" :value="d.id">{{ d.apellido }}, {{ d.nombre }} ({{ d.rol.replace('docente_','') }})</option>
            </select>
          </div>

          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar asignatura *</label>
            <select v-model="cargaForm.asignatura_id" :disabled="isEditing" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none disabled:opacity-60 disabled:bg-surface-variant dark:text-white">
              <option value="">Selecciona asignatura...</option>
              <option v-for="a in asignaturas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
            </select>
          </div>

          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Seleccionar grupo / grado *</label>
            <div class="max-h-[200px] overflow-y-auto border border-outline-variant rounded-input bg-surface p-2">
              <label v-for="g in grupos" :key="g.id" class="flex items-center gap-2 p-2 hover:bg-surface-container-low cursor-pointer rounded-md">
                <input type="checkbox" :value="g.id" v-model="cargaForm.grupo_ids" class="w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary focus:ring-2">
                <span class="text-body-md text-on-surface">{{ g.grado }} - {{ g.nombre }} <span class="text-outline text-sm">({{ g.sede.nombre }})</span></span>
              </label>
            </div>
            <p class="text-label-sm text-on-surface-variant">Puedes seleccionar múltiples grupos.</p>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showCargaModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitCarga" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">{{ isEditing ? 'Actualizar carga' : 'Asignar carga' }}</button>
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
