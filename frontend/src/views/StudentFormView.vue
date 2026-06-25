<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted, watch, computed, reactive, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStudentsStore } from '../stores/students'
import { useAuthStore } from '../stores/auth'
import { DEPARTAMENTOS } from '../data/colombia'

const router = useRouter()
const route = useRoute()
const studentsStore = useStudentsStore()
const authStore = useAuthStore()

// State
const currentStep = ref(1)
const isEditMode = ref(false)
const validationError = ref<string | null>(null)

// Catalog lists
const sedes = ref<any[]>([])
const grupos = ref<any[]>([])
const loadingSedesGrupos = ref(false)
const selectedSedeId = ref<string>('')

// Soporte médico (PDF)
const medicalSupportFile = ref<File | null>(null)
const isDeletingSupport = ref(false)
const isDownloadingSupport = ref(false)
const supportInputRef = ref<HTMLInputElement | null>(null)

async function downloadMedicalSupport() {
  const studentId = route.params.id as string
  if (!studentId) return
  
  isDownloadingSupport.value = true
  try {
    const blob = await studentsStore.downloadMedicalSupport(studentId)
    const url = window.URL.createObjectURL(blob)
    
    // Open PDF in a new tab
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    a.remove()
    
    setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 15000)
  } catch (e: any) {
    alert(e.message || 'Error al descargar el soporte médico.')
  } finally {
    isDownloadingSupport.value = false
  }
}

function onSupportFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      medicalSupportFile.value = file
    } else {
      alert('El soporte médico debe ser un archivo PDF (.pdf).')
      target.value = ''
    }
  }
}

async function removeExistingSupport() {
  const studentId = route.params.id as string
  if (!studentId) {
    medicalSupportFile.value = null
    studentsStore.draft.salud.soporte_medico_nombre = null
    return
  }
  
  if (confirm('¿Estás seguro de que deseas eliminar permanentemente el soporte médico del diagnóstico?')) {
    isDeletingSupport.value = true
    try {
      await studentsStore.deleteMedicalSupport(studentId)
      medicalSupportFile.value = null
    } catch (e: any) {
      alert(e.message || 'Error al eliminar el soporte médico.')
    } finally {
      isDeletingSupport.value = false
    }
  }
}

function triggerSupportFileSelect() {
  supportInputRef.value?.click()
}

const filteredGrupos = computed(() => {
  if (!selectedSedeId.value) return []
  return grupos.value.filter(g => g.sede && g.sede.id === selectedSedeId.value)
})

// -----------------------------------------------------------------------
// Custom date picker (Día / Mes / Año)
// -----------------------------------------------------------------------
const MESES = [
  { val: '01', label: 'Enero' }, { val: '02', label: 'Febrero' },
  { val: '03', label: 'Marzo' }, { val: '04', label: 'Abril' },
  { val: '05', label: 'Mayo' }, { val: '06', label: 'Junio' },
  { val: '07', label: 'Julio' }, { val: '08', label: 'Agosto' },
  { val: '09', label: 'Septiembre' }, { val: '10', label: 'Octubre' },
  { val: '11', label: 'Noviembre' }, { val: '12', label: 'Diciembre' },
]
const birthDay   = ref<string>('')
const birthMonth = ref<string>('')
const birthYear  = ref<string>('')

// Años válidos: nacidos entre 1990 y hace 2 años
const birthYears = computed(() => {
  const end = new Date().getFullYear() - 2
  const years: number[] = []
  for (let y = end; y >= 1990; y--) years.push(y)
  return years
})

// Días del mes seleccionado
const birthDays = computed(() => {
  const m = parseInt(birthMonth.value || '1')
  const y = parseInt(birthYear.value  || '2000')
  const max = new Date(y, m, 0).getDate()
  return Array.from({ length: max }, (_, i) => String(i + 1).padStart(2, '0'))
})

// Cuando cambia alguno de los tres selects, actualizar el modelo
watch([birthDay, birthMonth, birthYear], ([d, m, y]) => {
  if (d && m && y) {
    studentsStore.draft.general.fecha_nacimiento = `${y}-${m}-${d}`
  } else {
    studentsStore.draft.general.fecha_nacimiento = ''
  }
})

// Si ya hay una fecha en el store (modo edición), descomponer
watch(
  () => studentsStore.draft.general.fecha_nacimiento,
  (val) => {
    if (val && val.length === 10 && !birthYear.value) {
      const parts = val.split('-')
      birthYear.value  = parts[0] ?? ''
      birthMonth.value = parts[1] ?? ''
      birthDay.value   = parts[2] ?? ''
    }
  },
  { immediate: true }
)

// -----------------------------------------------------------------------
// Departamentos / Municipios — datos estáticos DANE (sin API externa)
// -----------------------------------------------------------------------
const departamentos = DEPARTAMENTOS.slice().sort((a, b) => a.nombre.localeCompare(b.nombre))
const municipios      = ref<{ id: string; nombre: string }[]>([])
const loadingMunicipios = ref(false)
const selectedDeptoId = ref<string>('')

const cargarMunicipios = (deptoId: string) => {
  if (!deptoId) { municipios.value = []; return }
  const depto = DEPARTAMENTOS.find(d => d.id === deptoId)
  municipios.value = depto
    ? depto.municipios.slice().sort((a, b) => a.nombre.localeCompare(b.nombre))
    : []
}

