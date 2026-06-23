import { defineStore } from 'pinia'
import { ref } from 'vue'

const API_URL = 'http://localhost:8000/api/v1'

export const usePiarStore = defineStore('piar', () => {
  const activePiar = ref<any>(null)
  const isGeneratingAI = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchPiarForStudent(estudianteId: string) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetch(`${API_URL}/piars/estudiante/${estudianteId}`)
      if (response.ok) {
        activePiar.value = await response.json()
      } else if (response.status === 404) {
        // Si no tiene PIAR, podríamos inicializar uno temporal o mostrar estado vacío
        activePiar.value = null
      } else {
        throw new Error('Error al obtener PIAR')
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  async function createPiar(estudianteId: string) {
    try {
      const response = await fetch(`${API_URL}/piars/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          estudiante_id: estudianteId,
          anio_lectivo: new Date().getFullYear(),
          estado: 'borrador'
        })
      })
      if (!response.ok) throw new Error('Error al crear PIAR')
      activePiar.value = await response.json()
      return activePiar.value
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function generateAIAjustes(barreras: string, objetivos: string, area: string, instrucciones: string = '') {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    isGeneratingAI.value = true
    error.value = null
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/generar_ia`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          barreras_evidenciadas: barreras,
          objetivos_propositos: objetivos,
          area: area,
          instrucciones_adicionales: instrucciones
        })
      })
      if (!response.ok) throw new Error('Error en el Agente DUA')
      const data = await response.json()
      return data.estrategias_generadas
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      isGeneratingAI.value = false
    }
  }

  async function saveAjuste(area: string, objetivos: string, barreras: string, ajustes: string) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/ajustes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area: area,
          objetivos_propositos: objetivos,
          barreras_evidenciadas: barreras,
          ajustes_estrategias: ajustes,
          evaluacion_ajustes: ''
        })
      })
      if (!response.ok) throw new Error('Error al guardar ajuste. Verifique que exista un periodo académico activo.')
      const nuevoAjuste = await response.json()
      // Actualizar el estado local
      if (!activePiar.value.ajustes_razonables) activePiar.value.ajustes_razonables = []
      activePiar.value.ajustes_razonables.push(nuevoAjuste)
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  return {
    activePiar,
    isGeneratingAI,
    isLoading,
    error,
    fetchPiarForStudent,
    createPiar,
    generateAIAjustes,
    saveAjuste
  }
})
