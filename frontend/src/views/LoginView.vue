<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// Form refs
const email = ref('')
const password = ref('')
const rememberMe = ref(false)

// UI state
const showPassword = ref(false)
const focusedField = ref<string | null>(null)

// Submit handler
const handleSubmit = async () => {
  if (!email.value || !password.value) return

  const success = await authStore.login(email.value, password.value)
  if (success) {
    router.push('/dashboard')
  }
}

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 md:p-8 bg-[#F8F9FD]">
    <!-- Main Shell -->
    <main
      class="w-full max-w-[1100px] grid grid-cols-1 md:grid-cols-2 glass-card overflow-hidden h-full min-h-[600px] md:min-h-[700px]"
    >
      <!-- Left Panel: Brand & Identity (Hidden on Mobile) -->
      <section class="left-panel-gradient hidden md:flex flex-col justify-center p-xl relative overflow-hidden">
        <div class="relative z-10 space-y-md">
          <!-- Star Brand Logo -->
          <div class="w-16 h-16 bg-white/80 rounded-2xl flex items-center justify-center shadow-sm">
            <span class="material-symbols-outlined text-[48px] star-icon">star</span>
          </div>

          <h1 class="font-headline-lg text-headline-lg text-on-surface leading-tight">
            Simplificando el PIAR con Inteligencia Pedagógica
          </h1>
          
          <p class="font-body-lg text-body-lg text-on-surface-variant max-w-[400px]">
            Optimiza tus procesos de inclusión escolar con herramientas diseñadas para el aula real.
          </p>

          <!-- Animated Feature Badges -->
          <div class="flex flex-col gap-sm pt-md">
            <div class="flex items-center gap-xs">
              <span
                class="px-sm py-xs bg-[#FDF2F8] text-[#9D174D] rounded-full font-label-md text-label-md badge-pulse border border-[#FBCFE8]/50"
              >
                Diseño Universal para el Aprendizaje (DUA)
              </span>
            </div>
            <div class="flex items-center gap-xs">
              <span
                class="px-sm py-xs bg-[#F0FDF4] text-[#166534] rounded-full font-label-md text-label-md badge-pulse border border-[#DCFCE7]/50"
                style="animation-delay: 1s;"
              >
                Integración Curricular MEN
              </span>
            </div>
            <div class="flex items-center gap-xs">
              <span
                class="px-sm py-xs bg-[#EFF6FF] text-[#1E40AF] rounded-full font-label-md text-label-md badge-pulse border border-[#DBEAFE]/50"
                style="animation-delay: 2s;"
              >
                100% Offline-First
              </span>
            </div>
          </div>
        </div>

        <!-- Floating Abstract Element -->
        <div class="absolute -bottom-20 -right-20 w-64 h-64 bg-primary/5 rounded-full blur-3xl"></div>
      </section>

      <!-- Right Panel: Login Form -->
      <section class="bg-surface-container-lowest flex flex-col justify-center p-md md:p-xl">
        <div class="max-w-[400px] mx-auto w-full">
          <!-- Mobile Logo (Hidden on Desktop) -->
          <div class="md:hidden flex items-center gap-xs mb-lg">
            <span class="material-symbols-outlined text-primary text-[32px] star-icon">star</span>
            <span class="font-display text-headline-md text-primary tracking-tight">OpenPiar</span>
          </div>

          <div class="mb-xl">
            <!-- Desktop Logo Header -->
            <div class="hidden md:flex items-center gap-xs mb-sm">
              <span class="material-symbols-outlined text-primary text-[28px] star-icon">star</span>
              <span class="font-display text-headline-md text-primary tracking-tight">OpenPiar</span>
            </div>
            
            <h2 class="font-headline-md text-headline-md text-on-surface">Bienvenido de nuevo</h2>
            <p class="font-body-md text-body-md text-on-surface-variant">
              Ingresa a tu cuenta de docente en {{ authStore.nombreInstitucion }}
            </p>
          </div>

          <!-- API Errors Display -->
          <div
            v-if="authStore.error"
            class="mb-md p-sm bg-error-container text-on-error-container rounded-input border border-error/20 flex gap-xs items-start animate-fade-in"
          >
            <span class="material-symbols-outlined text-error">error</span>
            <div class="text-body-md font-body-md">
              {{ authStore.error }}
            </div>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleSubmit" class="space-y-md">
            <!-- Email Field -->
            <div class="space-y-xs">
              <label
                class="font-label-md text-label-md transition-colors"
                :class="focusedField === 'email' ? 'text-primary' : 'text-on-surface-variant'"
                for="email"
              >
                Correo Electrónico
              </label>
              <div class="relative">
                <span
                  class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 transition-colors duration-200"
                  :class="focusedField === 'email' ? 'text-primary' : 'text-outline-variant'"
                >
                  mail
                </span>
                <input
                  id="email"
                  v-model="email"
                  class="w-full pl-12 pr-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md transition-all placeholder:text-outline-variant focus:border-2 focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                  placeholder="ejemplo@escuela.edu"
                  type="email"
                  required
                  @focus="focusedField = 'email'"
                  @blur="focusedField = null"
                />
              </div>
            </div>

            <!-- Password Field -->
            <div class="space-y-xs">
              <label
                class="font-label-md text-label-md transition-colors"
                :class="focusedField === 'password' ? 'text-primary' : 'text-on-surface-variant'"
                for="password"
              >
                Contraseña
              </label>
              <div class="relative">
                <span
                  class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 transition-colors duration-200"
                  :class="focusedField === 'password' ? 'text-primary' : 'text-outline-variant'"
                >
                  lock
                </span>
                <input
                  id="password"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  class="w-full pl-12 pr-12 py-3 bg-surface border border-outline-variant rounded-input font-body-md transition-all placeholder:text-outline-variant focus:border-2 focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                  placeholder="••••••••"
                  required
                  @focus="focusedField = 'password'"
                  @blur="focusedField = null"
                />
                <!-- Show/Hide password toggle -->
                <button
                  class="absolute right-4 top-1/2 -translate-y-1/2 text-outline-variant hover:text-primary transition-colors cursor-pointer"
                  type="button"
                  @click="togglePasswordVisibility"
                >
                  <span class="material-symbols-outlined">
                    {{ showPassword ? 'visibility_off' : 'visibility' }}
                  </span>
                </button>
              </div>
            </div>

            <!-- Remember Me / Forgot Password -->
            <div class="flex items-center justify-between">
              <label class="flex items-center gap-xs cursor-pointer select-none">
                <input
                  v-model="rememberMe"
                  class="w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary/20 accent-primary"
                  type="checkbox"
                />
                <span class="font-label-md text-label-md text-on-surface-variant">Recordarme</span>
              </label>
              <a class="font-label-md text-label-md text-primary hover:underline transition-all" href="#">
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <!-- Submit Button -->
            <button
              class="w-full py-4 bg-primary text-on-primary font-label-md text-label-md rounded-input shadow-md btn-hover-effect flex items-center justify-center gap-xs cursor-pointer disabled:opacity-75 disabled:pointer-events-none"
              type="submit"
              :disabled="authStore.loading"
            >
              <template v-if="authStore.loading">
                <span class="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
                Cargando...
              </template>
              <template v-else>
                Ingresar al Portal
                <span class="material-symbols-outlined text-[20px]">login</span>
              </template>
            </button>
          </form>

          <!-- Setup Wizard Link -->
          <div class="mt-xl pt-lg border-t border-outline-variant/30 text-center">
            <p class="font-body-md text-body-md text-on-surface-variant mb-xs">¿Es tu primera vez aquí?</p>
            <router-link
              to="/setup"
              class="inline-flex items-center gap-xs font-label-md text-label-md text-primary font-bold hover:gap-sm transition-all"
            >
              Configuración Inicial (Setup Wizard)
              <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
            </router-link>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer
      class="fixed bottom-0 left-0 w-full p-sm flex justify-center md:justify-between items-center px-container-margin pointer-events-none"
    >
      <div class="hidden md:block">
        <p class="font-label-sm text-label-sm text-outline-variant">
          © 2024 OpenPiar. Inteligencia Pedagógica para la Inclusión.
        </p>
      </div>
      <div class="flex gap-md pointer-events-auto">
        <a class="font-label-sm text-label-sm text-outline-variant hover:text-primary transition-colors" href="#">
          Privacidad
        </a>
        <a class="font-label-sm text-label-sm text-outline-variant hover:text-primary transition-colors" href="#">
          Soporte Técnico
        </a>
      </div>
    </footer>
  </div>
</template>
