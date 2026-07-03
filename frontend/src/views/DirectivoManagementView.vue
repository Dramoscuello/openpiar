<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const directivos = ref<any[]>([])

const directivosFiltrados = computed(() => {
  return directivos.value.filter(d => d.id !== authStore.user?.id)
})
const showDirectivoModal = ref(false)
const directivoForm = ref({ email: '', password: '', nombre: '', apellido: '', cargo: 'Coordinador' })
const directivoEditingId = ref<string | null>(null)
const directivoPasswordSecured = ref(false)
const errorMsg = ref<string | null>(null)
const successMsg = ref<string | null>(null)

const dirPasswordValid = computed(() => {
  const p = directivoForm.value.password
  return p.length >= 8 && /[A-Za-z]/.test(p) && /\d/.test(p) && /[^A-Za-z0-9]/.test(p)
})

const puedeRegistrarDirectivo = computed(() => {
  if (directivoEditingId.value) return true
  return dirPasswordValid.value && directivoPasswordSecured.value
})

async function fetchDirectivos() {
  if (!authStore.token) return
  try {
    const res = await fetch('/api/v1/gestion/directivos', {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) directivos.value = await res.json()
  } catch (_) {}
}

function openNewDirectivo() {
  directivoEditingId.value = null
  directivoPasswordSecured.value = false
  directivoForm.value = { email: '', password: '', nombre: '', apellido: '', cargo: 'Coordinador' }
  showDirectivoModal.value = true
}

function openEditDirectivo(d: any) {
  directivoEditingId.value = d.id
  directivoForm.value = { email: d.email, password: '', nombre: d.nombre, apellido: d.apellido, cargo: d.cargo || 'Coordinador' }
  showDirectivoModal.value = true
}

function generarContrasenaDir() {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const lower = 'abcdefghijkmnpqrstuvwxyz'
  const digits = '23456789'
  const specials = '!@#$%&*_-+=?'
  const all = upper + lower + digits + specials
  const pool = [
    upper[Math.floor(Math.random() * upper.length)],
    lower[Math.floor(Math.random() * lower.length)],
    digits[Math.floor(Math.random() * digits.length)],
    specials[Math.floor(Math.random() * specials.length)],
  ]
  for (let i = pool.length; i < 12; i++) {
    pool.push(all[Math.floor(Math.random() * all.length)])
  }
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]]
  }
  directivoForm.value.password = pool.join('')
}

async function copiarContrasenaDir() {
  const f = directivoForm.value
  const nombreCompleto = [f.nombre, f.apellido].filter(Boolean).join(' ') || 'Directivo'
  const texto = `Email: ${f.email}\nContraseña: ${f.password}\nAccede en: ${window.location.origin}/login`
  try {
    await navigator.clipboard.writeText(texto)
    directivoPasswordSecured.value = true
  } catch {
    const ta = document.createElement('textarea')
    ta.value = texto; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta)
    directivoPasswordSecured.value = true
  }
}

function descargarContrasenaDirTxt() {
  const f = directivoForm.value
  const nombreCompleto = [f.nombre, f.apellido].filter(Boolean).join(' ') || 'Directivo'
  const contenido = [
    'Credenciales de acceso — OpenPiar',
    '',
    `Nombre:   ${nombreCompleto}`,
    `Email:    ${f.email || 'No especificado'}`,
    `Contraseña: ${f.password}`,
    `Cargo:    ${f.cargo}`,
    '',
    `Accede en: ${window.location.origin}/login`,
  ].join('\n')
  const blob = new Blob([contenido], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `credenciales-${nombreCompleto.toLowerCase().replace(/\s+/g, '-')}.txt`
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
  directivoPasswordSecured.value = true
}

async function submitDirectivo() {
  const f = directivoForm.value
  if (!f.email || (!directivoEditingId.value && !f.password) || !f.nombre || !f.apellido) {
    errorMsg.value = 'Completa todos los campos obligatorios.'
    return
  }
  if (!directivoEditingId.value && !dirPasswordValid.value) {
    errorMsg.value = 'La contraseña no cumple con los requisitos mínimos de seguridad.'
    return
  }
  if (!directivoEditingId.value && !directivoPasswordSecured.value) {
    errorMsg.value = 'Debes copiar o descargar la contraseña antes de registrar.'
    return
  }
  errorMsg.value = null; successMsg.value = null
  try {
    const isEdit = directivoEditingId.value !== null
    const url = isEdit ? `/api/v1/gestion/directivos/${directivoEditingId.value}` : '/api/v1/gestion/directivos'
    const method = isEdit ? 'PUT' : 'POST'
    const body: any = { ...f }
    if (isEdit && !body.password) delete body.password
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authStore.token}` },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Error al procesar.')
    if (isEdit) {
      const idx = directivos.value.findIndex(d => d.id === directivoEditingId.value)
      if (idx !== -1) directivos.value[idx] = data
    } else {
      directivos.value.push(data)
    }
    showDirectivoModal.value = false
    successMsg.value = isEdit ? 'Directivo actualizado exitosamente.' : 'Directivo registrado exitosamente.'
    setTimeout(() => successMsg.value = null, 4000)
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

async function deleteDirectivo(id: string) {
  if (!confirm('¿Eliminar este directivo permanentemente? Perderá el acceso al sistema.')) return
  try {
    const res = await fetch(`/api/v1/gestion/directivos/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'No se pudo eliminar.')
    }
    directivos.value = directivos.value.filter(d => d.id !== id)
    successMsg.value = 'Directivo eliminado exitosamente.'
    setTimeout(() => successMsg.value = null, 4000)
  } catch (err: any) {
    errorMsg.value = err.message
  }
}

