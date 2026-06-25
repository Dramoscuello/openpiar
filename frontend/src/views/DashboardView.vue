<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// Theme state
const isDarkMode = ref(false)

// Change password modal state
const showPasswordModal = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const modalError = ref<string | null>(null)
const modalSuccess = ref<string | null>(null)
const modalSubmitting = ref(false)

// Password complexity rules
const hasMinLength = computed(() => newPassword.value.length >= 8)
const hasLetter = computed(() => /[A-Za-z]/.test(newPassword.value))
const hasNumber = computed(() => /\d/.test(newPassword.value))
const hasSpecialChar = computed(() => /[^A-Za-z0-9]/.test(newPassword.value))
const passwordIsValid = computed(() => hasMinLength.value && hasLetter.value && hasNumber.value && hasSpecialChar.value)
const passwordsMatch = computed(() => newPassword.value === confirmPassword.value)

onMounted(() => {
  // Inicializar estado del interruptor de Modo Oscuro
  isDarkMode.value = document.documentElement.classList.contains('dark')
})

// Toggle theme function
const toggleTheme = (dark: boolean) => {
  if (dark) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('theme', 'dark')
    isDarkMode.value = true
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
    isDarkMode.value = false
  }
}

// Logout handler
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// Change password submission
const handleChangePassword = async () => {
  if (!currentPassword.value || !newPassword.value) {
    modalError.value = 'Completa los campos de contraseña.'
    return
  }
  
  if (!passwordIsValid.value) {
    modalError.value = 'La nueva contraseña no cumple con los requisitos de seguridad.'
    return
  }

  if (!passwordsMatch.value) {
    modalError.value = 'Las contraseñas no coinciden.'
    return
  }

  modalSubmitting.value = true
  modalError.value = null
  modalSuccess.value = null

  try {
    const response = await fetch('/api/v1/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value,
      }),
    })

    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || 'Error al cambiar la contraseña.')
    }

    modalSuccess.value = 'Contraseña actualizada correctamente.'
    
    // Reset form after delay
    setTimeout(() => {
      closeModal()
    }, 2000)
  } catch (err: any) {
    modalError.value = err.message || 'Error en la petición de cambio de contraseña.'
  } finally {
    modalSubmitting.value = false
  }
}

const closeModal = () => {
  showPasswordModal.value = false
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  modalError.value = null
  modalSuccess.value = null
}
</script>

