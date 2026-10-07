// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fetchWithAuth,
  resetAuthHandlersForTests,
  setAuthHandlers,
} from './client'

const API = () => `${window.location.origin}/api/v1/piars/1`

function respuesta(status: number, body: unknown = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('cliente HTTP con refresh de sesión', () => {
  beforeEach(() => {
    resetAuthHandlersForTests()
  })

  it('adjunta el token, refresca tras 401 y reintenta con el token nuevo', async () => {
    let token: string | null = 'token-viejo'
    const refresh = vi.fn(async () => {
      token = 'token-nuevo'
      return true
    })
    setAuthHandlers({
      getToken: () => token,
      refresh,
      onSessionExpired: vi.fn(),
    })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respuesta(401))
      .mockResolvedValueOnce(respuesta(200, { ok: true }))

    const res = await fetchWithAuth(API(), { method: 'GET' }, { fetchImpl: fetchMock })

    expect(res.status).toBe(200)
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const reintento = fetchMock.mock.calls[1]![0] as Request
    expect(reintento.headers.get('Authorization')).toBe('Bearer token-nuevo')
  })

  it('si el refresh falla, notifica sesión expirada sin reintentar', async () => {
    const onSessionExpired = vi.fn()
    setAuthHandlers({
      getToken: () => 'token-viejo',
      refresh: vi.fn(async () => false),
      onSessionExpired,
    })

    const fetchMock = vi.fn().mockResolvedValueOnce(respuesta(401))

    const res = await fetchWithAuth(API(), { method: 'GET' }, { fetchImpl: fetchMock })

    expect(res.status).toBe(401)
    expect(onSessionExpired).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('no refresca en rutas de autenticación', async () => {
    const refresh = vi.fn(async () => true)
    setAuthHandlers({ getToken: () => 't', refresh, onSessionExpired: vi.fn() })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respuesta(401, { detail: 'Credenciales inválidas' }))

    const res = await fetchWithAuth(
      `${window.location.origin}/api/v1/auth/login`,
      { method: 'POST' },
      { fetchImpl: fetchMock },
    )

    expect(res.status).toBe(401)
    expect(refresh).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('agrupa varios 401 en un solo refresh', async () => {
    let token: string | null = 'viejo'
    const refresh = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10))
      token = 'nuevo'
      return true
    })
    setAuthHandlers({ getToken: () => token, refresh, onSessionExpired: vi.fn() })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respuesta(401))
      .mockResolvedValueOnce(respuesta(401))
      .mockResolvedValue(respuesta(200))

    await Promise.all([
      fetchWithAuth(API(), { method: 'GET' }, { fetchImpl: fetchMock }),
      fetchWithAuth(API(), { method: 'GET' }, { fetchImpl: fetchMock }),
    ])

    expect(refresh).toHaveBeenCalledTimes(1)
  })
})
