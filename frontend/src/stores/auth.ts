// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { authApi, type UserResponse, type SetupStatus } from '../api/auth'

export interface AuthState {
  token: string | null
  user: UserResponse | null
  setupStatus: SetupStatus | null
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('openpiar_token'),
    user: null,
    setupStatus: null,
    loading: false,
    error: null,
  }),

  getters: {
    isAuthenticated: (state): boolean => !!state.token,
    isSetupCompleted: (state): boolean => state.setupStatus?.setup_completado ?? true,
    nombreInstitucion: (state): string => state.setupStatus?.nombre_institucion ?? 'OpenPiar',
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
        localStorage.setItem('openpiar_token', response.access_token)
        
        // Cargar datos del usuario inmediatamente
        await this.fetchCurrentUser()
        return true
      } catch (err: any) {
        this.error = err.message || 'Error al iniciar sesión'
        this.logout()
        return false
      } finally {
        this.loading = false
      }
    },

    /**
     * Obtiene los datos del usuario logueado usando el token guardado.
     */
    async fetchCurrentUser(): Promise<void> {
      if (!this.token) return
      
      try {
        const userResponse = await authApi.getMe(this.token)
        this.user = userResponse
      } catch (err) {
        // Si el token es inválido o expiró, desloguear
        this.logout()
      }
    },

    /**
     * Cierra la sesión activa.
     */
    logout(): void {
      this.token = null
      this.user = null
      localStorage.removeItem('openpiar_token')
    },

    /**
     * Obtiene el estado del setup wizard.
     */
    async checkSetupStatus(): Promise<void> {
      try {
        const status = await authApi.getSetupStatus()
        this.setupStatus = status
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
      await this.checkSetupStatus()
      if (this.token) {
        await this.fetchCurrentUser()
      }
    },
  },
})
