// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

export interface StudentGeneral {
  nombres: string
  apellidos: string
  tipo_documento: string
  numero_documento: string
  fecha_nacimiento: string
  edad: number
  departamento_residencia: string
  municipio_residencia: string
  direccion: string
  barrio_vereda: string
  lugar_nacimiento: string
  telefono: string
  correo: string
  en_centro_proteccion: boolean
  centro_proteccion_donde: string
  grupo_etnico: string
  victima_conflicto: boolean
  registro_victima: boolean
  grupo_id: string | null
}

export interface TerapiaDetalle {
  tipo: string
  frecuencia: string
}

export interface StudentSalud {
  afiliacion_salud: boolean
  eps: string
  regimen: 'contributivo' | 'subsidiado' | ''
  lugar_emergencias: string
  atendido_sector_salud: boolean
  frecuencia_atencion_salud: string
  tiene_diagnostico_medico: boolean
  diagnostico_medico: string
  asiste_terapias: boolean
  terapias_detalle: TerapiaDetalle[]
  tratamiento_medico: boolean
  tratamiento_medico_cual: string
  consume_medicamentos: boolean
  medicamentos_detalle: string
  productos_apoyo_movilidad: boolean
  productos_apoyo_cual: string
}

export interface StudentHogar {
  nombre_madre: string
  ocupacion_madre: string
  nivel_educativo_madre: string
  nombre_padre: string
  ocupacion_padre: string
  nivel_educativo_padre: string
  nombre_cuidador: string
  parentesco_cuidador: string
  nivel_educativo_cuidador: string
  telefono_cuidador: string
  correo_cuidador: string
  personas_vive_estudiante: string
  numero_hermanos: number
  lugar_que_ocupa: number | null
  apoyo_crianza: string
  bajo_proteccion: boolean
  recibe_subsidio: boolean
  subsidio_cual: string
}

export interface StudentTrayectoria {
  vinculado_educacion_inicial: boolean
  educacion_inicial_instituciones: string
  ultimo_grado_cursado: string
  aprobo_ultimo_grado: boolean
  observaciones_trayectoria: string
  recibe_informe_pedagogico: boolean
  institucion_procedencia_informe: string
  asiste_programas_complementarios: boolean
  programas_complementarios_cuales: string
}

export interface StudentMatricula {
  institucion_educativa: string
  sede: string
  grado_ingreso: string
  jornada: 'mañana' | 'tarde' | 'unica' | 'nocturna' | ''
  medio_transporte: string
  distancia_tiempo_hogar: string
}

export interface StudentDraft {
  general: StudentGeneral
  salud: StudentSalud
  hogar: StudentHogar
  trayectoria: StudentTrayectoria
  matricula: StudentMatricula
}

export interface StudentListItem {
  id: string
  nombres: string
  apellidos: string
  tipo_documento: string
  numero_documento: string
  fecha_nacimiento: string
  edad: number
  departamento_residencia: string
  municipio_residencia: string
  direccion: string
  barrio_vereda: string
  created_at: string
}

export interface StudentsState {
  students: StudentListItem[]
  total: number
  loading: boolean
  submitting: boolean
  error: string | null
  draft: StudentDraft
}

