// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { ApiError, authApi, type UserResponse, type SetupStatus } from '../api/auth'

let initPromise: Promise<void> | null = null

export interface AuthState {
  token: string | null
  user: UserResponse | null
  setupStatus: SetupStatus | null
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    // El access token vive solo en memoria; el refresh va en cookie HttpOnly.
    token: null,
    user: null,
    setupStatus: null,
    loading: false,
    error: null,
  }),

  getters: {
    isAuthenticated: (state): boolean => !!state.token,
    isSetupCompleted: (state): boolean => state.setupStatus?.setup_completado ?? true,
    nombreInstitucion: (state): string => state.setupStatus?.nombre_institucion ?? 'OpenPiar',
    canCreateStudent: (state): boolean => {
      if (!state.user) return false
      return state.user.rol === 'directivo' || !!state.user.es_director
    },
  },

  actions: {
    /**
     * Inicia sesión con correo y contraseña.
     */
    async login(email: string, password: string): Promise<boolean> {
      this.loading = true
      this.error = null
      try {
        const response = await authApi.login(email, password)
        this.token = response.access_token
        await this.fetchCurrentUser()
        return true
      } catch (err: any) {
        this.error = err.message || 'Error al iniciar sesión'
        this.clearSession()
        return false
      } finally {
        this.loading = false
      }
    },

    /**
     * Renueva el access token usando la cookie HttpOnly de refresh.
     */
    async refreshSession(): Promise<boolean> {
      try {
        const response = await fetch('/api/v1/auth/refresh', { method: 'POST' })
        if (!response.ok) return false
        const data = await response.json()
        this.token = data.access_token
        return true
      } catch {
        return false
      }
    },

    /**
     * Obtiene los datos del usuario logueado con el access token en memoria.
     */
    async fetchCurrentUser(): Promise<void> {
      if (!this.token) return

      try {
        this.user = await authApi.getMe(this.token)
      } catch (err) {
        // Solo cerrar sesión si el servidor rechazó el token; no ante fallos de red.
        if (err instanceof ApiError && err.status === 401) {
          this.clearSession()
        }
      }
    },

    /**
     * Cierra la sesión activa y revoca el refresh token en el servidor.
     */
    async logout(): Promise<void> {
      try {
        await fetch('/api/v1/auth/logout', { method: 'POST' })
      } catch {
        // Aunque falle la red, la sesión local se limpia.
      }
      this.clearSession()
    },

    /**
     * Limpia el estado local de sesión.
     */
    clearSession(): void {
      this.token = null
      this.user = null
    },

    /**
     * Obtiene el estado del setup wizard.
     */
    async checkSetupStatus(): Promise<void> {
      try {
        this.setupStatus = await authApi.getSetupStatus()
      } catch (err) {
        console.error('Error obteniendo estado del setup wizard:', err)
        // Por defecto asumimos completado si falla para no bloquear el login en desarrollo sin backend
        this.setupStatus = {
          setup_completado: true,
          nombre_institucion: null,
          tiene_gemini_key: false,
        }
      }
    },

    /**
     * Inicializa la autenticación y el setup del sistema al arrancar la app.
     */
    async initAuth(): Promise<void> {
      if (initPromise) return initPromise

      initPromise = (async () => {
        await this.checkSetupStatus()
        // Limpieza del token persistente de versiones anteriores.
        localStorage.removeItem('openpiar_token')

        if (this.token) {
          await this.fetchCurrentUser()
          return
        }
        const refreshed = await this.refreshSession()
        if (refreshed) {
          await this.fetchCurrentUser()
        }
      })()

      return initPromise
    },

    /**
     * Marca la sesión como expirada y redirige al login.
     *
     * Antes de cerrar, reintenta el refresh: otra pestaña pudo haber rotado la
     * cookie y el navegador ya tener el token vigente.
     */
    async sessionExpired(): Promise<void> {
      const refreshed = await this.refreshSession()
      if (refreshed) {
        await this.fetchCurrentUser()
        return
      }
      this.clearSession()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    },
  },
})