<template>
  <div class="bg-background text-on-background min-h-screen transition-colors duration-300">
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

      <!-- Sidebar Footer (Support & Configuration) -->
      <div class="mt-auto p-gutter">
        <!-- Support Widget -->
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

    <!-- TopAppBar & Main Content -->
    <main class="ml-64 flex-1 min-h-screen flex flex-col">
      
      <!-- TopAppBar -->
      <header
        class="h-20 w-full sticky top-0 z-30 bg-background/85 backdrop-blur-md flex justify-between items-center px-gutter border-b border-outline-variant/30 transition-colors duration-300"
      >
        <!-- Search bar -->
        <div class="flex-1 max-w-[576px]">
          <div class="relative flex items-center">
            <span class="material-symbols-outlined absolute left-4 text-outline">search</span>
            <input
              class="w-full bg-surface border border-outline-variant rounded-full py-2.5 pl-12 pr-4 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-body-md outline-none focus:outline-none dark:text-white"
              placeholder="Buscar estudiantes..."
              type="text"
            />
          </div>
        </div>

        <!-- Top bar actions & profile -->
        <div class="flex items-center gap-6 ml-gutter">
          <!-- Offline Indicator -->
          <div class="flex items-center bg-orange-100 dark:bg-orange-950/40 px-4 py-1.5 rounded-full border border-orange-200 dark:border-orange-900/30">
            <span class="w-2 h-2 rounded-full bg-orange-500 animate-pulse mr-2"></span>
            <span class="text-orange-700 dark:text-orange-400 font-label-md text-label-sm">Offline Mode</span>
          </div>

          <!-- Theme Toggle -->
          <div class="flex items-center bg-surface-container-low p-1 rounded-full border border-outline-variant/30">
            <button
              @click="toggleTheme(false)"
              class="p-2 rounded-full flex items-center justify-center transition-all cursor-pointer"
              :class="!isDarkMode ? 'bg-white dark:bg-zinc-800 shadow-sm text-primary' : 'text-on-surface-variant hover:bg-surface-container'"
              title="Modo Claro"
            >
              <span class="material-symbols-outlined text-[18px]">light_mode</span>
            </button>
            <button
              @click="toggleTheme(true)"
              class="p-2 rounded-full flex items-center justify-center transition-all cursor-pointer"
              :class="isDarkMode ? 'bg-zinc-800 shadow-sm text-primary' : 'text-on-surface-variant hover:bg-surface-container'"
              title="Modo Oscuro"
            >
              <span class="material-symbols-outlined text-[18px]">dark_mode</span>
            </button>
          </div>

          <!-- Notifications & Status -->
          <div class="flex items-center gap-3">
            <button class="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-full transition-all relative cursor-pointer">
              <span class="material-symbols-outlined">notifications</span>
              <span class="absolute top-2 right-2 w-2 h-2 bg-error rounded-full"></span>
            </button>
            <button class="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-full transition-all cursor-pointer" title="Base de Datos en Sincronía">
              <span class="material-symbols-outlined">cloud_done</span>
            </button>
          </div>

          <div class="h-8 w-px bg-outline-variant/50 mx-1"></div>

          <!-- User Details / Hover Dropdown -->
          <div class="relative group flex items-center gap-3 select-none py-2">
            <!-- Avatar Circle -->
            <div class="w-10 h-10 rounded-full border-2 border-primary-container p-0.5 cursor-pointer group-hover:border-primary transition-all">
              <div class="w-full h-full bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-headline-md">
                {{ authStore.user?.nombre ? authStore.user.nombre.substring(0, 1).toUpperCase() : 'U' }}
              </div>
            </div>
            
            <!-- Hover Dropdown Menu -->
            <div
              class="absolute right-0 top-full mt-1 w-56 bg-surface-container-lowest border border-outline-variant/60 rounded-input shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 text-on-surface"
            >
              <div class="p-sm border-b border-outline-variant/30">
                <p class="font-label-md text-label-md text-on-surface">
                  {{ authStore.user?.nombre }} {{ authStore.user?.apellido }}
                </p>
                <p class="font-label-sm text-label-sm text-on-surface-variant capitalize">
                  {{ authStore.user?.rol.replace('_', ' ') }}
                </p>
              </div>
              <div class="p-xs space-y-xs">
                <button
                  @click="showPasswordModal = true"
                  class="w-full flex items-center gap-xs px-sm py-2 hover:bg-surface-container-low text-on-surface rounded-md font-label-md text-label-sm transition-all text-left cursor-pointer"
                >
                  <span class="material-symbols-outlined text-[18px]">settings</span>
                  Cambiar Contraseña
                </button>
                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-xs px-sm py-2 hover:bg-error/5 text-error rounded-md font-label-md text-label-sm transition-all text-left cursor-pointer"
                >
                  <span class="material-symbols-outlined text-[18px]">logout</span>
                  Cerrar Sesión
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

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
              <h3 class="font-headline-md text-on-surface text-[18px]">Horas de Trabajo</h3>
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
              <h3 class="font-headline-md text-headline-md text-on-surface">Procesos Activos</h3>
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
                <h4 class="font-bold text-on-surface text-body-md mb-2">Reunión Familiar</h4>
                <div class="bg-secondary-container text-on-secondary-container px-3 py-2 rounded-xl text-label-sm inline-flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]">family_restroom</span>
                  Est. Juan Pérez
                </div>
              </div>

              <div class="relative pl-6 border-l-4 border-tertiary-fixed">
                <div class="text-label-sm text-outline mb-1 font-label-sm">03:00 PM - 04:00 PM</div>
                <h4 class="font-bold text-on-surface text-body-md mb-2">Ajustes Matemáticas</h4>
                <div class="bg-tertiary-fixed text-on-tertiary-fixed-variant px-3 py-2 rounded-xl text-label-sm inline-flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]">calculate</span>
                  Grado 4°A
                </div>
              </div>

              <div
                class="p-4 bg-surface-container-low rounded-xl border border-dashed border-outline-variant/60 text-center cursor-pointer hover:bg-surface-container-high transition-all"
              >
                <span class="material-symbols-outlined text-primary mb-1">add_circle</span>
                <p class="text-label-sm font-bold text-primary">Agendar Actividad</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>

    <!-- Change Password Modal Overlay -->
    <div
      v-if="showPasswordModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
    >
      <div class="glass-card max-w-[450px] w-full bg-surface-container-lowest p-xl space-y-md rounded-xxl shadow-xl border border-outline-variant/30 text-on-surface">
        <div class="flex justify-between items-center pb-sm border-b border-outline-variant/30">
          <h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-xs">
            <span class="material-symbols-outlined text-primary">settings</span>
            Cambiar Contraseña
          </h3>
          <button @click="closeModal" class="text-outline hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Success/Error alert inside modal -->
        <div v-if="modalError" class="p-sm bg-error-container text-on-error-container rounded-input text-body-md border border-error/20 flex gap-xs items-start">
          <span class="material-symbols-outlined text-error">error</span>
          <span>{{ modalError }}</span>
        </div>
        <div v-if="modalSuccess" class="p-sm bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 rounded-input text-body-md border border-green-200 dark:border-green-900/30 flex gap-xs items-start">
          <span class="material-symbols-outlined">check_circle</span>
          <span>{{ modalSuccess }}</span>
        </div>

        <form @submit.prevent="handleChangePassword" class="space-y-md">
          <!-- Current Password -->
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant" for="curr-pass">Contraseña Actual</label>
            <input
              id="curr-pass"
              v-model="currentPassword"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
              type="password"
              required
              placeholder="Tu contraseña actual"
            />
          </div>

          <!-- New Password -->
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant" for="new-pass">Nueva Contraseña</label>
            <input
              id="new-pass"
              v-model="newPassword"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
              type="password"
              required
              placeholder="Al menos 8 caracteres"
            />
            
            <!-- Real-time checks -->
            <div class="pt-1 grid grid-cols-2 gap-xs">
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasMinLength ? 'text-green-700 dark:text-green-400' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasMinLength ? 'check_circle' : 'circle' }}</span> Mín. 8 caracteres
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasLetter ? 'text-green-700 dark:text-green-400' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasLetter ? 'check_circle' : 'circle' }}</span> Al menos una letra
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasNumber ? 'text-green-700 dark:text-green-400' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasNumber ? 'check_circle' : 'circle' }}</span> Al menos un número
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasSpecialChar ? 'text-green-700 dark:text-green-400' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ hasSpecialChar ? 'check_circle' : 'circle' }}</span> Un carácter especial
              </span>
            </div>
          </div>

          <!-- Confirm Password -->
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant" for="confirm-pass">Confirmar Nueva Contraseña</label>
            <input
              id="confirm-pass"
              v-model="confirmPassword"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 dark:text-white"
              type="password"
              required
              placeholder="Confirma la contraseña"
            />
            <span v-if="confirmPassword && !passwordsMatch" class="text-error font-label-sm text-label-sm block">
              Las contraseñas no coinciden.
            </span>
          </div>

          <!-- Action Buttons -->
          <div class="pt-md border-t border-outline-variant/30 flex justify-end gap-sm">
            <button
              @click="closeModal"
              class="px-lg py-3 bg-surface border border-outline-variant hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all"
              type="button"
              :disabled="modalSubmitting"
            >
              Cancelar
            </button>
            <button
              class="px-lg py-3 bg-green-700 hover:bg-green-800 text-white font-label-md text-label-md rounded-input shadow-md flex items-center justify-center gap-xs cursor-pointer disabled:opacity-75 disabled:pointer-events-none transition-all"
              type="submit"
              :disabled="modalSubmitting || !passwordIsValid || !passwordsMatch"
            >
              <template v-if="modalSubmitting">
                <span class="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
                Guardando...
              </template>
              <template v-else>
                Actualizar
                <span class="material-symbols-outlined text-[20px]">check_circle</span>
              </template>
            </button>
          </div>
        </form>
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
