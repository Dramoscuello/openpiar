// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
/**
 * Cliente HTTP central.
 *
 * - Adjunta el access token (en memoria) a todas las peticiones /api.
 * - Ante 401, intenta un único POST /auth/refresh y reintenta la petición.
 * - Si el refresh falla, notifica sesión expirada.
 *
 * Se instala como interceptor de `window.fetch` para cubrir las llamadas
 * existentes sin reescribirlas, y exporta `fetchWithAuth` para uso directo.
 */

export interface AuthHandlers {
  getToken: () => string | null
  refresh: () => Promise<boolean>
  onSessionExpired: () => void
}

type FetchInput = RequestInfo | URL
type FetchImpl = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

const AUTH_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/refresh',
  '/api/v1/auth/logout',
]

let handlers: AuthHandlers | null = null
let refreshPromise: Promise<boolean> | null = null
let interceptorInstalled = false

export function setAuthHandlers(next: AuthHandlers | null): void {
  handlers = next
}

export function resetAuthHandlersForTests(): void {
  handlers = null
  refreshPromise = null
  interceptorInstalled = false
}

function urlOf(input: FetchInput): string {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.toString()
  return input.url
}

function esRutaDeAuth(url: string): boolean {
  return AUTH_PATHS.some((ruta) => url.includes(ruta))
}

function esApiUrl(url: string): boolean {
  if (url.startsWith('/api/')) return true
  try {
    const parsed = new URL(url, window.location.origin)
    return (
      parsed.origin === window.location.origin &&
      parsed.pathname.startsWith('/api/')
    )
  } catch {
    return false
  }
}

function buildRequest(input: FetchInput, init?: RequestInit): Request {
  const request = input instanceof Request ? input.clone() : new Request(input, init)
  const token = handlers?.getToken() ?? null
  if (token) {
    request.headers.set('Authorization', `Bearer ${token}`)
  } else {
    request.headers.delete('Authorization')
  }
  return request
}

async function refreshOnce(): Promise<boolean> {
  if (!handlers) return false
  if (!refreshPromise) {
    refreshPromise = handlers
      .refresh()
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export async function fetchWithAuth(
  input: FetchInput,
  init: RequestInit | undefined,
  deps: { fetchImpl: FetchImpl },
): Promise<Response> {
  const url = urlOf(input)
  if (!esApiUrl(url)) {
    return deps.fetchImpl(input, init)
  }

  const response = await deps.fetchImpl(buildRequest(input, init))

  if (response.status !== 401 || esRutaDeAuth(url)) {
    return response
  }

  const refreshed = await refreshOnce()
  if (!refreshed) {
    handlers?.onSessionExpired()
    return response
  }
  return deps.fetchImpl(buildRequest(input, init))
}

export function installApiInterceptor(): void {
  if (interceptorInstalled) return
  interceptorInstalled = true
  const original = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    fetchWithAuth(input, init, { fetchImpl: original })
}
