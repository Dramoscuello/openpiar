// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'

function respuestaJson(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('sesión en memoria', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('reintenta el refresh antes de cerrar la sesión', async () => {
    let refrescos = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/refresh')) {
        refrescos += 1
        return refrescos === 1
          ? respuestaJson(401, { detail: 'rotado' })
          : respuestaJson(200, { access_token: 'token-nuevo' })
      }
      if (url.includes('/auth/me')) {
        return respuestaJson(200, {
          id: 'u1',
          email: 'docente@colegio.edu.co',
          nombre: 'Ada',
          apellido: 'Lovelace',
          rol: 'docente_aula',
          created_at: '2026-01-01T00:00:00Z',
        })
      }
      return respuestaJson(404, {})
    })
    vi.stubGlobal('fetch', fetchMock)

    const store = useAuthStore()
    // Primer intento: el que hace el interceptor y falla por la carrera.
    await store.refreshSession()
    // Reintento antes de cerrar la sesión: la cookie ya fue rotada por otra pestaña.
    await store.sessionExpired()

    expect(refrescos).toBe(2)
    expect(store.token).toBe('token-nuevo')
    expect(store.user?.id).toBe('u1')

    vi.unstubAllGlobals()
  })
})