onMounted(() => {
  fetchDirectivos()
})
</script>

<template>
  <div class="p-gutter max-w-screen-2xl mx-auto space-y-gutter flex-grow w-full">
    <div class="flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container-lowest p-md border border-outline-variant/30 rounded-xxl shadow-sm">
      <div class="flex items-center gap-3">
        <span class="material-symbols-outlined text-primary text-[28px]">admin_panel_settings</span>
        <h2 class="font-headline-md text-headline-md text-on-surface">Gestión Directiva</h2>
      </div>
      <button
        @click="openNewDirectivo()"
        class="bg-primary hover:bg-primary-container text-white px-lg py-3 rounded-xl font-label-md text-label-md flex items-center gap-xs cursor-pointer shadow-md shadow-primary/10 transition-all active:scale-95"
      >
        <span class="material-symbols-outlined text-[20px]">person_add</span>
        Registrar directivo
      </button>
    </div>

    <div v-if="errorMsg" class="bg-error-container text-on-error-container p-3 rounded-xl text-body-sm">{{ errorMsg }}</div>
    <div v-if="successMsg" class="bg-[#caead6] dark:bg-green-800 text-[#042014] dark:text-green-100 p-3 rounded-xl text-body-sm">{{ successMsg }}</div>

    <div class="bg-surface-container-lowest border border-outline-variant/30 rounded-xxl overflow-hidden shadow-sm">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="border-b border-outline-variant/30 bg-surface-container text-on-surface-variant text-label-sm font-bold">
            <th class="py-4 px-md">Nombre</th>
            <th class="py-4 px-md">Email</th>
            <th class="py-4 px-md">Cargo</th>
            <th class="py-4 px-md text-right">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/20 text-body-md text-on-surface">
          <tr v-for="d in directivosFiltrados" :key="d.id" class="hover:bg-surface-container-low/40">
            <td class="py-4 px-md font-bold">{{ d.apellido }}, {{ d.nombre }}</td>
            <td class="py-4 px-md font-mono text-[13px]">{{ d.email }}</td>
            <td class="py-4 px-md">
              <span class="bg-primary/10 text-primary px-2 py-0.5 rounded text-label-sm font-bold">{{ d.cargo }}</span>
            </td>
            <td class="py-4 px-md text-right flex justify-end gap-xs">
              <button @click="openEditDirectivo(d)" class="p-2 hover:bg-surface-container-high rounded-full text-outline hover:text-primary transition-all cursor-pointer" title="Editar directivo">
                <span class="material-symbols-outlined text-[20px]">edit</span>
              </button>
              <button @click="deleteDirectivo(d.id)" class="p-2 hover:bg-red-50 rounded-full text-outline hover:text-error transition-all cursor-pointer" title="Eliminar directivo">
                <span class="material-symbols-outlined text-[20px]">delete</span>
              </button>
            </td>
          </tr>
          <tr v-if="directivosFiltrados.length === 0">
            <td colspan="4" class="py-8 text-center text-outline">No hay otros directivos registrados.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- MODAL -->
    <div v-if="showDirectivoModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div class="bg-surface-container-lowest max-w-[512px] w-full rounded-xxl p-md border border-outline-variant/30 shadow-lg space-y-md overflow-y-auto max-h-[90vh]">
        <h3 class="font-headline-md text-[20px] text-primary flex items-center gap-xs">
          <span class="material-symbols-outlined">{{ directivoEditingId ? 'manage_accounts' : 'admin_panel_settings' }}</span>
          {{ directivoEditingId ? 'Editar directivo' : 'Registrar nuevo directivo' }}
        </h3>
        <div class="space-y-sm">
          <div class="grid grid-cols-2 gap-sm">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Nombres *</label>
              <input v-model="directivoForm.nombre" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant">Apellidos *</label>
              <input v-model="directivoForm.apellido" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="text" />
            </div>
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Email *</label>
            <input v-model="directivoForm.email" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white" type="email" placeholder="directivo@colegio.edu.co" />
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">{{ directivoEditingId ? 'Nueva contraseña (dejar en blanco para conservar la actual)' : 'Contraseña de acceso *' }}</label>
            <input
              v-model="directivoForm.password" type="password"
              class="w-full px-4 py-3 bg-surface border rounded-input focus:outline-none dark:text-white"
              :class="!directivoEditingId && directivoForm.password && !dirPasswordValid ? 'border-error' : 'border-outline-variant focus:border-primary'"
            />
            <div v-if="!directivoEditingId && directivoForm.password" class="pt-1 grid grid-cols-2 gap-xs">
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="directivoForm.password.length >= 8 ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ directivoForm.password.length >= 8 ? 'check_circle' : 'circle' }}</span> Mín. 8 caracteres
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="/[A-Za-z]/.test(directivoForm.password) ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ /[A-Za-z]/.test(directivoForm.password) ? 'check_circle' : 'circle' }}</span> Al menos una letra
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="/\d/.test(directivoForm.password) ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ /\d/.test(directivoForm.password) ? 'check_circle' : 'circle' }}</span> Al menos un número
              </span>
              <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="/[^A-Za-z0-9]/.test(directivoForm.password) ? 'text-[#166534]' : 'text-on-surface-variant'">
                <span class="material-symbols-outlined text-[16px]">{{ /[^A-Za-z0-9]/.test(directivoForm.password) ? 'check_circle' : 'circle' }}</span> Un carácter especial
              </span>
            </div>
            <button v-if="!directivoEditingId" @click="generarContrasenaDir" class="text-label-sm text-primary font-bold flex items-center gap-1 hover:underline cursor-pointer select-none" type="button">
              <span class="material-symbols-outlined text-[16px]">casino</span> Generar contraseña aleatoria
            </button>
            <div v-if="!directivoEditingId && dirPasswordValid" class="flex gap-sm pt-1">
              <button @click="copiarContrasenaDir" class="px-3 py-2 bg-surface border border-outline-variant rounded-lg text-label-sm flex items-center gap-1 hover:bg-secondary-container transition-all cursor-pointer font-bold" type="button">
                <span class="material-symbols-outlined text-[16px]">content_copy</span> Copiar
              </button>
              <button @click="descargarContrasenaDirTxt" class="px-3 py-2 bg-surface border border-outline-variant rounded-lg text-label-sm flex items-center gap-1 hover:bg-secondary-container transition-all cursor-pointer font-bold" type="button">
                <span class="material-symbols-outlined text-[16px]">download</span> Descargar TXT
              </button>
            </div>
            <p v-if="!directivoEditingId && dirPasswordValid && !directivoPasswordSecured" class="text-amber-700 font-label-sm text-label-sm">
              Copia o descarga la contraseña para habilitar el registro.
            </p>
          </div>
          <div class="space-y-xs">
            <label class="font-label-md text-label-md text-on-surface-variant">Cargo *</label>
            <select v-model="directivoForm.cargo" class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input focus:border-primary focus:outline-none dark:text-white">
              <option value="Rector/Director">Rector / Director</option>
              <option value="Coordinador">Coordinador</option>
              <option value="Secretario/a">Secretario/a</option>
              <option value="Administrativo">Administrativo</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-sm pt-sm border-t border-outline-variant/30">
          <button @click="showDirectivoModal = false" class="px-lg py-3 border border-outline hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all active:scale-95">Cancelar</button>
          <button @click="submitDirectivo" :disabled="!puedeRegistrarDirectivo" class="px-lg py-3 bg-primary text-white rounded-input font-label-md text-label-md transition-all active:scale-95" :class="puedeRegistrarDirectivo ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'">{{ directivoEditingId ? 'Actualizar directivo' : 'Registrar directivo' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
