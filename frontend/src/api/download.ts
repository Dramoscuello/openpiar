// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
/**
 * Utilidades para descargar archivos respetando el nombre que envía el servidor.
 */

export function nombreDesdeRespuesta(response: Response, fallback: string): string {
  const header = response.headers.get('Content-Disposition') || ''
  const utf8 = header.match(/filename\*=UTF-8''([^;]+)/i)
  const simple = header.match(/filename="?([^";]+)"?/i)
  const valor = (utf8?.[1] ?? simple?.[1] ?? '').trim()
  if (!valor) return fallback
  try {
    return decodeURIComponent(valor)
  } catch {
    return valor
  }
}

export function descargarBlob(blob: Blob, nombre: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = nombre
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