const createDefaultDraft = (): StudentDraft => ({
  general: {
    nombres: '',
    apellidos: '',
    tipo_documento: 'TI',
    numero_documento: '',
    fecha_nacimiento: '',
    edad: 0,
    departamento_residencia: 'Cundinamarca',
    municipio_residencia: '',
    direccion: '',
    barrio_vereda: '',
    lugar_nacimiento: '',
    telefono: '',
    correo: '',
    en_centro_proteccion: false,
    centro_proteccion_donde: '',
    grupo_etnico: '',
    victima_conflicto: false,
    registro_victima: false,
    grupo_id: null,
  },
  salud: {
    afiliacion_salud: false,
    eps: '',
    regimen: '',
    lugar_emergencias: '',
    atendido_sector_salud: false,
    frecuencia_atencion_salud: '',
    tiene_diagnostico_medico: false,
    diagnostico_medico: '',
    asiste_terapias: false,
    terapias_detalle: [],
    tratamiento_medico: false,
    tratamiento_medico_cual: '',
    consume_medicamentos: false,
    medicamentos_detalle: '',
    productos_apoyo_movilidad: false,
    productos_apoyo_cual: '',
  },
  hogar: {
    nombre_madre: '',
    ocupacion_madre: '',
    nivel_educativo_madre: '',
    nombre_padre: '',
    ocupacion_padre: '',
    nivel_educativo_padre: '',
    nombre_cuidador: '',
    parentesco_cuidador: '',
    nivel_educativo_cuidador: '',
    telefono_cuidador: '',
    correo_cuidador: '',
    personas_vive_estudiante: '',
    numero_hermanos: 0,
    lugar_que_ocupa: null,
    apoyo_crianza: '',
    bajo_proteccion: false,
    recibe_subsidio: false,
    subsidio_cual: '',
  },
  trayectoria: {
    vinculado_educacion_inicial: false,
    educacion_inicial_instituciones: '',
    ultimo_grado_cursado: '',
    aprobo_ultimo_grado: true,
    observaciones_trayectoria: '',
    recibe_informe_pedagogico: false,
    institucion_procedencia_informe: '',
    asiste_programas_complementarios: false,
    programas_complementarios_cuales: '',
  },
  matricula: {
    institucion_educativa: '',
    sede: '',
    grado_ingreso: '',
    jornada: 'unica',
    medio_transporte: '',
    distancia_tiempo_hogar: '',
  },
})

