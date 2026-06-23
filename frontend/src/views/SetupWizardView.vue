<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// Wizard steps: 1 (Colegio), 2 (IA), 3 (Administrador)
const currentStep = ref(1)

// Step 1: Colegio
const nombreInstitucion = ref('')
const nit = ref('')
const codigoDane = ref('')
const direccion = ref('')
const telefonoContacto = ref('')
const correoContacto = ref('')
const nombreRector = ref('')

// Step 2: Gemini
const geminiApiKey = ref('')

// Step 3: PEI
const peiFile = ref<File | null>(null)
const isUploadingPei = ref(false)
const peiUploadError = ref<string | null>(null)
const peiData = ref<any>(null)

// Step 4: Administrador
const adminNombre = ref('')
const adminApellido = ref('')
const adminCargo = ref('')
const adminEmail = ref('')
const adminPassword = ref('')
const adminConfirmPassword = ref('')

// UI state
const isSubmitting = ref(false)
const errorMessage = ref<string | null>(null)

// Password complexity rules
const hasMinLength = computed(() => adminPassword.value.length >= 8)
const hasLetter = computed(() => /[A-Za-z]/.test(adminPassword.value))
const hasNumber = computed(() => /\d/.test(adminPassword.value))
const hasSpecialChar = computed(() => /[^A-Za-z0-9]/.test(adminPassword.value))
const passwordIsValid = computed(() => hasMinLength.value && hasLetter.value && hasNumber.value && hasSpecialChar.value)
const passwordsMatch = computed(() => adminPassword.value === adminConfirmPassword.value)

// DANE validation
const daneIsValid = computed(() => codigoDane.value.length === 12 && /^\d+$/.test(codigoDane.value))

// Navigation functions
const nextStep = () => {
  if (currentStep.value === 1) {
    if (!nombreInstitucion.value || !nit.value || !codigoDane.value || !direccion.value) {
      errorMessage.value = 'Por favor, completa todos los campos obligatorios del colegio.'
      return
    }
    if (!daneIsValid.value) {
      errorMessage.value = 'El código DANE debe tener exactamente 12 dígitos numéricos.'
      return
    }
  }

  if (currentStep.value === 2) {
    if (!geminiApiKey.value) {
      errorMessage.value = 'Recomendamos configurar la API Key de Gemini para que el Asistente funcione en el siguiente paso al leer el PEI.'
      // Not returning here to allow skipping if they really want to, but for PEI it will fail.
    }
  }
  
  if (currentStep.value === 3) {
    // Si estamos en el paso 3 y presionan siguiente sin subir archivo, podemos dejarlos pasar
    // pero perderán la capacidad de IA inicial.
    // Para simplificar, permitimos omitir.
  }
  
  errorMessage.value = null
  currentStep.value++
}

const handleFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    peiFile.value = target.files[0] || null
  }
}

const uploadPEI = async () => {
  if (!peiFile.value) {
    peiUploadError.value = 'Por favor selecciona un archivo PDF.'
    return
  }
  if (!geminiApiKey.value) {
    peiUploadError.value = 'Necesitas haber ingresado tu API Key de Gemini en el paso anterior para procesar el PEI con IA.'
    return
  }
  
  isUploadingPei.value = true
  peiUploadError.value = null
  
  const formData = new FormData()
  formData.append('file', peiFile.value)
  formData.append('gemini_api_key', geminiApiKey.value)
  
  try {
    const response = await fetch('/api/v1/setup/upload-pei', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Error al procesar el archivo PEI.')
    }
    
    peiData.value = await response.json()
    // Avanzar automáticamente al paso 4 cuando el PEI se lee con éxito
    currentStep.value++
  } catch (e: any) {
    peiUploadError.value = e.message
  } finally {
    isUploadingPei.value = false
  }
}

const prevStep = () => {
  errorMessage.value = null
  currentStep.value--
}