// Al cambiar departamento, actualizar municipio y el nombre en el store
watch(selectedDeptoId, (newId) => {
  studentsStore.draft.general.municipio_residencia = ''
  const depto = DEPARTAMENTOS.find(d => d.id === newId)
  studentsStore.draft.general.departamento_residencia = depto ? depto.nombre : ''
  cargarMunicipios(newId)
})

const fetchSedesAndGrupos = async () => {
  loadingSedesGrupos.value = true
  try {
    const headers = { 'Authorization': `Bearer ${authStore.token}` }
    const [resSedes, resGrupos] = await Promise.all([
      fetch('/api/v1/gestion/sedes', { headers }),
      fetch('/api/v1/gestion/grupos', { headers })
    ])
    if (resSedes.ok) sedes.value = await resSedes.json()
    if (resGrupos.ok) grupos.value = await resGrupos.json()
    
    // Si estamos editando y el estudiante ya tiene un grupo_id, pre-seleccionar la sede
    if (studentsStore.draft.general.grupo_id) {
      const grupo = grupos.value.find(g => g.id === studentsStore.draft.general.grupo_id)
      if (grupo && grupo.sede) {
        selectedSedeId.value = grupo.sede.id
      }
    }
  } catch (e) {
    console.error('Error cargando sedes/grupos:', e)
  } finally {
    loadingSedesGrupos.value = false
  }
}

// Load data on mount
onMounted(async () => {
  // Enforzar permisos
  if (!authStore.canCreateStudent) {
    router.push('/estudiantes')
    return
  }

  const studentId = route.params.id as string
  if (studentId) {
    isEditMode.value = true
    await studentsStore.fetchStudentForEdit(studentId)
  } else {
    isEditMode.value = false
    studentsStore.loadDraft()
    // Default system values
    if (!studentsStore.draft.matricula.institucion_educativa && authStore.nombreInstitucion) {
      studentsStore.draft.matricula.institucion_educativa = authStore.nombreInstitucion
    }
  }
  await fetchSedesAndGrupos()

  // Si en modo edición ya hay depto guardado, pre-seleccionar y restaurar municipio
  if (studentsStore.draft.general.departamento_residencia) {
    const deptoName = studentsStore.draft.general.departamento_residencia
    // Guardar el municipio ANTES de que el watch lo borre al cambiar selectedDeptoId
    const savedMunicipio = studentsStore.draft.general.municipio_residencia
    const depto = DEPARTAMENTOS.find(d =>
      d.nombre.toLowerCase() === deptoName.toLowerCase()
    )
    if (depto) {
      selectedDeptoId.value = depto.id
      cargarMunicipios(depto.id)
      // El watch borra municipio_residencia al dispararse; restaurarlo en el siguiente tick
      await nextTick()
      studentsStore.draft.general.municipio_residencia = savedMunicipio
    }
  }
})

// Sincronizar Sede seleccionada con texto del Anexo 1
watch(selectedSedeId, (newSedeId) => {
  const selectedGrupo = grupos.value.find(g => g.id === studentsStore.draft.general.grupo_id)
  if (selectedGrupo && selectedGrupo.sede.id !== newSedeId) {
    studentsStore.draft.general.grupo_id = null
  }
  const sedeObj = sedes.value.find(s => s.id === newSedeId)
  if (sedeObj) {
    studentsStore.draft.matricula.sede = sedeObj.nombre
  } else {
    studentsStore.draft.matricula.sede = ''
  }
})

// Sincronizar Grupo seleccionado con grado de ingreso del Anexo 1
watch(() => studentsStore.draft.general.grupo_id, (newGrupoId) => {
  if (newGrupoId) {
    const grupoObj = grupos.value.find(g => g.id === newGrupoId)
    if (grupoObj) {
      studentsStore.draft.matricula.grado_ingreso = `${grupoObj.grado} - ${grupoObj.nombre}`
    }
  } else {
    studentsStore.draft.matricula.grado_ingreso = ''
  }
})

// Auto-save draft on changes (de-bounced via watcher)
let debounceTimeout: any = null
const saveDraft = () => {
  if (debounceTimeout) clearTimeout(debounceTimeout)
  debounceTimeout = setTimeout(() => {
    if (!isEditMode.value) {
      studentsStore.saveDraft()
    }
  }, 1000)
}

// Watch draft to trigger saveDraft
watch(() => studentsStore.draft, () => {
  saveDraft()
}, { deep: true })

// Age auto-calculator from birthdate
watch(() => studentsStore.draft.general.fecha_nacimiento, (newDate) => {
  if (!newDate) return
  try {
    const today = new Date()
    const birthDate = new Date(newDate)
    let age = today.getFullYear() - birthDate.getFullYear()
    const m = today.getMonth() - birthDate.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--
    }
    if (age >= 0 && age <= 30) {
      studentsStore.draft.general.edad = age
    }
  } catch (e) {
    console.error('Error calculando edad:', e)
  }
})

// Add/Remove therapies details dynamically
const addTerapia = () => {
  studentsStore.draft.salud.terapias_detalle.push({ tipo: '', frecuencia: '' })
}

const removeTerapia = (index: number) => {
  studentsStore.draft.salud.terapias_detalle.splice(index, 1)
}

