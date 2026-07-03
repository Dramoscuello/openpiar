<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

interface EstudianteInfo {
  id: string
  nombre: string
  grado: string | null
  piar_id: string | null
  codigo_acceso_familia: string | null
}

interface ContactoInfo {
  nombre: string
  rol: string
  telefono: string | null
  correo: string | null
  numero_documento: string | null
  acudiente_principal: boolean
  estudiantes: EstudianteInfo[]
}

const contactos = ref<ContactoInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const expandedContactos = ref<Set<number>>(new Set())
const sharingIndex = ref<number | null>(null)
const sharingLoading = ref(false)

const rolLabels: Record<string, string> = {
  madre: 'Madre',
  padre: 'Padre',
  cuidador: 'Cuidador(a)',
}

async function fetchDirectorio() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/v1/directorio', {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error al cargar el directorio')
    }
    const data = await res.json()
    contactos.value = data.contactos || []
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function toggleExpand(index: number) {
  if (expandedContactos.value.has(index)) {
    expandedContactos.value.delete(index)
  } else {
    expandedContactos.value.add(index)
  }
}

async function downloadPiarPDF(piarId: string, estudianteNombre: string) {
  try {
    const res = await fetch(`/api/v1/piars/${piarId}/acta/pdf`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    if (!res.ok) throw new Error('Error al descargar el PDF')
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `PIAR_${estudianteNombre.replace(/\s+/g, '_')}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e: any) {
    alert(e.message || 'No se pudo descargar el PDF')
  }
}

async function compartirPDF(estudiante: EstudianteInfo) {
  if (!estudiante.piar_id) {
    alert('Este estudiante no tiene un PIAR activo para compartir.')
    return
  }
  sharingLoading.value = true
  try {
    const res = await fetch(`/api/v1/piars/${estudiante.piar_id}/acta/pdf`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    if (!res.ok) throw new Error('Error al obtener el PDF')
    const blob = await res.blob()
    const file = new File([blob], `PIAR_${estudiante.nombre.replace(/\s+/g, '_')}.pdf`, { type: 'application/pdf' })

    if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({
        title: `PIAR - ${estudiante.nombre}`,
        text: `Plan Individual de Ajustes Razonables de ${estudiante.nombre}`,
        files: [file],
      })
    } else {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `PIAR_${estudiante.nombre.replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      alert(e.message || 'No se pudo compartir el PDF')
    }
  } finally {
    sharingLoading.value = false
    sharingIndex.value = null
  }
}

function limpiarTelefono(telefono: string | null): string {
  if (!telefono) return ''
  return telefono.replace(/[\s\-\+\(\)]/g, '')
}

async function asegurarCodigo(estudiante: EstudianteInfo): Promise<string> {
  if (estudiante.codigo_acceso_familia) return estudiante.codigo_acceso_familia
  try {
    const res = await fetch(`/api/v1/estudiantes/${estudiante.id}/regenerar-codigo-familia`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` },
    })
    if (res.ok) {
      const data = await res.json()
      const match = data.message?.match(/:\s*(\S+)$/)
      const codigo = match ? match[1] : ''
      estudiante.codigo_acceso_familia = codigo
      return codigo
    }
  } catch (e) { /* fallback */ }
  return ''
}

function urlFamilia(estudiante: EstudianteInfo): string {
  return estudiante.codigo_acceso_familia
    ? `${window.location.origin}/familia/${estudiante.codigo_acceso_familia}`
    : ''
}

async function compartirWhatsApp(estudiante: EstudianteInfo, telefono: string | null) {
  if (!estudiante.piar_id) return
  sharingLoading.value = true
  await asegurarCodigo(estudiante)
  sharingLoading.value = false
  const url = urlFamilia(estudiante)
  const texto = url
    ? `Plan Individual de Ajustes Razonables (PIAR) de ${estudiante.nombre}${estudiante.grado ? ` — Grado: ${estudiante.grado}` : ''}.\n\nAccede al documento aquí:\n${url}`
    : `Plan Individual de Ajustes Razonables (PIAR) de ${estudiante.nombre}.`
  const phone = limpiarTelefono(telefono)
  const waUrl = phone
    ? `https://wa.me/57${phone}?text=${encodeURIComponent(texto)}`
    : `https://wa.me/?text=${encodeURIComponent(texto)}`
  window.open(waUrl, '_blank')
}

async function compartirEmail(estudiante: EstudianteInfo) {
  if (!estudiante.piar_id) return
  sharingLoading.value = true
  await asegurarCodigo(estudiante)
  sharingLoading.value = false
  const url = urlFamilia(estudiante)
  const asunto = `PIAR — ${estudiante.nombre}`
  const cuerpo = url
    ? `Plan Individual de Ajustes Razonables (PIAR) de ${estudiante.nombre}${estudiante.grado ? ` (Grado: ${estudiante.grado})` : ''}.\n\nAccede al documento aquí:\n${url}\n\nGenerado por OpenPiar.`
    : `Plan Individual de Ajustes Razonables (PIAR) de ${estudiante.nombre}.\n\nGenerado por OpenPiar.`
  window.open(`mailto:?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`, '_blank')
}

onMounted(() => {
  fetchDirectorio()
})
</script>

<template>
  <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
    <div class="flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container-lowest p-md border border-outline-variant/30 rounded-xxl shadow-sm transition-colors duration-300">
      <div class="flex items-center gap-3">
        <span class="material-symbols-outlined text-primary text-[28px]">contacts</span>
        <h2 class="font-headline-md text-headline-md text-on-surface">Directorio de padres y acudientes</h2>
      </div>
      <div class="flex items-center gap-xs text-label-sm text-outline">
        Total: <span class="font-bold text-on-surface">{{ contactos.length }}</span> contactos
      </div>
    </div>

    <div v-if="loading" class="p-xl flex flex-col items-center justify-center gap-sm text-outline">
      <span class="material-symbols-outlined animate-spin text-[48px] text-primary">progress_activity</span>
      Cargando directorio...
    </div>

    <div v-else-if="error" class="p-xl text-center">
      <span class="material-symbols-outlined text-[48px] text-error">error</span>
      <p class="text-error mt-sm">{{ error }}</p>
      <button
        @click="fetchDirectorio"
        class="mt-md bg-primary text-white px-lg py-2 rounded-xl font-label-md cursor-pointer"
      >
        Reintentar
      </button>
    </div>

    <div v-else-if="contactos.length === 0" class="p-xl text-center space-y-sm">
      <span class="material-symbols-outlined text-[64px] text-outline">contact_page</span>
      <h3 class="font-headline-md text-[20px] text-on-surface">No hay contactos registrados</h3>
      <p class="text-body-md text-outline max-w-[448px] mx-auto">
        Registra la información de los padres en el formulario del estudiante (Anexo 1, sección Hogar) para que aparezcan aquí.
      </p>
    </div>

    <div v-else class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold select-none">
              <th class="py-4 px-md">#</th>
              <th class="py-4 px-md">Contacto</th>
              <th class="py-4 px-md">Rol</th>
              <th class="py-4 px-md">Teléfono</th>
              <th class="py-4 px-md">Correo</th>
              <th class="py-4 px-md">Estudiantes a cargo</th>
              <th class="py-4 px-md text-right">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
            <template v-for="(c, ci) in contactos" :key="ci">
              <tr class="hover:bg-surface-container-low/40 transition-colors duration-200">
                <td class="py-4 px-md text-outline">{{ ci + 1 }}</td>
                <td class="py-4 px-md">
                  <div class="flex items-center gap-xs">
                    <div class="w-9 h-9 bg-primary/10 text-primary rounded-full flex items-center justify-center font-bold text-[14px]">
                      {{ c.nombre.substring(0, 1).toUpperCase() }}
                    </div>
                    <div>
                      <div class="font-bold">{{ c.nombre }}</div>
                      <div v-if="c.numero_documento" class="text-label-sm text-outline font-mono">{{ c.numero_documento }}</div>
                    </div>
                  </div>
                </td>
                <td class="py-4 px-md">
                  <span class="inline-flex items-center gap-1">
                    {{ rolLabels[c.rol] || c.rol }}
                    <span v-if="c.acudiente_principal" class="bg-amber-100 text-amber-800 text-label-xs px-1.5 py-0.5 rounded-full font-bold">Acudiente</span>
                  </span>
                </td>
                <td class="py-4 px-md font-mono text-label-md">
                  <a v-if="c.telefono" :href="'https://wa.me/' + c.telefono.replace(/\D/g, '')" target="_blank" class="text-primary hover:underline">
                    {{ c.telefono }}
                  </a>
                  <span v-else class="text-outline">—</span>
                </td>
                <td class="py-4 px-md">
                  <a v-if="c.correo" :href="'mailto:' + c.correo" class="text-primary hover:underline text-label-md">{{ c.correo }}</a>
                  <span v-else class="text-outline">—</span>
                </td>
                <td class="py-4 px-md">
                  <div class="flex flex-col gap-1">
                    <div v-for="(est, ei) in (expandedContactos.has(ci) || c.estudiantes.length <= 1 ? c.estudiantes : c.estudiantes.slice(0, 1))" :key="ei">
                      <span class="text-label-md">{{ est.nombre }}</span>
                      <span v-if="est.grado" class="text-label-sm text-outline ml-1">({{ est.grado }})</span>
                      <span v-if="!est.piar_id" class="text-label-xs text-error ml-1">Sin PIAR</span>
                    </div>
                    <button
                      v-if="c.estudiantes.length > 1"
                      @click="toggleExpand(ci)"
                      class="text-primary hover:underline text-label-sm font-bold cursor-pointer mt-1"
                    >
                      <span v-if="expandedContactos.has(ci)">
                        <span class="material-symbols-outlined text-[16px] align-middle">expand_less</span>
                        Mostrar menos
                      </span>
                      <span v-else>
                        <span class="material-symbols-outlined text-[16px] align-middle">expand_more</span>
                        +{{ c.estudiantes.length - 1 }} más
                      </span>
                    </button>
                  </div>
                </td>
                <td class="py-4 px-md text-right">
                  <div class="flex items-center justify-end gap-xs" v-for="est in c.estudiantes" :key="est.id">
                    <button
                      :disabled="!est.piar_id || sharingLoading"
                      @click="compartirPDF(est)"
                      class="p-2 text-primary hover:bg-primary/5 rounded-full transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      :title="est.piar_id ? 'Compartir PIAR' : 'No tiene PIAR activo'"
                    >
                      <span class="material-symbols-outlined text-[20px]">share</span>
                    </button>
                    <button
                      :disabled="!est.piar_id"
                      @click="compartirWhatsApp(est, c.telefono)"
                      class="p-2 text-green-600 hover:bg-green-50 rounded-full transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      :title="'Enviar por WhatsApp'"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                    </button>
                    <button
                      :disabled="!est.piar_id"
                      @click="compartirEmail(est)"
                      class="p-2 text-blue-600 hover:bg-blue-50 rounded-full transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      :title="'Enviar por Email'"
                    >
                      <span class="material-symbols-outlined text-[20px]">mail</span>
                    </button>
                    <button
                      :disabled="!est.piar_id"
                      @click="downloadPiarPDF(est.piar_id!, est.nombre)"
                      class="p-2 text-outline hover:bg-surface-container-high rounded-full transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      :title="'Descargar PDF'"
                    >
                      <span class="material-symbols-outlined text-[20px]">download</span>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
