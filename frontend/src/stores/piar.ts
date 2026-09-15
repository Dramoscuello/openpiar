// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'
import type { PiarCompletitud } from '../types/piar'

export const usePiarStore = defineStore('piar', () => {
  const activePiar = ref<any>(null)
  const isGeneratingAI = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchPiarForStudent(estudianteId: string, periodoId?: number | null) {
    isLoading.value = true
    error.value = null
    const authStore = useAuthStore()
    try {
      const query = periodoId ? `?periodo_id=${periodoId}` : ''
      const response = await fetch(`/api/v1/piars/estudiante/${estudianteId}${query}`, {
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
      const response = await fetch(`/api/v1/piars/`, {
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
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/generar_ia`, {
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

  async function saveAjuste(data: { asignaturaId?: string | null, area: string, tituloTema: string, objetivos: string, barreras: string, ajustes: string, tipoAjuste?: string | null, apoyoRequerido?: string | null, temporalidad?: string | null, responsable?: string | null, mediosVerificacion?: string | null, dbaReferencia?: string | null }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/ajustes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          asignatura_id: data.asignaturaId || null,
          area: data.area,
          titulo_tema: data.tituloTema,
          objetivos_propositos: data.objetivos,
          barreras_evidenciadas: data.barreras,
          ajustes_estrategias: data.ajustes,
          evaluacion_ajustes: '',
          tipo_ajuste: data.tipoAjuste || null,
          apoyo_requerido: data.apoyoRequerido || null,
          temporalidad: data.temporalidad || null,
          responsable: data.responsable || null,
          medios_verificacion: data.mediosVerificacion || null,
          dba_referencia: data.dbaReferencia || null,
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

  async function updateAjuste(data: { ajusteId: string, asignaturaId?: string | null, area: string, tituloTema: string, objetivos: string, barreras: string, ajustes: string, evaluacion: string, tipoAjuste?: string | null, apoyoRequerido?: string | null, temporalidad?: string | null, responsable?: string | null, mediosVerificacion?: string | null, dbaReferencia?: string | null }) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/ajustes/${data.ajusteId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          asignatura_id: data.asignaturaId || null,
          area: data.area,
          titulo_tema: data.tituloTema,
          objetivos_propositos: data.objetivos,
          barreras_evidenciadas: data.barreras,
          ajustes_estrategias: data.ajustes,
          evaluacion_ajustes: data.evaluacion,
          tipo_ajuste: data.tipoAjuste || null,
          apoyo_requerido: data.apoyoRequerido || null,
          temporalidad: data.temporalidad || null,
          responsable: data.responsable || null,
          medios_verificacion: data.mediosVerificacion || null,
          dba_referencia: data.dbaReferencia || null,
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
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/ajustes/${ajusteId}`, {
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

  async function puntuarAjuste(ajusteId: string, puntuacion: number, comentario: string | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/ajustes/${ajusteId}/puntuacion`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({ puntuacion, comentario })
      })
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Error al puntuar ajuste')
      }
      const updatedAjuste = await response.json()
      const index = activePiar.value.ajustes_razonables.findIndex((a: any) => a.id === ajusteId)
      if (index !== -1) {
        activePiar.value.ajustes_razonables[index] = {
          ...activePiar.value.ajustes_razonables[index],
          ...updatedAjuste,
        }
      }
      return updatedAjuste
    } catch (e: any) {
      error.value = e.message
      throw e
    }
  }

  async function updatePiar(docentesElaboran: string, caracteristicas?: Record<string, any>, lugarDiligenciamiento?: string, periodoId?: number | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const query = periodoId ? `?periodo_id=${periodoId}` : ''
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}${query}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          docentes_elaboran: docentesElaboran,
          lugar_diligenciamiento: lugarDiligenciamiento || undefined,
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

  async function firmarPiar(periodoId?: number | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')

    const authStore = useAuthStore()
    try {
      const query = periodoId ? `?periodo_id=${periodoId}` : ''
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/finalizar${query}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail?.mensaje || err.detail || 'Error al finalizar el PIAR')
      }
      const version = await response.json()
      activePiar.value.estado = 'firmado'
      activePiar.value.version_actual = version.numero
      activePiar.value.versiones = [...(activePiar.value.versiones || []), version]
      return version
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
  }, periodoId?: number | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    
    const authStore = useAuthStore()
    try {
      const response = await fetch(`/api/v1/piars/${activePiar.value.id}/acta`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify({
          periodo_id: periodoId ?? null,
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

  function downloadPiarPDF(modo: 'borrador' | 'final' = 'borrador', periodoId?: number | null) {
    if (!activePiar.value) return
    const authStore = useAuthStore()
    const query = periodoId ? `&periodo_id=${periodoId}` : ''
    fetch(`/api/v1/piars/${activePiar.value!.id}/pdf?modo=${modo}${query}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    .then(response => {
      if (!response.ok) return response.json().then(body => { throw new Error(body.detail?.mensaje || body.detail || 'Error al descargar el PDF') })
      return response.blob()
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `PIAR_${activePiar.value?.id}_${modo}.pdf`
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

  async function fetchCompletitud(periodoId?: number | null): Promise<PiarCompletitud | null> {
    if (!activePiar.value) return null
    const authStore = useAuthStore()
    const query = periodoId ? `?periodo_id=${periodoId}` : ''
    const response = await fetch(`/api/v1/piars/${activePiar.value.id}/completitud${query}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` },
    })
    if (!response.ok) throw new Error('No fue posible consultar el progreso del PIAR.')
    return await response.json() as PiarCompletitud
  }

  async function updateAsignaturaEstado(asignaturaId: string, estado: 'pendiente' | 'no_requiere', justificacion: string, periodoId?: number | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    const authStore = useAuthStore()
    const query = periodoId ? `?periodo_id=${periodoId}` : ''
    const response = await fetch(`/api/v1/piars/${activePiar.value.id}/asignaturas/${asignaturaId}${query}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({ estado, justificacion }),
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || 'No fue posible actualizar la asignatura.')
    }
    const updated = await response.json()
    const index = (activePiar.value.asignaturas_estado || []).findIndex((item: any) => item.asignatura_id === asignaturaId)
    if (index >= 0) activePiar.value.asignaturas_estado[index] = updated
    return updated
  }

  async function reabrirPiar(periodoId?: number | null) {
    if (!activePiar.value) throw new Error('No hay PIAR activo')
    const authStore = useAuthStore()
    const query = periodoId ? `?periodo_id=${periodoId}` : ''
    const response = await fetch(`/api/v1/piars/${activePiar.value.id}/reabrir${query}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || 'No fue posible reabrir el PIAR.')
    }
    activePiar.value = await response.json()
    return activePiar.value
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
    puntuarAjuste,
    updatePiar,
    firmarPiar,
    saveActaAcuerdo,
    downloadPiarPDF,
    fetchCompletitud,
    updateAsignaturaEstado,
    reabrirPiar,
  }
})