// Stepper Validation
const validateStep = (step: number): boolean => {
  validationError.value = null
  const gen = studentsStore.draft.general

  if (step === 1) {
    if (!gen.nombres || !gen.apellidos) {
      validationError.value = 'Completa los nombres y apellidos del estudiante.'
      return false
    }
    if (!gen.tipo_documento || !gen.numero_documento) {
      validationError.value = 'Completa el tipo y número de documento de identidad.'
      return false
    }
    if (!gen.fecha_nacimiento || gen.edad < 0 || gen.edad > 30) {
      validationError.value = 'Ingresa una fecha de nacimiento válida (edad máx: 30 años).'
      return false
    }
    if (!gen.departamento_residencia || !gen.municipio_residencia) {
      validationError.value = 'El departamento y el municipio son obligatorios.'
      return false
    }
    if (!gen.direccion || !gen.barrio_vereda) {
      validationError.value = 'Ingresa la dirección y barrio o vereda de residencia.'
      return false
    }
  }

  if (step === 2) {
    const salud = studentsStore.draft.salud
    if (salud.afiliacion_salud && (!salud.eps || !salud.regimen)) {
      validationError.value = 'Si cuenta con afiliación de salud, completa la EPS y el régimen.'
      return false
    }
    if (salud.tiene_diagnostico_medico && !salud.diagnostico_medico) {
      validationError.value = 'Si tiene diagnóstico médico, ingresa los detalles del diagnóstico.'
      return false
    }
    if (salud.asiste_terapias && salud.terapias_detalle.length === 0) {
      validationError.value = 'Si asiste a terapias, añade al menos una terapia.'
      return false
    }
    if (salud.asiste_terapias) {
      for (const t of salud.terapias_detalle) {
        if (!t.tipo || !t.frecuencia) {
          validationError.value = 'Completa el tipo y frecuencia de todas las terapias añadidas.'
          return false
        }
      }
    }
    if (salud.tratamiento_medico && !salud.tratamiento_medico_cual) {
      validationError.value = 'Ingresa los detalles del tratamiento médico.'
      return false
    }
    if (salud.consume_medicamentos && !salud.medicamentos_detalle) {
      validationError.value = 'Ingresa los detalles del consumo de medicamentos (frecuencia/horarios).'
      return false
    }
    if (salud.productos_apoyo_movilidad && !salud.productos_apoyo_cual) {
      validationError.value = 'Detalla los productos de apoyo (silla de ruedas, audífonos, etc.).'
      return false
    }
  }

  if (step === 3) {
    const hogar = studentsStore.draft.hogar
    if (hogar.bajo_proteccion && !hogar.personas_vive_estudiante) {
      validationError.value = 'Describe con quiénes vive el estudiante.'
      return false
    }
    if (hogar.recibe_subsidio && !hogar.subsidio_cual) {
      validationError.value = 'Especifica qué subsidio recibe la familia.'
      return false
    }
  }

  if (step === 4) {
    const mat = studentsStore.draft.matricula
    if (!mat.institucion_educativa || !mat.sede || !mat.grado_ingreso || !mat.jornada) {
      validationError.value = 'Completa todos los campos obligatorios de la matrícula actual (IE, Sede, Grado y Jornada).'
      return false
    }
  }

  return true
}

