<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isDarkMode = ref(false)
const showPasswordModal = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const modalError = ref<string | null>(null)
const modalSuccess = ref<string | null>(null)
const modalSubmitting = ref(false)

const hasMinLength = computed(() => newPassword.value.length >= 8)
const hasLetter = computed(() => /[A-Za-z]/.test(newPassword.value))
const hasNumber = computed(() => /\d/.test(newPassword.value))
const hasSpecialChar = computed(() => /[^A-Za-z0-9]/.test(newPassword.value))
const passwordIsValid = computed(() => hasMinLength.value && hasLetter.value && hasNumber.value && hasSpecialChar.value)
const passwordsMatch = computed(() => newPassword.value === confirmPassword.value)

onMounted(() => {
  isDarkMode.value = document.documentElement.classList.contains('dark')
})

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

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const closeModal = () => {
  showPasswordModal.value = false
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  modalError.value = null
  modalSuccess.value = null
}

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
    if (!response.ok) throw new Error(data.detail || 'Error al cambiar la contraseña.')
    modalSuccess.value = 'Contraseña actualizada correctamente.'
    setTimeout(() => closeModal(), 2000)
  } catch (err: any) {
    modalError.value = err.message || 'Error en la petición de cambio de contraseña.'
  } finally {
    modalSubmitting.value = false
  }
}
</script>

<template>
  <header
    class="h-20 w-full sticky top-0 z-30 bg-background/85 backdrop-blur-md flex justify-between items-center px-gutter border-b border-outline-variant/30 transition-colors duration-300"
  >
    <!-- Top bar actions & profile -->
    <div class="flex items-center gap-6 ml-auto">
      <!-- Offline Indicator -->
      <div class="flex items-center bg-orange-100 dark:bg-orange-950/40 px-4 py-1.5 rounded-full border border-orange-200 dark:border-orange-900/30">
        <span class="w-2 h-2 rounded-full bg-orange-500 animate-pulse mr-2"></span>
        <span class="text-orange-700 dark:text-orange-400 font-label-md text-label-sm">Modo offline</span>
      </div>

      <!-- Theme Toggle -->
      <div class="flex items-center bg-surface-container-low p-1 rounded-full border border-outline-variant/30">
        <button
          @click="toggleTheme(false)"
          class="p-2 rounded-full flex items-center justify-center transition-all cursor-pointer"
          :class="!isDarkMode ? 'bg-white dark:bg-zinc-800 shadow-sm text-primary' : 'text-on-surface-variant hover:bg-surface-container'"
          title="Modo claro"
        >
          <span class="material-symbols-outlined text-[18px]">light_mode</span>
        </button>
        <button
          @click="toggleTheme(true)"
          class="p-2 rounded-full flex items-center justify-center transition-all cursor-pointer"
          :class="isDarkMode ? 'bg-zinc-800 shadow-sm text-primary' : 'text-on-surface-variant hover:bg-surface-container'"
          title="Modo oscuro"
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
        <div class="w-10 h-10 rounded-full border-2 border-primary-container p-0.5 cursor-pointer group-hover:border-primary transition-all">
          <div class="w-full h-full bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-headline-md">
            {{ authStore.user?.nombre ? authStore.user.nombre.substring(0, 1).toUpperCase() : 'U' }}
          </div>
        </div>
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
              Cambiar contraseña
            </button>
            <button
              @click="handleLogout"
              class="w-full flex items-center gap-xs px-sm py-2 hover:bg-error/5 text-error rounded-md font-label-md text-label-sm transition-all text-left cursor-pointer"
            >
              <span class="material-symbols-outlined text-[18px]">logout</span>
              Cerrar sesión
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Change Password Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="showPasswordModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
        style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
        @click.self="closeModal"
      >
        <div class="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl w-full max-w-md p-8">
          <h3 class="text-headline-md font-bold text-on-surface mb-6">Cambiar contraseña</h3>
          
          <div v-if="modalError" class="bg-error-container text-on-error-container p-3 rounded-xl text-body-sm mb-4">
            {{ modalError }}
          </div>
          <div v-if="modalSuccess" class="bg-[#caead6] text-[#042014] p-3 rounded-xl text-body-sm mb-4">
            {{ modalSuccess }}
          </div>

          <div class="space-y-4">
            <div class="flex flex-col gap-1">
              <label class="font-label-md text-label-sm text-on-surface-variant">Contraseña actual</label>
              <input
                v-model="currentPassword"
                type="password"
                class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="font-label-md text-label-sm text-on-surface-variant">Nueva contraseña</label>
              <input
                v-model="newPassword"
                type="password"
                class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all"
              />
              <div class="flex flex-wrap gap-2 mt-1">
                <span :class="hasMinLength ? 'text-green-600' : 'text-red-400'" class="text-xs">8+ caracteres</span>
                <span :class="hasLetter ? 'text-green-600' : 'text-red-400'" class="text-xs">Letras</span>
                <span :class="hasNumber ? 'text-green-600' : 'text-red-400'" class="text-xs">Números</span>
                <span :class="hasSpecialChar ? 'text-green-600' : 'text-red-400'" class="text-xs">Especiales</span>
              </div>
            </div>
            <div class="flex flex-col gap-1">
              <label class="font-label-md text-label-sm text-on-surface-variant">Confirmar contraseña</label>
              <input
                v-model="confirmPassword"
                type="password"
                class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all"
                :class="confirmPassword && !passwordsMatch ? 'border-error' : ''"
              />
              <span v-if="confirmPassword && !passwordsMatch" class="text-error text-xs">No coinciden</span>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-outline-variant/30">
            <button
              @click="closeModal"
              class="px-5 py-2.5 text-on-surface-variant font-bold rounded-xl hover:bg-surface-container-low transition-all cursor-pointer"
            >
              Cancelar
            </button>
            <button
              @click="handleChangePassword"
              :disabled="modalSubmitting || modalSuccess !== null"
              class="px-5 py-2.5 bg-primary text-on-primary font-bold rounded-xl hover:opacity-90 disabled:opacity-50 transition-all cursor-pointer"
            >
              {{ modalSubmitting ? 'Cambiando...' : 'Cambiar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
