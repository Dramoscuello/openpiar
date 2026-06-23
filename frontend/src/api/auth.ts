// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
/**
 * Cliente de API para Autenticación y Setup.
 */

export interface SetupStatus {
  setup_completado: boolean
  nombre_institucion: string | null
  tiene_gemini_key: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  nombre: string
  apellido: string
  rol: string
  es_director?: boolean
  created_at: string
}

/**
 * Helper para peticiones HTTP
 */
async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, options)

  if (!response.ok) {
    let errorDetail = 'Ha ocurrido un error inesperado'
    try {
      const errorJson = await response.json()
      errorDetail = errorJson.detail || errorDetail
    } catch {
      // Usar error por defecto si la respuesta no es JSON
    }
    throw new Error(errorDetail)
  }

  return response.json() as Promise<T>
}

export const authApi = {
  /**
   * Obtiene el estado de configuración inicial de la plataforma
   */
  async getSetupStatus(): Promise<SetupStatus> {
    return apiFetch<SetupStatus>('/api/v1/setup/status')
  },

  /**
   * Inicia sesión con credenciales de usuario (docente/directivo)
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)

    return apiFetch<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
    })
  },

  /**
   * Obtiene los datos del usuario actualmente autenticado
   */
  async getMe(token: string): Promise<UserResponse> {
    return apiFetch<UserResponse>('/api/v1/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
  },
}