// Navigation Actions
const nextStep = () => {
  if (validateStep(currentStep.value)) {
    if (currentStep.value < 4) {
      currentStep.value++
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const goToStep = (step: number) => {
  // Solo permitir saltar a pasos anteriores o al paso inmediatamente siguiente si el actual es válido
  if (step < currentStep.value) {
    currentStep.value = step
  } else if (step === currentStep.value + 1 && validateStep(currentStep.value)) {
    currentStep.value = step
  }
}

const cancel = () => {
  studentsStore.clearDraft()
  router.push('/estudiantes')
}

const save = async () => {
  // Auto-asignar la institucion educativa asociada al usuario que crea el estudiante
  if (authStore.nombreInstitucion) {
    studentsStore.draft.matricula.institucion_educativa = authStore.nombreInstitucion
  }
  if (!validateStep(4)) return

  const studentId = route.params.id as string
  const success = await studentsStore.saveStudent(studentId, medicalSupportFile.value)

  if (success) {
    router.push('/estudiantes')
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
          <span class="material-symbols-outlined text-primary text-[28px]">assignment_ind</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">
            {{ isEditMode ? 'Editar' : 'Registrar' }} Registro Pedagógico — Anexo 1
          </h2>
        </div>
        <div class="flex items-center gap-xs">
          <button
            @click="cancel"
            class="px-lg py-3 border border-error/30 text-error hover:bg-error/5 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer transition-all active:scale-95"
          >
            <span class="material-symbols-outlined text-[18px]">close</span>
            Cancelar
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="p-gutter max-w-4xl mx-auto w-full space-y-gutter flex-grow">
        <!-- Visual Stepper Progress Bar -->
        <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl p-md shadow-sm flex justify-between items-center select-none transition-colors duration-300">
          <div
            v-for="step in 4"
            :key="step"
            @click="goToStep(step)"
            class="flex-1 flex flex-col items-center gap-xs cursor-pointer relative"
            :class="{ 'pointer-events-none': step > currentStep + 1 }"
          >
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-label-md transition-all duration-300"
              :class="
                step === currentStep
                  ? 'bg-primary text-white scale-110 shadow-md shadow-primary/20'
                  : step < currentStep
                  ? 'bg-tertiary text-on-tertiary'
                  : 'bg-surface-container-high text-outline'
              "
            >
              <span v-if="step < currentStep" class="material-symbols-outlined text-[18px]">check</span>
              <span v-else>{{ step }}</span>
            </div>
            <span
              class="text-label-sm font-bold transition-colors"
              :class="step === currentStep ? 'text-primary' : 'text-outline'"
            >
              {{ step === 1 ? 'General' : step === 2 ? 'Salud' : step === 3 ? 'Hogar' : 'Trayectoria' }}
            </span>
          </div>
        </div>

        <!-- Validation Alert -->
        <div v-if="validationError" class="p-sm bg-error-container text-on-error-container rounded-xl text-body-md border border-error/20 flex gap-xs items-start">
          <span class="material-symbols-outlined text-error">error</span>
          <span>{{ validationError }}</span>
        </div>

        <!-- Form Cards by Step -->
        <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl p-md md:p-xl shadow-sm space-y-md transition-colors duration-300">
          
          <!-- STEP 1: INFORMACIÓN GENERAL -->
          <div v-if="currentStep === 1" class="space-y-md">
            <h3 class="font-headline-md text-[18px] text-primary border-b border-outline-variant/30 pb-sm">1. Información General del Estudiante</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nombres *</label>
                <input
                  v-model="studentsStore.draft.general.nombres"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                  type="text"
                  placeholder="Nombres completos"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Apellidos *</label>
                <input
                  v-model="studentsStore.draft.general.apellidos"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                  type="text"
                  placeholder="Apellidos completos"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Tipo Documento *</label>
                <div class="relative">
                  <select
                    v-model="studentsStore.draft.general.tipo_documento"
                    class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                  >
                    <option value="RC">Registro Civil (RC)</option>
                    <option value="TI">Tarjeta de Identidad (TI)</option>
                    <option value="CC">Cédula de Ciudadanía (CC)</option>
                    <option value="NES">Número Establecido por Secretaría (NES)</option>
                    <option value="PEP">Permiso Especial de Permanencia (PEP)</option>
                  </select>
                  <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="6 9 12 15 18 9"/>
                    </svg>
                  </span>
                </div>
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Número Documento *</label>
                <input
                  v-model="studentsStore.draft.general.numero_documento"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                  type="text"
                  placeholder="Número de identidad"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Fecha de Nacimiento *</label>
                <div class="grid grid-cols-3 gap-2">
                  <!-- Día -->
                  <div class="relative">
                    <select
                      v-model="birthDay"
                      class="w-full px-3 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Día</option>
                      <option v-for="d in birthDays" :key="d" :value="d">{{ parseInt(d) }}</option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-2 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                  <!-- Mes -->
                  <div class="relative">
                    <select
                      v-model="birthMonth"
                      class="w-full px-3 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Mes</option>
                      <option v-for="m in MESES" :key="m.val" :value="m.val">{{ m.label }}</option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-2 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                  <!-- Año -->
                  <div class="relative">
                    <select
                      v-model="birthYear"
                      class="w-full px-3 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Año</option>
                      <option v-for="y in birthYears" :key="y" :value="String(y)">{{ y }}</option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-2 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Edad Calculada</label>
                <input
                  v-model.number="studentsStore.draft.general.edad"
                  readonly
                  class="w-full px-4 py-3 bg-surface-container border border-outline-variant/50 rounded-input font-body-md text-outline cursor-not-allowed dark:text-white"
                  type="number"
                />
              </div>
              <div class="space-y-xs md:col-span-3">
                <label class="font-label-md text-label-md text-on-surface-variant">Lugar de Nacimiento</label>
                <input
                  v-model="studentsStore.draft.general.lugar_nacimiento"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Municipio, Departamento / País"
                />
              </div>
            </div>

            <h4 class="font-bold text-label-sm text-outline tracking-wide pt-sm">DIRECCIÓN Y CONTACTO</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <!-- Departamento -->
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Departamento de Residencia *</label>
                <div class="relative">
                  <select
                    v-model="selectedDeptoId"
                    class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                  >
                    <option value="" disabled>Selecciona un departamento</option>
                    <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                  </select>
                  <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                </div>
              </div>
              <!-- Municipio -->
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Municipio de Residencia *</label>
                <div class="relative">
                  <select
                    v-model="studentsStore.draft.general.municipio_residencia"
                    :disabled="!selectedDeptoId"
                    class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="" disabled>
                      {{ !selectedDeptoId ? 'Primero selecciona un departamento' : 'Selecciona un municipio' }}
                    </option>
                    <option v-for="m in municipios" :key="m.id" :value="m.nombre">{{ m.nombre }}</option>
                  </select>
                  <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Dirección Física *</label>
                <input
                  v-model="studentsStore.draft.general.direccion"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Calle / Carrera / Avenida..."
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Barrio / Vereda *</label>
                <input
                  v-model="studentsStore.draft.general.barrio_vereda"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Teléfono de Contacto</label>
                <input
                  v-model="studentsStore.draft.general.telefono"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="tel"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Correo Electrónico</label>
                <input
                  v-model="studentsStore.draft.general.correo"
                  class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="email"
                />
              </div>
            </div>

            <h4 class="font-bold text-label-sm text-outline tracking-wide pt-sm">CONDICIONES PARTICULARES</h4>
            <div class="space-y-sm bg-surface-container-low p-md rounded-xl border border-outline-variant/20">
              <div class="flex items-center gap-xs">
                <input
                  id="conflicto"
                  v-model="studentsStore.draft.general.victima_conflicto"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="conflicto" class="font-label-md text-label-md text-on-surface select-none">¿Es víctima del conflicto armado?</label>
              </div>

              <div v-if="studentsStore.draft.general.victima_conflicto" class="flex items-center gap-xs pl-6">
                <input
                  id="registro-victima"
                  v-model="studentsStore.draft.general.registro_victima"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="registro-victima" class="font-label-md text-label-md text-on-surface select-none">¿Cuenta con Registro Único de Víctimas (RUV)?</label>
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="proteccion"
                  v-model="studentsStore.draft.general.en_centro_proteccion"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="proteccion" class="font-label-md text-label-md text-on-surface select-none">¿Está bajo un centro de protección (ICBF/Fundación)?</label>
              </div>

              <div v-if="studentsStore.draft.general.en_centro_proteccion" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">¿En dónde?</label>
                <input
                  v-model="studentsStore.draft.general.centro_proteccion_donde"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Nombre de la institución"
                />
              </div>

              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Pertenencia a Grupo Étnico</label>
                <input
                  v-model="studentsStore.draft.general.grupo_etnico"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Ej: Indígena (especificar resguardo), Afrocolombiano, Raizal, Rom o NULL"
                />
              </div>
            </div>
          </div>

          <!-- STEP 2: ENTORNO SALUD -->
          <div v-if="currentStep === 2" class="space-y-md">
            <h3 class="font-headline-md text-[18px] text-primary border-b border-outline-variant/30 pb-sm">2. Entorno Salud</h3>

            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="afiliacion-salud"
                  v-model="studentsStore.draft.salud.afiliacion_salud"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="afiliacion-salud" class="font-label-md text-label-md text-on-surface select-none">¿Está afiliado al sistema de salud (SGSSS)?</label>
              </div>

              <div v-if="studentsStore.draft.salud.afiliacion_salud" class="grid grid-cols-1 md:grid-cols-2 gap-md pl-6">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">EPS *</label>
                  <input
                    v-model="studentsStore.draft.salud.eps"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                  />
                </div>
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Régimen *</label>
                  <div class="relative">
                    <select
                      v-model="studentsStore.draft.salud.regimen"
                      class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Selecciona régimen...</option>
                      <option value="contributivo">Contributivo</option>
                      <option value="subsidiado">Subsidiado</option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                </div>
              </div>

              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Lugar de Emergencias</label>
                <input
                  v-model="studentsStore.draft.salud.lugar_emergencias"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="IPS o clínica de atención prioritaria"
                />
              </div>
            </div>

            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="atendido-salud"
                  v-model="studentsStore.draft.salud.atendido_sector_salud"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="atendido-salud" class="font-label-md text-label-md text-on-surface select-none">¿Es atendido periódicamente por salud especial?</label>
              </div>

              <div v-if="studentsStore.draft.salud.atendido_sector_salud" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">Frecuencia de Atención</label>
                <input
                  v-model="studentsStore.draft.salud.frecuencia_atencion_salud"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Ej: Mensual, Trimestral"
                />
              </div>
            </div>

            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="tiene-diagnostico"
                  v-model="studentsStore.draft.salud.tiene_diagnostico_medico"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="tiene-diagnostico" class="font-label-md text-label-md text-on-surface select-none">¿Tiene un diagnóstico médico acreditado? *</label>
              </div>

              <div v-if="studentsStore.draft.salud.tiene_diagnostico_medico" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">Diagnóstico Médico (e.g. Autismo, TDAH, Discapacidad Auditiva) *</label>
                <textarea
                  v-model="studentsStore.draft.salud.diagnostico_medico"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  rows="2"
                  placeholder="Escribe el diagnóstico tal cual figura en la historia clínica"
                ></textarea>

                <!-- Soporte Médico PDF -->
                <div class="mt-4 space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Soporte Médico del Diagnóstico (PDF)</label>
                  
                  <!-- Caso 1: Ya existe un soporte guardado en el servidor -->
                  <div v-if="studentsStore.draft.salud.soporte_medico_nombre" class="flex items-center justify-between bg-surface border border-outline-variant/30 p-3 rounded-lg">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-red-500">picture_as_pdf</span>
                      <span class="font-body-md text-on-surface font-semibold max-w-[200px] truncate" :title="studentsStore.draft.salud.soporte_medico_nombre">
                        {{ studentsStore.draft.salud.soporte_medico_nombre }}
                      </span>
                    </div>
                    <div class="flex items-center gap-2">
                      <button
                        type="button"
                        @click="downloadMedicalSupport"
                        :disabled="isDownloadingSupport"
                        class="text-primary hover:bg-primary/10 px-3 py-1.5 rounded-lg text-label-sm font-bold flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <span v-if="isDownloadingSupport" class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                        <span v-else class="material-symbols-outlined text-[18px]">visibility</span>
                        Ver / Descargar
                      </button>
                      <button
                        type="button"
                        @click="removeExistingSupport"
                        :disabled="isDeletingSupport"
                        class="text-error hover:bg-error/10 px-3 py-1.5 rounded-lg text-label-sm font-bold flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <span v-if="isDeletingSupport" class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                        <span v-else class="material-symbols-outlined text-[18px]">delete</span>
                        Eliminar
                      </button>
                    </div>
                  </div>

                  <!-- Caso 2: Se seleccionó un nuevo soporte local -->
                  <div v-else-if="medicalSupportFile" class="flex items-center justify-between bg-green-50/50 border border-green-200 p-3 rounded-lg">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-green-600">check_circle</span>
                      <span class="font-body-md text-on-surface font-semibold max-w-[200px] truncate" :title="medicalSupportFile.name">
                        {{ medicalSupportFile.name }}
                      </span>
                      <span class="text-xs text-outline">
                        ({{ (medicalSupportFile.size / 1024).toFixed(1) }} KB)
                      </span>
                    </div>
                    <button
                      type="button"
                      @click="removeExistingSupport"
                      class="text-error hover:bg-error/10 px-3 py-1.5 rounded-lg text-label-sm font-bold flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      <span class="material-symbols-outlined text-[18px]">close</span>
                      Remover
                    </button>
                  </div>

                  <!-- Caso 3: No hay soporte cargado ni seleccionado -->
                  <div
                    v-else
                    @click="triggerSupportFileSelect"
                    class="border-2 border-dashed border-outline-variant/60 rounded-xl p-6 text-center cursor-pointer hover:border-primary/60 transition-all bg-surface/50 flex flex-col items-center justify-center gap-1"
                  >
                    <input
                      ref="supportInputRef"
                      type="file"
                      accept=".pdf"
                      @change="onSupportFileChange"
                      style="display: none;"
                    />
                    <span class="material-symbols-outlined text-outline text-[28px]">picture_as_pdf</span>
                    <span class="font-label-sm text-outline font-semibold">Haz clic para adjuntar el dictamen/soporte PDF</span>
                    <span class="text-[11px] text-outline">Solo archivos PDF (Max. 10MB)</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="asiste-terapias"
                  v-model="studentsStore.draft.salud.asiste_terapias"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="asiste-terapias" class="font-label-md text-label-md text-on-surface select-none">¿Asiste a terapias extracurriculares? *</label>
              </div>

              <div v-if="studentsStore.draft.salud.asiste_terapias" class="space-y-sm pl-6">
                <div class="flex justify-between items-center">
                  <h4 class="font-bold text-label-sm text-outline">Listado de Terapias</h4>
                  <button
                    type="button"
                    @click="addTerapia"
                    class="bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-lg text-label-sm font-bold flex items-center gap-1 cursor-pointer"
                  >
                    <span class="material-symbols-outlined text-[16px]">add</span>
                    Añadir Terapia
                  </button>
                </div>

                <div v-for="(terapia, idx) in studentsStore.draft.salud.terapias_detalle" :key="idx" class="flex items-center gap-sm bg-surface p-sm border border-outline-variant/30 rounded-input">
                  <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-sm">
                    <input
                      v-model="terapia.tipo"
                      class="px-3 py-2 bg-surface-container border border-outline-variant rounded-input font-body-md text-label-sm focus:border-primary focus:outline-none dark:text-white"
                      placeholder="Tipo (Física, Ocupacional, etc.)"
                    />
                    <input
                      v-model="terapia.frecuencia"
                      class="px-3 py-2 bg-surface-container border border-outline-variant rounded-input font-body-md text-label-sm focus:border-primary focus:outline-none dark:text-white"
                      placeholder="Frecuencia (Semanal, Quincenal)"
                    />
                  </div>
                  <button
                    type="button"
                    @click="removeTerapia(idx)"
                    class="text-error hover:bg-error/10 p-1.5 rounded-full cursor-pointer transition-all"
                  >
                    <span class="material-symbols-outlined text-[20px]">delete</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="tratamiento-medico"
                  v-model="studentsStore.draft.salud.tratamiento_medico"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="tratamiento-medico" class="font-label-md text-label-md text-on-surface select-none">¿Recibe algún otro tratamiento médico particular? *</label>
              </div>

              <div v-if="studentsStore.draft.salud.tratamiento_medico" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">¿Cuál? *</label>
                <input
                  v-model="studentsStore.draft.salud.tratamiento_medico_cual"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="medicamentos"
                  v-model="studentsStore.draft.salud.consume_medicamentos"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="medicamentos" class="font-label-md text-label-md text-on-surface select-none">¿Consume medicamentos de control en horario escolar? *</label>
              </div>

              <div v-if="studentsStore.draft.salud.consume_medicamentos" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">Medicamentos (Nombre, dosis, horario escolar) *</label>
                <textarea
                  v-model="studentsStore.draft.salud.medicamentos_detalle"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  rows="2"
                  placeholder="Dosis e instrucciones para el docente"
                ></textarea>
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="productos-apoyo"
                  v-model="studentsStore.draft.salud.productos_apoyo_movilidad"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="productos-apoyo" class="font-label-md text-label-md text-on-surface select-none">¿Requiere productos de apoyo para la movilidad/comunicación? *</label>
              </div>

              <div v-if="studentsStore.draft.salud.productos_apoyo_movilidad" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">¿Cuáles? (ej: Silla de ruedas, bastón, audífonos, pictogramas) *</label>
                <input
                  v-model="studentsStore.draft.salud.productos_apoyo_cual"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
            </div>
          </div>

          <!-- STEP 3: ENTORNO HOGAR -->
          <div v-if="currentStep === 3" class="space-y-md">
            <h3 class="font-headline-md text-[18px] text-primary border-b border-outline-variant/30 pb-sm">3. Entorno Hogar y Conformación Familiar</h3>

            <h4 class="font-bold text-label-sm text-outline tracking-wide">INFORMACIÓN DE LOS PADRES</h4>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nombre de la Madre</label>
                <input
                  v-model="studentsStore.draft.hogar.nombre_madre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Ocupación Madre</label>
                <input
                  v-model="studentsStore.draft.hogar.ocupacion_madre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nivel Educativo Madre</label>
                <input
                  v-model="studentsStore.draft.hogar.nivel_educativo_madre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Primaria, Bachillerato, Tec..."
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nombre del Padre</label>
                <input
                  v-model="studentsStore.draft.hogar.nombre_padre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Ocupación Padre</label>
                <input
                  v-model="studentsStore.draft.hogar.ocupacion_padre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nivel Educativo Padre</label>
                <input
                  v-model="studentsStore.draft.hogar.nivel_educativo_padre"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
            </div>

            <h4 class="font-bold text-label-sm text-outline tracking-wide pt-sm">CUIDADOR ENCARGADO (SI DIFIERE DE LOS PADRES)</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Nombre del Cuidador</label>
                <input
                  v-model="studentsStore.draft.hogar.nombre_cuidador"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
              <div class="grid grid-cols-2 gap-sm">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Parentesco</label>
                  <input
                    v-model="studentsStore.draft.hogar.parentesco_cuidador"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                    placeholder="Ej: Abuelo, Tío"
                  />
                </div>
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Nivel Educativo</label>
                  <input
                    v-model="studentsStore.draft.hogar.nivel_educativo_cuidador"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                  />
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Teléfono Cuidador</label>
                <input
                  v-model="studentsStore.draft.hogar.telefono_cuidador"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="tel"
                />
              </div>
              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Correo Cuidador</label>
                <input
                  v-model="studentsStore.draft.hogar.correo_cuidador"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="email"
                />
              </div>
            </div>

            <h4 class="font-bold text-label-sm text-outline tracking-wide pt-sm">ENTORNO SOCIAL Y CONVIVENCIA</h4>
            <div class="space-y-md bg-surface-container-low p-md rounded-xl border border-outline-variant/20">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Número de Hermanos</label>
                  <input
                    v-model.number="studentsStore.draft.hogar.numero_hermanos"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="number"
                    min="0"
                  />
                </div>
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Lugar que Ocupa entre hermanos</label>
                  <input
                    v-model.number="studentsStore.draft.hogar.lugar_que_ocupa"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="number"
                    min="1"
                    placeholder="Ej: 1 (Mayor)"
                  />
                </div>
              </div>

              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant font-bold">Personas con las que vive el estudiante *</label>
                <textarea
                  v-model="studentsStore.draft.hogar.personas_vive_estudiante"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  rows="2"
                  placeholder="Detalla si vive con mamá, hermanos, abuelos, etc."
                ></textarea>
              </div>

              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">¿Quiénes apoyan la crianza?</label>
                <input
                  v-model="studentsStore.draft.hogar.apoyo_crianza"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="Mamá y Abuela, etc."
                />
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="proteccion-hogar"
                  v-model="studentsStore.draft.hogar.bajo_proteccion"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="proteccion-hogar" class="font-label-md text-label-md text-on-surface select-none">¿La familia se encuentra bajo medidas especiales de protección?</label>
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="recibe-subsidio"
                  v-model="studentsStore.draft.hogar.recibe_subsidio"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="recibe-subsidio" class="font-label-md text-label-md text-on-surface select-none">¿La familia recibe subsidios o ayudas del gobierno? *</label>
              </div>

              <div v-if="studentsStore.draft.hogar.recibe_subsidio" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">¿Cuál subsidio? (ej: Familias en Acción, Ingreso Solidario) *</label>
                <input
                  v-model="studentsStore.draft.hogar.subsidio_cual"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
            </div>
          </div>

          <!-- STEP 4: TRAYECTORIA Y MATRÍCULA -->
          <div v-if="currentStep === 4" class="space-y-md">
            <h3 class="font-headline-md text-[18px] text-primary border-b border-outline-variant/30 pb-sm">4. Trayectoria Educativa e Institución Actual</h3>

            <h4 class="font-bold text-label-sm text-outline tracking-wide">TRAYECTORIA EDUCATIVA PREVIA</h4>
            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="flex items-center gap-xs">
                <input
                  id="inicial"
                  v-model="studentsStore.draft.trayectoria.vinculado_educacion_inicial"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="inicial" class="font-label-md text-label-md text-on-surface select-none">¿Ha estado vinculado en otra institución educativa, fundación o modalidad de educación inicial?</label>
              </div>

              <div v-if="studentsStore.draft.trayectoria.vinculado_educacion_inicial" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">Instituciones / Modalidades previas</label>
                <input
                  v-model="studentsStore.draft.trayectoria.educacion_inicial_instituciones"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                  placeholder="¿Cuáles?"
                />
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Último grado cursado</label>
                  <input
                    v-model="studentsStore.draft.trayectoria.ultimo_grado_cursado"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                    placeholder="Ej: Transición, Primero"
                  />
                </div>
                <div class="flex items-center gap-xs pt-8">
                  <input
                    id="aprobo"
                    v-model="studentsStore.draft.trayectoria.aprobo_ultimo_grado"
                    type="checkbox"
                    class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                  />
                  <label for="aprobo" class="font-label-md text-label-md text-on-surface select-none">¿Aprobó el último grado cursado?</label>
                </div>
              </div>

              <div class="space-y-xs">
                <label class="font-label-md text-label-md text-on-surface-variant">Observaciones de la trayectoria (deserción, cambios de escuela, motivos)</label>
                <textarea
                  v-model="studentsStore.draft.trayectoria.observaciones_trayectoria"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  rows="2"
                ></textarea>
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="informe-ped"
                  v-model="studentsStore.draft.trayectoria.recibe_informe_pedagogico"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="informe-ped" class="font-label-md text-label-md text-on-surface select-none">¿Se recibe informe pedagógico o PIAR previo de la otra institución?</label>
              </div>

              <div v-if="studentsStore.draft.trayectoria.recibe_informe_pedagogico" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">Institución de procedencia del informe</label>
                <input
                  v-model="studentsStore.draft.trayectoria.institucion_procedencia_informe"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>

              <div class="flex items-center gap-xs">
                <input
                  id="complementarios"
                  v-model="studentsStore.draft.trayectoria.asiste_programas_complementarios"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-outline-variant rounded focus:ring-primary"
                />
                <label for="complementarios" class="font-label-md text-label-md text-on-surface select-none">¿Asiste a programas complementarios (música, deportes, pintura)?</label>
              </div>

              <div v-if="studentsStore.draft.trayectoria.asiste_programas_complementarios" class="space-y-xs pl-6">
                <label class="font-label-md text-label-md text-on-surface-variant">¿Cuáles programas?</label>
                <input
                  v-model="studentsStore.draft.trayectoria.programas_complementarios_cuales"
                  class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                  type="text"
                />
              </div>
            </div>

            <h4 class="font-bold text-label-sm text-outline tracking-wide pt-sm">MATRÍCULA INSTITUCIONAL ACTUAL *</h4>
            <div class="bg-surface-container-low p-md rounded-xl border border-outline-variant/20 space-y-md">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Sede Escolar *</label>
                  <div v-if="sedes.length > 0" class="relative">
                    <select
                      v-model="selectedSedeId"
                      class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Selecciona sede...</option>
                      <option v-for="sede in sedes" :key="sede.id" :value="sede.id">
                        {{ sede.nombre }}
                      </option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                  <input
                    v-else
                    v-model="studentsStore.draft.matricula.sede"
                    class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    type="text"
                    placeholder="Ej: Sede Principal, Sede B"
                  />
                </div>
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Grado al que ingresa *</label>
                  <div v-if="sedes.length > 0 && grupos.length > 0" class="relative">
                    <select
                      v-model="studentsStore.draft.general.grupo_id"
                      :disabled="!selectedSedeId"
                      class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 disabled:opacity-50 disabled:cursor-not-allowed dark:text-white"
                    >
                      <option :value="null" disabled>Selecciona grupo...</option>
                      <option v-for="grupo in filteredGrupos" :key="grupo.id" :value="grupo.id">
                        {{ grupo.grado }} - {{ grupo.nombre }}
                      </option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                  <input
                    v-else
                    v-model="studentsStore.draft.matricula.grado_ingreso"
                    class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    type="text"
                    placeholder="Ej: Primero, Cuarto"
                  />
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Jornada Escolar *</label>
                  <div class="relative">
                    <select
                      v-model="studentsStore.draft.matricula.jornada"
                      class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md appearance-none cursor-pointer focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
                    >
                      <option value="" disabled>Selecciona jornada...</option>
                      <option value="mañana">Mañana</option>
                      <option value="tarde">Tarde</option>
                      <option value="unica">Única</option>
                      <option value="nocturna">Nocturna</option>
                    </select>
                    <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-outline">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </div>
                </div>
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Medio de transporte al colegio</label>
                  <input
                    v-model="studentsStore.draft.matricula.medio_transporte"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                    placeholder="Ej: Caminando, Ruta, Moto"
                  />
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
                <div class="space-y-xs">
                  <label class="font-label-md text-label-md text-on-surface-variant">Distancia / Tiempo desde el hogar</label>
                  <input
                    v-model="studentsStore.draft.matricula.distancia_tiempo_hogar"
                    class="w-full px-4 py-2.5 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none dark:text-white"
                    type="text"
                    placeholder="Ej: 15 minutos, 2 km"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Navigation Controls -->
          <div class="pt-md border-t border-outline-variant/30 flex justify-between gap-sm">
            <button
              v-if="currentStep > 1"
              @click="prevStep"
              class="px-lg py-3 bg-surface border border-outline-variant hover:bg-surface-container-low rounded-input font-label-md text-label-md flex items-center gap-xs cursor-pointer transition-all active:scale-95"
              type="button"
            >
              <span class="material-symbols-outlined text-[18px]">arrow_back</span>
              Anterior
            </button>
            <div v-else></div>

            <div class="flex items-center gap-sm">
              <button
                v-if="currentStep < 4"
                @click="nextStep"
                class="px-lg py-3 bg-primary hover:bg-primary-container text-white font-label-md text-label-md rounded-input shadow-md flex items-center gap-xs cursor-pointer transition-all active:scale-95"
                type="button"
              >
                Siguiente
                <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
              </button>
              <button
                v-else
                @click="save"
                :disabled="studentsStore.submitting"
                class="px-lg py-3 bg-green-700 hover:bg-green-800 text-white font-label-md text-label-md rounded-input shadow-md flex items-center justify-center gap-xs cursor-pointer disabled:opacity-75 disabled:pointer-events-none transition-all"
                type="button"
              >
                <template v-if="studentsStore.submitting">
                  <span class="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
                  Guardando Expediente...
                </template>
                <template v-else>
                  Guardar Registro
                  <span class="material-symbols-outlined text-[20px]">cloud_upload</span>
                </template>
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
input[type="checkbox"] {
  accent-color: var(--color-primary);
  width: 18px;
  height: 18px;
  cursor: pointer;
}
</style>
