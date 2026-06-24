// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'

const API_URL = 'http://localhost:8000/api/v1'

export const usePiarStore = defineStore('piar', () => {
  const activePiar = ref<any>(null)
  const isGeneratingAI = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchPiarForStudent(estudianteId: string) {
    isLoading.value = true
    error.value = null
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/estudiante/${estudianteId}`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (response.ok) {
        activePiar.value = await response.json()
      } else if (response.status === 404) {
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
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
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
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/generar_ia`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
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

  async function saveAjuste(data: { area: string, tituloTema: string, objetivos: string, barreras: string, ajustes: string }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/ajustes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          area: data.area,
          titulo_tema: data.tituloTema,
          objetivos_propositos: data.objetivos,
          barreras_evidenciadas: data.barreras,
          ajustes_estrategias: data.ajustes,
          evaluacion_ajustes: ''
        })
      })
      if (!response.ok) throw new Error('Error al guardar ajuste. Verifique que exista un periodo académico activo.')
      const nuevoAjuste = await response.json()
      if (!activePiar.value.ajustes_razonables) activePiar.value.ajustes_razonables = []
      activePiar.value.ajustes_razonables.push(nuevoAjuste)
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function updateAjuste(data: { ajusteId: string, area: string, tituloTema: string, objetivos: string, barreras: string, ajustes: string, evaluacion: string }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/ajustes/${data.ajusteId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          area: data.area,
          titulo_tema: data.tituloTema,
          objetivos_propositos: data.objetivos,
          barreras_evidenciadas: data.barreras,
          ajustes_estrategias: data.ajustes,
          evaluacion_ajustes: data.evaluacion
        })
      })
      if (!response.ok) throw new Error('Error al actualizar ajuste')
      const updatedAjuste = await response.json()
      const index = activePiar.value.ajustes_razonables.findIndex((a: any) => a.id === data.ajusteId)
      if (index !== -1) {
        activePiar.value.ajustes_razonables[index] = updatedAjuste
      }
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function deleteAjuste(ajusteId: string) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/ajustes/${ajusteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (!response.ok) throw new Error('Error al eliminar ajuste')
      activePiar.value.ajustes_razonables = activePiar.value.ajustes_razonables.filter((a: any) => a.id !== ajusteId)
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function updatePiar(docentesElaboran: string, caracteristicas?: { descripcion_gustos_intereses: string, descripcion_habilidades: string }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          docentes_elaboran: docentesElaboran,
          caracteristicas: caracteristicas
        })
      })
      if (!response.ok) throw new Error('Error al actualizar PIAR')
      const updatedPiar = await response.json()
      activePiar.value = updatedPiar
      return updatedPiar
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function addRecomendacionPMI(actor: string, acciones: string, estrategias: string) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/pmi`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          actor: actor,
          acciones: acciones,
          estrategias_implementar: estrategias
        })
      })
      if (!response.ok) throw new Error('Error al agregar recomendación PMI')
      const nuevaRec = await response.json()
      if (!activePiar.value.recomendaciones_pmi) activePiar.value.recomendaciones_pmi = []
      activePiar.value.recomendaciones_pmi.push(nuevaRec)
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function updateRecomendacionPMI(pmiId: string, actor: string, acciones: string, estrategias: string) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/pmi/${pmiId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          actor: actor,
          acciones: acciones,
          estrategias_implementar: estrategias
        })
      })
      if (!response.ok) throw new Error('Error al actualizar recomendación PMI')
      const updatedRec = await response.json()
      const index = activePiar.value.recomendaciones_pmi.findIndex((r: any) => r.id === pmiId)
      if (index !== -1) {
        activePiar.value.recomendaciones_pmi[index] = updatedRec
      }
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function deleteRecomendacionPMI(pmiId: string) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/pmi/${pmiId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (!response.ok) throw new Error('Error al eliminar recomendación PMI')
      activePiar.value.recomendaciones_pmi = activePiar.value.recomendaciones_pmi.filter((r: any) => r.id !== pmiId)
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function saveActaAcuerdo(data: {
    fechaFirma: string | null,
    compromisosAula: string,
    firmadoEstudiante: boolean,
    firmadoAcudiente: boolean,
    firmadoDocenteApoyo: boolean,
    firmadoDocentesAula: boolean,
    firmadoDirectivo: boolean,
    compromisosCasa: Array<{ nombre_actividad: string, descripcion_estrategia: string, frecuencia: string }>
  }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`${API_URL}/piars/${activePiar.value.id}/acta`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          fecha_firma: data.fechaFirma || null,
          compromisos_aula: data.compromisosAula,
          firmado_estudiante: data.firmadoEstudiante,
          firmado_acudiente: data.firmadoAcudiente,
          firmado_docente_apoyo: data.firmadoDocenteApoyo,
          firmado_docentes_aula: data.firmadoDocentesAula,
          firmado_directivo: data.firmadoDirectivo,
          compromisos_casa: data.compromisosCasa
        })
      })
      if (!response.ok) throw new Error('Error al guardar el acta de acuerdo')
      const actaGuardada = await response.json()
      activePiar.value.acta_acuerdo = actaGuardada
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  function downloadActaPDF() {
    if (!activePiar.value) return
    const authStore = useAuthStore()
    fetch(`${API_URL}/piars/${activePiar.value!.id}/acta/pdf`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    .then(response => {
      if (!response.ok) throw new Error('Error al descargar el PDF')
      return response.blob()
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Acta_Acuerdo_${activePiar.value?.id}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    })
    .catch(e => {
      error.value = e.message
      alert(e.message || 'No se pudo descargar el PDF.')
    })
  }

  return {
    activePiar,
    isGeneratingAI,
    isLoading,
    error,
    fetchPiarForStudent,
    createPiar,
    generateAIAjustes,
    saveAjuste,
    updateAjuste,
    deleteAjuste,
    updatePiar,
    addRecomendacionPMI,
    updateRecomendacionPMI,
    deleteRecomendacionPMI,
    saveActaAcuerdo,
    downloadActaPDF
  }
})