// Submission
const handleConfigure = async () => {
  if (currentStep.value !== 4) return
  
  if (!adminNombre.value || !adminApellido.value || !adminCargo.value || !adminEmail.value || !adminPassword.value) {
    errorMessage.value = 'Por favor, completa todos los campos del administrador.'
    return
  }
  
  if (!passwordIsValid.value) {
    errorMessage.value = 'La contraseña no cumple con los requisitos mínimos de seguridad.'
    return
  }
  
  if (!passwordsMatch.value) {
    errorMessage.value = 'Las contraseñas no coinciden.'
    return
  }

  isSubmitting.value = true
  errorMessage.value = null

  try {
    const response = await fetch('/api/v1/setup/configure', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        nombre_institucion: nombreInstitucion.value,
        nit: nit.value,
        codigo_dane: codigoDane.value,
        direccion: direccion.value,
        telefono_contacto: telefonoContacto.value || null,
        correo_contacto: correoContacto.value || null,
        nombre_rector: nombreRector.value || null,
        gemini_api_key: geminiApiKey.value || null,
        pei_nombre_archivo: peiData.value?.nombre_archivo || null,
        pei_modelo_pedagogico: peiData.value?.perfil_extraido?.modelo_pedagogico || null,
        pei_valores_principios: peiData.value?.perfil_extraido || {},
        admin_email: adminEmail.value,
        admin_password: adminPassword.value,
        admin_nombre: adminNombre.value,
        admin_apellido: adminApellido.value,
        admin_cargo: adminCargo.value,
      }),
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Error al completar la configuración inicial.')
    }

    // Actualizar el estado de setup en el store
    await authStore.checkSetupStatus()
    
    // Redirigir al login
    router.push('/login')
  } catch (err: any) {
    errorMessage.value = err.message || 'Error en el servidor durante la configuración.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 md:p-8 bg-[#F8F9FD]">
    <div class="glass-card max-w-[800px] w-full bg-white overflow-hidden shadow-lg flex flex-col min-h-[600px]">
      
      <!-- Top Wizard Header / Indicator -->
      <header class="bg-primary p-md text-on-primary flex flex-col md:flex-row md:justify-between md:items-center gap-sm">
        <div>
          <div class="flex items-center gap-xs mb-xs">
            <span class="material-symbols-outlined text-[28px] text-white">construction</span>
            <span class="font-display text-headline-md tracking-tight text-white">Configuración Inicial</span>
          </div>
          <p class="font-body-md text-body-md text-primary-fixed-dim">
            Asistente de configuración paso a paso para OpenPiar
          </p>
        </div>
        
        <!-- Step Indicators -->
        <div class="flex items-center gap-xs select-none">
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-label-md text-label-md"
            :class="currentStep >= 1 ? 'bg-white text-primary font-bold' : 'bg-primary-container text-primary-fixed-dim'"
          >
            1
          </div>
          <div class="w-8 h-[2px] bg-primary-container"></div>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-label-md text-label-md"
            :class="currentStep >= 2 ? 'bg-white text-primary font-bold' : 'bg-primary-container text-primary-fixed-dim'"
          >
            2
          </div>
          <div class="w-8 h-[2px] bg-primary-container"></div>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-label-md text-label-md"
            :class="currentStep >= 3 ? 'bg-white text-primary font-bold' : 'bg-primary-container text-primary-fixed-dim'"
          >
            3
          </div>
          <div class="w-8 h-[2px] bg-primary-container"></div>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-label-md text-label-md"
            :class="currentStep >= 4 ? 'bg-white text-primary font-bold' : 'bg-primary-container text-primary-fixed-dim'"
          >
            4
          </div>
        </div>
      </header>

      <!-- Error message container -->
      <div v-if="errorMessage" class="p-sm bg-error-container text-on-error-container border-b border-error/15 flex items-start gap-xs">
        <span class="material-symbols-outlined text-error">error</span>
        <div class="text-body-md font-body-md">{{ errorMessage }}</div>
      </div>

      <!-- Main Step Forms -->
      <main class="p-md md:p-xl flex-grow flex flex-col justify-between">
        
        <!-- STEP 1: INSTITUCIÓN -->
        <div v-if="currentStep === 1" class="space-y-md">
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">Datos de la Institución</h2>
            <p class="font-body-md text-body-md text-on-surface-variant">Ingresa los datos oficiales de tu establecimiento educativo.</p>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="nombre">Nombre de la Institución *</label>
              <input
                id="nombre"
                v-model="nombreInstitucion"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. Colegio Integrado Nacional"
                type="text"
              />
            </div>
            
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="nit">NIT *</label>
              <input
                id="nit"
                v-model="nit"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. 900.123.456-7"
                type="text"
              />
            </div>
            
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="dane">Código DANE (12 dígitos) *</label>
              <input
                id="dane"
                v-model="codigoDane"
                maxlength="12"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                :class="codigoDane && !daneIsValid ? 'border-error ring-error/10' : ''"
                placeholder="Ej. 111001123456"
                type="text"
              />
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="direccion">Dirección *</label>
              <input
                id="direccion"
                v-model="direccion"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. Calle 10 # 5-20"
                type="text"
              />
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="telefono">Teléfono de Contacto</label>
              <input
                id="telefono"
                v-model="telefonoContacto"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. (601) 321-4567"
                type="text"
              />
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="correo">Correo de Contacto</label>
              <input
                id="correo"
                v-model="correoContacto"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. contacto@colegio.edu.co"
                type="email"
              />
            </div>

            <div class="space-y-xs md:col-span-2">
              <label class="font-label-md text-label-md text-on-surface-variant" for="rector">Nombre del Rector / Director rural</label>
              <input
                id="rector"
                v-model="nombreRector"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. Lic. Carlos Gómez Soler"
                type="text"
              />
            </div>
          </div>
        </div>

        <!-- STEP 2: INTELIGENCIA ARTIFICIAL -->
        <div v-if="currentStep === 2" class="space-y-md">
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">Configuración de Inteligencia Artificial</h2>
            <p class="font-body-md text-body-md text-on-surface-variant">
              OpenPiar utiliza el SDK de Google Gen AI para ayudar a los docentes a diseñar planes pedagógicos.
            </p>
          </div>
          
          <div class="bg-surface-container-low p-md rounded-input space-y-sm border border-outline-variant/30">
            <h3 class="font-label-md text-label-md text-primary flex items-center gap-xs">
              <span class="material-symbols-outlined text-[20px]">lightbulb</span>
              ¿Cómo obtener la API Key?
            </h3>
            <p class="font-body-md text-body-md text-on-surface-variant">
              Puedes crear una clave gratuita en la plataforma de Google AI Studio. Esta clave le da acceso a los modelos Gemini para autogenerar sugerencias DUA del PIAR.
            </p>
            <a
              href="https://aistudio.google.com/"
              target="_blank"
              class="inline-flex items-center gap-xs text-primary font-bold font-label-md hover:underline"
            >
              Ir a Google AI Studio
              <span class="material-symbols-outlined text-[16px]">open_in_new</span>
            </a>
          </div>

          <div class="space-y-xs pt-sm">
            <label class="font-label-md text-label-md text-on-surface-variant" for="gemini">Gemini API Key (Opcional)</label>
            <input
              id="gemini"
              v-model="geminiApiKey"
              class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
              placeholder="AIzaSy..."
              type="password"
            />
            <p class="font-label-sm text-label-sm text-on-surface-variant">
              Si la dejas en blanco, podrás configurarla posteriormente desde el panel directivo de administración.
            </p>
          </div>
        </div>

        <!-- STEP 3: PEI UPLOAD -->
        <div v-if="currentStep === 3" class="space-y-md">
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">Proyecto Educativo Institucional (PEI)</h2>
            <p class="font-body-md text-body-md text-on-surface-variant">Sube el documento oficial de tu colegio en PDF para que Gemini extraiga automáticamente los valores y el modelo pedagógico.</p>
          </div>

          <div class="bg-surface-container border-2 border-dashed border-outline-variant rounded-xl p-xl flex flex-col items-center justify-center text-center">
            <span class="material-symbols-outlined text-6xl text-primary mb-sm">upload_file</span>
            
            <label for="pei-upload" class="cursor-pointer bg-primary text-on-primary font-bold py-3 px-6 rounded-full hover:bg-primary/90 transition-colors inline-flex items-center gap-xs shadow-sm">
              <span class="material-symbols-outlined text-[20px]">file_upload</span>
              Seleccionar documento
            </label>
            <input 
              id="pei-upload"
              type="file" 
              accept=".pdf" 
              @change="handleFileUpload"
              class="hidden"
            />
            
            <p v-if="peiFile" class="mt-md text-label-md font-bold text-on-surface flex items-center gap-xs">
              <span class="material-symbols-outlined text-[18px] text-[#166534]">check_circle</span>
              {{ peiFile.name }}
            </p>
            <p v-else class="mt-md text-label-sm text-on-surface-variant">Solo formato PDF. Máximo 30 páginas serán leídas.</p>
          </div>

          <!-- Error del PEI -->
          <div v-if="peiUploadError" class="p-sm bg-error-container text-on-error-container rounded-lg flex items-start gap-xs">
            <span class="material-symbols-outlined text-[20px] text-error">error</span>
            <p class="text-body-sm font-bold">{{ peiUploadError }}</p>
          </div>

          <!-- Botón de extracción -->
          <div class="flex justify-center mt-md">
            <button
              @click="uploadPEI"
              :disabled="!peiFile || isUploadingPei"
              class="px-xl py-3 bg-tertiary text-on-tertiary font-bold rounded-full flex items-center gap-2 shadow-md hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <span class="material-symbols-outlined animate-spin" v-if="isUploadingPei">sync</span>
              <span class="material-symbols-outlined" v-else>memory</span>
              {{ isUploadingPei ? 'Analizando documento con IA...' : 'Extraer Principios (Gemini)' }}
            </button>
          </div>
        </div>

        <!-- STEP 4: ADMINISTRADOR -->
        <div v-if="currentStep === 4" class="space-y-md">
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">Usuario Administrador</h2>
            <p class="font-body-md text-body-md text-on-surface-variant">Registra los datos del docente o directivo encargado de administrar la plataforma.</p>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-nombre">Nombres *</label>
              <input
                id="admin-nombre"
                v-model="adminNombre"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. Ana Lucía"
                type="text"
              />
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-apellido">Apellidos *</label>
              <input
                id="admin-apellido"
                v-model="adminApellido"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Ej. Ortega Restrepo"
                type="text"
              />
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-cargo">Cargo del Administrador *</label>
              <select
                id="admin-cargo"
                v-model="adminCargo"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10 cursor-pointer"
              >
                <option value="" disabled selected>Selecciona una opción</option>
                <option value="Rector">Rector</option>
                <option value="Coordinador">Coordinador</option>
                <option value="Docente encargado">Docente encargado</option>
              </select>
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-email">Correo Electrónico *</label>
              <input
                id="admin-email"
                v-model="adminEmail"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="admin@colegio.edu.co"
                type="email"
              />
              <p class="font-label-sm text-label-sm text-primary font-bold">
                Nota: Se usará para restablecer la contraseña si la olvidas.
              </p>
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-password">Contraseña *</label>
              <input
                id="admin-password"
                v-model="adminPassword"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Mínimo 8 caracteres"
                type="password"
              />
              
              <!-- Real-time Password Strength Criteria Display -->
              <div class="pt-1 grid grid-cols-2 gap-xs">
                <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasMinLength ? 'text-[#166534]' : 'text-on-surface-variant'">
                  <span class="material-symbols-outlined text-[16px]">{{ hasMinLength ? 'check_circle' : 'circle' }}</span> Mín. 8 caracteres
                </span>
                <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasLetter ? 'text-[#166534]' : 'text-on-surface-variant'">
                  <span class="material-symbols-outlined text-[16px]">{{ hasLetter ? 'check_circle' : 'circle' }}</span> Al menos una letra
                </span>
                <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasNumber ? 'text-[#166534]' : 'text-on-surface-variant'">
                  <span class="material-symbols-outlined text-[16px]">{{ hasNumber ? 'check_circle' : 'circle' }}</span> Al menos un número
                </span>
                <span class="flex items-center gap-1 font-label-sm text-label-sm" :class="hasSpecialChar ? 'text-[#166534]' : 'text-on-surface-variant'">
                  <span class="material-symbols-outlined text-[16px]">{{ hasSpecialChar ? 'check_circle' : 'circle' }}</span> Un carácter especial
                </span>
              </div>
            </div>

            <div class="space-y-xs">
              <label class="font-label-md text-label-md text-on-surface-variant" for="admin-confirm">Confirmar Contraseña *</label>
              <input
                id="admin-confirm"
                v-model="adminConfirmPassword"
                class="w-full px-4 py-3 bg-surface border border-outline-variant rounded-input font-body-md focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                placeholder="Repite la contraseña"
                type="password"
              />
              <span v-if="adminConfirmPassword && !passwordsMatch" class="text-error font-label-sm text-label-sm block">
                Las contraseñas no coinciden.
              </span>
            </div>
          </div>
        </div>

        <!-- Buttons navigation -->
        <div class="pt-xl flex justify-between items-center gap-md border-t border-outline-variant/30 mt-lg">
          <button
            v-if="currentStep > 1"
            @click="prevStep"
            class="px-lg py-3 bg-surface border border-outline-variant hover:bg-surface-container-low rounded-input font-label-md text-label-md cursor-pointer transition-all flex items-center gap-xs"
            type="button"
            :disabled="isSubmitting"
          >
            <span class="material-symbols-outlined text-[18px]">arrow_back</span>
            Atrás
          </button>
          <div v-else></div> <!-- Spacer -->

          <button
            v-if="currentStep < 4"
            @click="nextStep"
            class="px-lg py-3 bg-primary text-on-primary font-label-md text-label-md rounded-input shadow-md btn-hover-effect cursor-pointer flex items-center gap-xs ml-auto"
            type="button"
          >
            Siguiente
            <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
          
          <button
            v-else
            @click="handleConfigure"
            class="px-lg py-3 bg-[#166534] hover:bg-[#15803d] text-white font-label-md text-label-md rounded-input shadow-md flex items-center justify-center gap-xs cursor-pointer disabled:opacity-75 disabled:pointer-events-none transition-all ml-auto"
            type="button"
            :disabled="isSubmitting || !passwordIsValid || !passwordsMatch"
          >
            <template v-if="isSubmitting">
              <span class="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
              Configurando...
            </template>
            <template v-else>
              Guardar y Finalizar
              <span class="material-symbols-outlined text-[20px]">check_circle</span>
            </template>
          </button>
        </div>

      </main>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