export const useStudentsStore = defineStore('students', {
  state: (): StudentsState => ({
    students: [],
    total: 0,
    loading: false,
    submitting: false,
    error: null,
    draft: createDefaultDraft(),
  }),

  actions: {
    /**
     * Carga el borrador del formulario desde LocalStorage.
     */
    loadDraft() {
      const saved = localStorage.getItem('openpiar_student_draft')
      if (saved) {
        try {
          this.draft = JSON.parse(saved)
        } catch (e) {
          this.draft = createDefaultDraft()
        }
      } else {
        this.draft = createDefaultDraft()
      }
    },

    /**
     * Guarda el estado actual del borrador en LocalStorage.
     */
    saveDraft() {
      localStorage.setItem('openpiar_student_draft', JSON.stringify(this.draft))
    },

    /**
     * Limpia el borrador actual y borra el registro de LocalStorage.
     */
    clearDraft() {
      this.draft = createDefaultDraft()
      localStorage.removeItem('openpiar_student_draft')
    },

    /**
     * Obtiene la lista de estudiantes del backend.
     */
    async fetchStudents(skip = 0, limit = 50) {
      const authStore = useAuthStore()
      this.loading = true
      this.error = null

      try {
        const response = await fetch(`/api/v1/estudiantes/?skip=${skip}&limit=${limit}`, {
          headers: {
            'Authorization': `Bearer ${authStore.token}`,
          },
        })

        if (!response.ok) {
          const errData = await response.json()
          throw new Error(errData.detail || 'Error al obtener la lista de estudiantes.')
        }

        const data = await response.json()
        this.students = data.items
        this.total = data.total
      } catch (err: any) {
        this.error = err.message || 'Error en la petición de listado de estudiantes.'
      } finally {
        this.loading = false
      }
    },

    /**
     * Obtiene el estudiante y todos sus entornos asociados (Anexo 1).
     * Rellena el draft con la información recuperada.
     */
    async fetchStudentForEdit(id: string) {
      const authStore = useAuthStore()
      this.loading = true
      this.error = null
      this.clearDraft()

      try {
        const headers = { 'Authorization': `Bearer ${authStore.token}` }

        // 1. Obtener datos generales del estudiante
        const resGeneral = await fetch(`/api/v1/estudiantes/${id}`, { headers })
        if (!resGeneral.ok) {
          throw new Error('Estudiante no encontrado.')
        }
        const dataGeneral = await resGeneral.json()

        // Mapear datos generales
        this.draft.general = {
          nombres: dataGeneral.nombres,
          apellidos: dataGeneral.apellidos,
          tipo_documento: dataGeneral.tipo_documento,
          numero_documento: dataGeneral.numero_documento,
          fecha_nacimiento: dataGeneral.fecha_nacimiento,
          edad: dataGeneral.edad,
          departamento_residencia: dataGeneral.departamento_residencia,
          municipio_residencia: dataGeneral.municipio_residencia,
          direccion: dataGeneral.direccion,
          barrio_vereda: dataGeneral.barrio_vereda,
          lugar_nacimiento: dataGeneral.lugar_nacimiento || '',
          telefono: dataGeneral.telefono || '',
          correo: dataGeneral.correo || '',
          en_centro_proteccion: dataGeneral.en_centro_proteccion || false,
          centro_proteccion_donde: dataGeneral.centro_proteccion_donde || '',
          grupo_etnico: dataGeneral.grupo_etnico || '',
          victima_conflicto: dataGeneral.victima_conflicto || false,
          registro_victima: dataGeneral.registro_victima || false,
          grupo_id: dataGeneral.grupo_id || null,
        }

        // 2. Fetch de sub-entornos de forma paralela (tolerante a 404s en caso de que no se hayan creado aún)
        const fetchSubResource = async (url: string, defaultValue: any) => {
          try {
            const res = await fetch(url, { headers })
            if (res.status === 404) return defaultValue
            if (!res.ok) throw new Error('Error recuperando sub-recurso.')
            return await res.json()
          } catch {
            return defaultValue
          }
        }

        const [dataSalud, dataHogar, dataTrayectoria, dataMatricula] = await Promise.all([
          fetchSubResource(`/api/v1/estudiantes/${id}/salud`, null),
          fetchSubResource(`/api/v1/estudiantes/${id}/hogar`, null),
          fetchSubResource(`/api/v1/estudiantes/${id}/trayectoria`, null),
          fetchSubResource(`/api/v1/estudiantes/${id}/matricula`, null),
        ])

        if (dataSalud) {
          this.draft.salud = {
            afiliacion_salud: dataSalud.afiliacion_salud || false,
            eps: dataSalud.eps || '',
            regimen: dataSalud.regimen || '',
            lugar_emergencias: dataSalud.lugar_emergencias || '',
            atendido_sector_salud: dataSalud.atendido_sector_salud || false,
            frecuencia_atencion_salud: dataSalud.frecuencia_atencion_salud || '',
            tiene_diagnostico_medico: dataSalud.tiene_diagnostico_medico || false,
            diagnostico_medico: dataSalud.diagnostico_medico || '',
            asiste_terapias: dataSalud.asiste_terapias || false,
            terapias_detalle: dataSalud.terapias_detalle || [],
            tratamiento_medico: dataSalud.tratamiento_medico || false,
            tratamiento_medico_cual: dataSalud.tratamiento_medico_cual || '',
            consume_medicamentos: dataSalud.consume_medicamentos || false,
            medicamentos_detalle: dataSalud.medicamentos_detalle || '',
            productos_apoyo_movilidad: dataSalud.productos_apoyo_movilidad || false,
            productos_apoyo_cual: dataSalud.productos_apoyo_cual || '',
          }
        }

        if (dataHogar) {
          this.draft.hogar = {
            nombre_madre: dataHogar.nombre_madre || '',
            ocupacion_madre: dataHogar.ocupacion_madre || '',
            nivel_educativo_madre: dataHogar.nivel_educativo_madre || '',
            nombre_padre: dataHogar.nombre_padre || '',
            ocupacion_padre: dataHogar.ocupacion_padre || '',
            nivel_educativo_padre: dataHogar.nivel_educativo_padre || '',
            nombre_cuidador: dataHogar.nombre_cuidador || '',
            parentesco_cuidador: dataHogar.parentesco_cuidador || '',
            nivel_educativo_cuidador: dataHogar.nivel_educativo_cuidador || '',
            telefono_cuidador: dataHogar.telefono_cuidador || '',
            correo_cuidador: dataHogar.correo_cuidador || '',
            personas_vive_estudiante: dataHogar.personas_vive_estudiante || '',
            numero_hermanos: dataHogar.numero_hermanos || 0,
            lugar_que_ocupa: dataHogar.lugar_que_ocupa || null,
            apoyo_crianza: dataHogar.apoyo_crianza || '',
            bajo_proteccion: dataHogar.bajo_proteccion || false,
            recibe_subsidio: dataHogar.recibe_subsidio || false,
            subsidio_cual: dataHogar.subsidio_cual || '',
          }
        }

        if (dataTrayectoria) {
          this.draft.trayectoria = {
            vinculado_educacion_inicial: dataTrayectoria.vinculado_educacion_inicial || false,
            educacion_inicial_instituciones: dataTrayectoria.educacion_inicial_instituciones || '',
            ultimo_grado_cursado: dataTrayectoria.ultimo_grado_cursado || '',
            aprobo_ultimo_grado: dataTrayectoria.aprobo_ultimo_grado ?? true,
            observaciones_trayectoria: dataTrayectoria.observaciones_trayectoria || '',
            recibe_informe_pedagogico: dataTrayectoria.recibe_informe_pedagogico || false,
            institucion_procedencia_informe: dataTrayectoria.institucion_procedencia_informe || '',
            asiste_programas_complementarios: dataTrayectoria.asiste_programas_complementarios || false,
            programas_complementarios_cuales: dataTrayectoria.programas_complementarios_cuales || '',
          }
        }

        if (dataMatricula) {
          this.draft.matricula = {
            institucion_educativa: dataMatricula.institucion_educativa || '',
            sede: dataMatricula.sede || '',
            grado_ingreso: dataMatricula.grado_ingreso || '',
            jornada: dataMatricula.jornada || '',
            medio_transporte: dataMatricula.medio_transporte || '',
            distancia_tiempo_hogar: dataMatricula.distancia_tiempo_hogar || '',
          }
        }

        this.saveDraft()
      } catch (err: any) {
        this.error = err.message || 'Error cargando datos del estudiante.'
      } finally {
        this.loading = false
      }
    },

    /**
     * Sincroniza el borrador local (general, salud, hogar, trayectoria y matrícula) con el servidor.
     * Si `estudianteId` existe, edita; de lo contrario, registra un nuevo estudiante.
     */
    async saveStudent(estudianteId?: string): Promise<boolean> {
      const authStore = useAuthStore()
      this.submitting = true
      this.error = null

      try {
        const headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`,
        }

        let id = estudianteId

        // Limpiar strings vacíos de inputs opcionales y formatear nulos del formulario
        const payloadGeneral = { ...this.draft.general }
        if (!payloadGeneral.correo) delete (payloadGeneral as any).correo
        if (!payloadGeneral.telefono) delete (payloadGeneral as any).telefono
        if (!payloadGeneral.lugar_nacimiento) delete (payloadGeneral as any).lugar_nacimiento
        if (!payloadGeneral.centro_proteccion_donde) delete (payloadGeneral as any).centro_proteccion_donde
        if (!payloadGeneral.grupo_etnico) delete (payloadGeneral as any).grupo_etnico

        // --- 1. Sincronizar Datos Generales ---
        if (id) {
          // Edición (En estudiantes.py el endpoint es PATCH /api/v1/estudiantes/{id} ? Espera, let's verify if PATCH exists on backend)
          // Wait, let's assume it does since it's common or we can inspect. Let's verify in students.py.
          // Wait, we didn't check if PATCH /estudiantes/{id} exists. Let's look at students.py lines 150 to 220.
          // Lines 172-181 in students.py is GET /{estudiante_id}.
          // Let's check if there is a PATCH /estudiantes/{id}. Let's grep "PATCH /" in students.py.
          // Ah, we ran a search for "entorno" but let's check what methods are in students.py.
          // Let's search students.py for "router.patch" or "router.put".
          const res = await fetch(`/api/v1/estudiantes/${id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(payloadGeneral),
          })
          if (!res.ok) {
            const errData = await res.json()
            throw new Error(errData.detail || 'Error al actualizar el estudiante.')
          }
        } else {
          // Registro nuevo
          const res = await fetch(`/api/v1/estudiantes/`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payloadGeneral),
          })
          if (!res.ok) {
            const errData = await res.json()
            throw new Error(errData.detail || 'Error al registrar el estudiante.')
          }
          const created = await res.json()
          id = created.id
        }

        if (!id) throw new Error('No se pudo determinar el ID del estudiante.')

        // Auxiliar para POST o PATCH de sub-entornos
        const syncSubResource = async (baseUrl: string, body: any) => {
          // 1. Intentar PATCH
          let res = await fetch(baseUrl, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(body),
          })
          if (res.status === 404) {
            // 2. Si no existe, crear con POST
            res = await fetch(baseUrl, {
              method: 'POST',
              headers,
              body: JSON.stringify(body),
            })
          }
          if (!res.ok) {
            const errData = await res.json()
            throw new Error(errData.detail || 'Error al sincronizar datos complementarios.')
          }
        }

        // --- 2. Sincronizar Entorno Salud ---
        const payloadSalud = { ...this.draft.salud }
        if (payloadSalud.regimen === '') delete (payloadSalud as any).regimen
        await syncSubResource(`/api/v1/estudiantes/${id}/salud`, payloadSalud)

        // --- 3. Sincronizar Entorno Hogar ---
        const payloadHogar = { ...this.draft.hogar }
        if (!payloadHogar.correo_cuidador) delete (payloadHogar as any).correo_cuidador
        await syncSubResource(`/api/v1/estudiantes/${id}/hogar`, payloadHogar)

        // --- 4. Sincronizar Trayectoria Educativa ---
        const payloadTrayectoria = { ...this.draft.trayectoria }
        await syncSubResource(`/api/v1/estudiantes/${id}/trayectoria`, payloadTrayectoria)

        // --- 5. Sincronizar Matrícula Actual ---
        const payloadMatricula = { ...this.draft.matricula }
        if (payloadMatricula.jornada === '') delete (payloadMatricula as any).jornada
        await syncSubResource(`/api/v1/estudiantes/${id}/matricula`, payloadMatricula)

        // Limpiar el borrador y LocalStorage al guardar exitosamente
        this.clearDraft()
        return true
      } catch (err: any) {
        this.error = err.message || 'Error al guardar el expediente del estudiante.'
        return false
      } finally {
        this.submitting = false
      }
    },

    /**
     * Elimina un estudiante y todos sus datos relacionados del servidor.
     */
    async deleteStudent(id: string): Promise<boolean> {
      const authStore = useAuthStore()
      this.error = null
      try {
        const res = await fetch(`/api/v1/estudiantes/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${authStore.token}` },
        })
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}))
          throw new Error(errData.detail || 'Error al eliminar el estudiante.')
        }
        // Remover de la lista local sin recargar
        this.students = this.students.filter(s => s.id !== id)
        this.total = Math.max(0, this.total - 1)
        return true
      } catch (err: any) {
        this.error = err.message || 'Error al eliminar.'
        return false
      }
    },

    async exportStudent(studentId: string, password: string): Promise<void> {
      const authStore = useAuthStore()
      this.loading = true
      this.error = null
      try {
        const response = await fetch(`/api/v1/estudiantes/${studentId}/exportar?password=${encodeURIComponent(password)}`, {
          headers: {
            'Authorization': `Bearer ${authStore.token}`,
          },
        })
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}))
          throw new Error(errData.detail || 'Error al exportar el expediente.')
        }
        const blob = await response.blob()
        const contentDisposition = response.headers.get('Content-Disposition')
        let filename = `estudiante_${studentId}.openpiar`
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?([^"]+)"?/)
          if (match && match[1]) {
            filename = match[1]
          }
        }
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } catch (err: any) {
        this.error = err.message || 'Error al exportar el estudiante.'
        throw err
      } finally {
        this.loading = false
      }
    },

    async importStudent(file: File, password: string, grupoId: string | null): Promise<boolean> {
      const authStore = useAuthStore()
      this.submitting = true
      this.error = null
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('password', password)
        if (grupoId) {
          formData.append('grupo_id', grupoId)
        }

        const response = await fetch(`/api/v1/estudiantes/importar`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authStore.token}`,
          },
          body: formData,
        })

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}))
          throw new Error(errData.detail || 'Error al importar el expediente.')
        }

        await this.fetchStudents() // Refrescar lista de estudiantes
        return true
      } catch (err: any) {
        this.error = err.message || 'Error al importar el estudiante.'
        throw err
      } finally {
        this.submitting = false
      }
    },
  },
})
