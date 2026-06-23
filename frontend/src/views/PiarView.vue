<template>
  <div class="flex flex-col h-screen bg-background overflow-hidden font-body-md text-on-surface">
    <!-- Header -->
    <header class="h-20 w-full flex-shrink-0 bg-surface flex justify-between items-center px-lg border-b border-outline-variant/30 shadow-sm z-20">
      <div class="flex items-center gap-4">
        <router-link to="/estudiantes" class="flex items-center justify-center w-10 h-10 rounded-full hover:bg-surface-container-high active:scale-95 transition-all text-on-surface-variant cursor-pointer">
          <span class="material-symbols-outlined">arrow_back</span>
        </router-link>
        <div>
          <h1 class="text-headline-md font-bold text-primary flex items-center gap-2">
            <span class="material-symbols-outlined">description</span>
            Anexo 2: Plan Individual de Ajustes Razonables (PIAR)
          </h1>
          <p v-if="estudiante" class="text-body-md text-on-surface-variant">
            Estudiante: <strong class="text-on-surface font-semibold">{{ estudiante.nombres }} {{ estudiante.apellidos }}</strong> ({{ estudiante.tipo_documento }} {{ estudiante.numero_documento }})
          </p>
        </div>
      </div>
      <div class="flex items-center gap-sm">
        <span v-if="activePiar" class="bg-primary/10 text-primary px-3 py-1 rounded-full text-label-md font-bold uppercase tracking-wider">
          Lectivo: {{ activePiar.anio_lectivo }}
        </span>
        <span v-if="activePiar" class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-label-md font-bold uppercase tracking-wider">
          Estado: {{ activePiar.estado }}
        </span>
      </div>
    </header>

    <!-- Loading / Error States -->
    <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center">
      <span class="material-symbols-outlined animate-spin text-primary text-5xl mb-4">progress_activity</span>
      <p class="text-on-surface-variant font-medium text-body-lg">Cargando PIAR y contexto del estudiante...</p>
    </div>

    <div v-else-if="error" class="flex-1 p-lg overflow-y-auto">
      <div class="bg-error-container text-on-error-container p-6 rounded-2xl max-w-[36rem] mx-auto shadow-md border border-error/20">
        <h3 class="font-bold text-headline-sm flex items-center gap-2 mb-2">
          <span class="material-symbols-outlined text-error">error</span> Error del Servidor
        </h3>
        <p class="text-body-md mb-4">{{ error }}</p>
        <button @click="reintentarCarga" class="px-6 py-2.5 bg-error text-on-error rounded-xl font-bold hover:opacity-90 transition-all cursor-pointer">
          Reintentar Carga
        </button>
      </div>
    </div>

    <!-- No PIAR active -->
    <div v-else-if="!activePiar" class="flex-1 w-full overflow-y-auto flex items-center justify-center p-md bg-surface-container-lowest">
      <div class="glass-card w-[90%] max-w-[500px] p-md md:p-lg flex flex-col items-center text-center space-y-md border border-outline-variant/30 shadow-lg animate-fade-in my-auto">
        <div class="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-2 shadow-inner flex-shrink-0">
          <span class="material-symbols-outlined text-4xl">description</span>
        </div>
        <div class="space-y-sm w-full">
          <h2 class="text-headline-md font-bold text-on-surface leading-tight">No hay un PIAR activo para este estudiante</h2>
          <p class="text-body-md text-on-surface-variant w-full leading-relaxed">
            Para el año lectivo en curso, el estudiante no cuenta con un Plan Individual de Ajustes Razonables (PIAR) registrado. Inicia el proceso de planeación a continuación.
          </p>
        </div>
        <button @click="iniciarPiar" class="mt-4 px-8 py-3.5 bg-primary text-on-primary rounded-xl font-bold flex items-center gap-2 hover:shadow-lg hover:shadow-primary/30 active:scale-95 transition-all cursor-pointer flex-shrink-0">
          <span class="material-symbols-outlined">add_circle</span>
          Iniciar PIAR 2026
        </button>
      </div>
    </div>

    <!-- Main Workspace -->
    <div v-else class="flex-1 flex flex-col overflow-hidden">
      <!-- Tabs Navigation -->
      <div class="bg-surface border-b border-outline-variant/30 flex-shrink-0 px-lg flex gap-md">
        <button 
          @click="activeTab = 'caracteristicas'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'caracteristicas' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">person_celebrate</span>
          1. Características del Estudiante
        </button>
        <button 
          @click="activeTab = 'ajustes'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'ajustes' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">grid_on</span>
          2. Matriz de Ajustes Razonables
        </button>
        <button 
          @click="activeTab = 'pmi'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'pmi' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">groups</span>
          3. Recomendaciones PMI
        </button>
      </div>

      <!-- Tab Content Area -->
      <div class="flex-1 p-lg overflow-y-auto bg-surface-container-lowest">


        <!-- TAB 1: CARACTERÍSTICAS -->
        <div v-if="activeTab === 'caracteristicas'" class="max-w-4xl mx-auto space-y-md">
          <section class="glass-card p-lg space-y-md border border-outline-variant/30">
            <h2 class="text-headline-md font-bold text-primary flex items-center gap-2 border-b border-outline-variant/30 pb-xs">
              <span class="material-symbols-outlined">edit_note</span>
              Sección 1: Características del Estudiante, Docentes y Contexto
            </h2>

            <div class="space-y-sm">
              <div class="flex flex-col gap-1">
                <label class="font-label-md text-body-md text-on-surface-variant flex items-center gap-2">
                  <span class="material-symbols-outlined text-[18px]">co_present</span>
                  Docentes que elaboran el PIAR
                </label>
                <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-md text-body-md text-on-surface-variant flex items-center gap-2 select-none">
                  <span class="material-symbols-outlined text-[20px] text-primary">person</span>
                  <span>{{ docentesElaboran }}</span>
                </div>
              </div>

              <div class="flex flex-col gap-1">
                <label class="font-label-md text-body-md text-on-surface-variant flex items-center gap-2">
                  <span class="material-symbols-outlined text-[18px]">favorite</span>
                  Gustos, intereses y expectativas del estudiante y su familia
                </label>
                <textarea 
                  v-model="gustos"
                  class="bg-surface border border-outline-variant rounded-xl p-md text-body-md focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none outline-none h-32"
                  placeholder="Ej: Le interesan los dinosaurios, el dibujo y las actividades grupales al aire libre. La familia espera que logre integrarse socialmente y aprender lectoescritura básica."
                ></textarea>
              </div>

              <div class="flex flex-col gap-1">
                <label class="font-label-md text-body-md text-on-surface-variant flex items-center gap-2">
                  <span class="material-symbols-outlined text-[18px]">psychology</span>
                  Habilidades, cualidades, fortalezas y apoyos requeridos
                </label>
                <textarea 
                  v-model="habilidades"
                  class="bg-surface border border-outline-variant rounded-xl p-md text-body-md focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none outline-none h-32"
                  placeholder="Ej: Posee gran habilidad visual y espacial, excelente memoria a corto plazo. Requiere apoyos visuales (pictogramas), simplificación de mallas y acompañamiento del docente de apoyo."
                ></textarea>
              </div>
            </div>

            <div class="flex justify-end pt-sm border-t border-outline-variant/30">
              <button 
                @click="guardarCaracteristicas"
                :disabled="isSavingCarac"
                class="px-6 py-3 bg-primary text-on-primary rounded-xl font-bold flex items-center gap-2 hover:shadow-lg hover:shadow-primary/20 active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
              >
                <span class="material-symbols-outlined" :class="{ 'animate-spin': isSavingCarac }">
                  {{ isSavingCarac ? 'progress_activity' : 'save' }}
                </span>
                Guardar Características
              </button>
            </div>
          </section>
        </div>

        <!-- TAB 2: MATRIZ DE AJUSTES -->
        <div v-if="activeTab === 'ajustes'" class="grid grid-cols-12 gap-lg items-start">
          <!-- Formulario de Ingreso/Edición de Ajuste (5 columnas) -->
          <div class="col-span-12 lg:col-span-5 space-y-md">
            <section :class="['glass-card p-md border transition-all', isEditingAjuste ? 'border-secondary-container shadow-md shadow-secondary/5' : 'border-outline-variant/30']">
              <div class="flex justify-between items-center border-b border-outline-variant/30 pb-xs mb-sm">
                <h3 class="font-headline-md font-bold flex items-center gap-2" :class="isEditingAjuste ? 'text-secondary-container' : 'text-primary'">
                  <span class="material-symbols-outlined">{{ isEditingAjuste ? 'edit_square' : 'add_box' }}</span>
                  {{ isEditingAjuste ? 'Editar Ajuste Razonable' : 'Agregar Ajuste Razonable' }}
                </h3>
                <button 
                  v-if="isEditingAjuste"
                  @click="cancelarEdicionAjuste"
                  class="text-label-sm text-outline hover:text-error font-bold flex items-center gap-1 cursor-pointer transition-colors"
                >
                  <span class="material-symbols-outlined text-[16px]">cancel</span> Cancelar
                </button>
              </div>

              <div class="space-y-sm">
                <!-- Area -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant flex items-center gap-1">Área o Asignatura</label>
                  <select 
                    v-model="ajusteForm.area" 
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all font-semibold"
                  >
                    <option v-if="dbAsignaturas.length === 0" v-for="areaOpt in AREAS_VALIDAS" :key="areaOpt" :value="areaOpt">{{ areaOpt }}</option>
                    <option v-else v-for="asig in dbAsignaturas" :key="asig.id" :value="asig.nombre">{{ asig.nombre }}</option>
                  </select>
                </div>

                <!-- Objetivos y buscador -->
                <div class="flex flex-col gap-1 relative">
                  <div class="flex justify-between items-center">
                    <label class="font-label-md text-label-sm text-on-surface-variant">Objetivos / Propósitos de Aprendizaje</label>
                    <button 
                      @click="toggleCurriculumSearch"
                      class="text-label-sm text-primary hover:underline font-bold flex items-center gap-1 cursor-pointer"
                    >
                      <span class="material-symbols-outlined text-[16px]">manage_search</span> 
                      {{ showCurriculumSearch ? 'Ocultar Buscador' : 'Buscador de Mallas (DBA/EBC)' }}
                    </button>
                  </div>

                  <!-- Buscador Curricular Desplegable -->
                  <div v-if="showCurriculumSearch" class="bg-surface-container border border-outline-variant rounded-xl p-md space-y-sm shadow-md mt-1 mb-xs animate-fade-in z-10">
                    <div class="flex items-center justify-between border-b border-outline-variant/30 pb-xs mb-xs">
                      <span class="font-label-md text-body-md text-primary flex items-center gap-1">
                        <span class="material-symbols-outlined text-[18px]">search</span>
                        Mallas Curriculares Oficiales (MEN)
                      </span>
                      <button @click="showCurriculumSearch = false" class="text-outline hover:text-error cursor-pointer">
                        <span class="material-symbols-outlined text-[18px]">close</span>
                      </button>
                    </div>

                    <div class="grid grid-cols-2 gap-xs">
                      <div class="flex flex-col gap-1">
                        <label class="text-[12px] font-bold text-on-surface-variant">Tipo</label>
                        <select v-model="searchType" class="bg-surface border border-outline-variant rounded-lg p-2 text-label-sm outline-none">
                          <option value="dba">Derechos Básicos (DBA)</option>
                          <option value="ebc">Estándares (EBC)</option>
                        </select>
                      </div>
                      <div class="flex flex-col gap-1">
                        <label class="text-[12px] font-bold text-on-surface-variant">Grado / Rango</label>
                        <div class="bg-surface/50 border border-outline-variant rounded-lg p-2 text-label-sm font-semibold text-primary flex items-center gap-1.5 h-[38px] select-none">
                          <span class="material-symbols-outlined text-[16px] text-secondary">school</span>
                          <span>
                            {{ searchType === 'dba' ? formatGrado(estudiante?.grado) : 'Grados ' + searchGrade }}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div class="flex flex-col gap-1">
                      <label class="text-[12px] font-bold text-on-surface-variant">Buscar por palabras clave</label>
                      <div class="flex gap-2">
                        <input 
                          v-model="searchQuery"
                          class="flex-1 bg-surface border border-outline-variant rounded-lg p-2 text-label-sm outline-none"
                          placeholder="Ej: Fraccionarios, suma, redacción..."
                          type="text"
                          @keyup.enter="buscarCurriculo"
                        />
                        <button @click="buscarCurriculo" class="bg-primary text-on-primary px-4 py-2 rounded-lg font-bold hover:opacity-90 transition-all cursor-pointer">
                          Buscar
                        </button>
                      </div>
                    </div>

                    <!-- Resultados del buscador -->
                    <div class="max-h-48 overflow-y-auto border border-outline-variant/30 rounded-lg bg-surface/50 divide-y divide-outline-variant/20">
                      <p v-if="isSearchingCurriculum" class="p-4 text-center text-outline text-[12px] flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined animate-spin text-[18px]">progress_activity</span> Buscando en la base de datos...
                      </p>
                      <p v-else-if="searchResults.length === 0" class="p-4 text-center text-outline text-[12px]">Sin resultados. Intenta otra búsqueda.</p>
                      <div 
                        v-else
                        v-for="item in searchResults" 
                        :key="item.id" 
                        @click="seleccionarCurriculo(item.enunciado)"
                        class="p-2 text-label-sm text-left hover:bg-primary/5 active:bg-primary/10 transition-colors cursor-pointer text-on-surface-variant leading-tight"
                      >
                        <span class="font-bold text-primary text-[11px] block uppercase mb-1">
                          {{ searchType === 'dba' ? `DBA #${item.numero}` : `${item.factor}` }}
                        </span>
                        {{ item.enunciado }}
                      </div>
                    </div>
                  </div>

                  <textarea 
                    v-model="ajusteForm.objetivos"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-24"
                    placeholder="Estándares o Derechos Básicos de Aprendizaje (DBA) a adaptar para el grado en curso."
                  ></textarea>
                </div>

                <!-- Barreras -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant">Barreras Identificadas en el Contexto</label>
                  <textarea 
                    v-model="ajusteForm.barreras"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-20"
                    placeholder="Barreras físicas, cognitivas o metodológicas del aula."
                  ></textarea>
                </div>

                <!-- Ajustes didácticos (DUA) -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant flex items-center justify-between">
                    Ajustes Razonables / Estrategias (DUA)
                  </label>
                  <textarea 
                    v-model="ajusteForm.ajustes"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-28"
                    placeholder="Apoyos didácticos, metodologías de trabajo o cambios curriculares."
                  ></textarea>
                </div>

                <!-- Evaluacion (Solo si es editable) -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant">Evaluación de los Ajustes (Opcional - Seguimiento)</label>
                  <textarea 
                    v-model="ajusteForm.evaluacion"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-16"
                    placeholder="Valoración del impacto de los ajustes al cierre del trimestre escolar."
                  ></textarea>
                </div>
              </div>

              <!-- Action buttons -->
              <div class="flex justify-end gap-xs pt-md mt-sm border-t border-outline-variant/30">

                <!-- Botón IA: Generar con Gemini -->
                <button
                  @click="generarConIA"
                  :disabled="isGeneratingIA || !ajusteForm.area"
                  class="px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold rounded-lg flex items-center gap-1.5 hover:opacity-90 active:scale-95 disabled:opacity-50 transition-all cursor-pointer shadow-md hover:shadow-violet-400/30 mr-auto"
                  title="Generar sugerencias de ajustes razonables con Gemini IA basados en las barreras redactadas"
                >
                  <span class="material-symbols-outlined text-[20px]" :class="{ 'animate-spin': isGeneratingIA }">
                    {{ isGeneratingIA ? 'progress_activity' : 'auto_awesome' }}
                  </span>
                  {{ isGeneratingIA ? 'Generando...' : 'Generar con IA ✨' }}
                </button>

                <button 
                  v-if="isEditingAjuste"
                  @click="cancelarEdicionAjuste"
                  class="px-4 py-2.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant font-bold rounded-lg transition-all cursor-pointer"
                >
                  Cancelar
                </button>
                <button 
                  @click="guardarAjuste"
                  :disabled="isSavingAjuste || !ajusteForm.objetivos || !ajusteForm.barreras || !ajusteForm.ajustes"
                  class="px-5 py-2.5 bg-primary text-on-primary font-bold rounded-lg flex items-center gap-1 hover:opacity-90 active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
                >
                  <span class="material-symbols-outlined text-[20px]">
                    {{ isSavingAjuste ? 'progress_activity' : 'save_as' }}
                  </span>
                  {{ isEditingAjuste ? 'Guardar Cambios' : 'Agregar a la Matriz' }}
                </button>
              </div>
            </section>
          </div>

          <!-- Matriz de Ajustes Cargados (7 columnas) -->
          <div class="col-span-12 lg:col-span-7 space-y-sm">
            <h3 class="text-headline-md font-bold text-on-surface flex items-center gap-2 mb-xs">
              <span class="material-symbols-outlined text-primary">view_quilt</span>
              Malla Escolar Inclusiva ({{ activePiar.ajustes_razonables?.length || 0 }} registros)
            </h3>

            <div v-if="!activePiar.ajustes_razonables || activePiar.ajustes_razonables.length === 0" class="bg-surface-container p-xl rounded-2xl text-center text-outline border border-dashed border-outline-variant/50">
              <span class="material-symbols-outlined text-5xl text-outline-variant mb-2">grid_off</span>
              <p class="font-semibold text-body-lg">La matriz de ajustes está vacía.</p>
              <p class="text-label-sm max-w-[24rem] mx-auto">Utiliza el formulario de la izquierda para agregar objetivos de aprendizaje y estrategias adaptadas para el estudiante.</p>
            </div>

            <div v-else class="space-y-sm max-h-[70vh] overflow-y-auto pr-xs">
              <article 
                v-for="ajuste in activePiar.ajustes_razonables" 
                :key="ajuste.id" 
                class="bg-surface border border-outline-variant/30 rounded-2xl p-md shadow-sm flex flex-col gap-2 hover:border-primary/40 transition-all relative group"
              >
                <!-- Card Header -->
                <div class="flex justify-between items-start">
                  <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-md font-bold text-xs uppercase">
                    {{ ajuste.area }}
                  </span>
                  <div class="flex items-center gap-xs lg:opacity-0 group-hover:opacity-100 transition-opacity">
                    <button 
                      @click="cargarAjusteParaEdicion(ajuste)"
                      class="p-1.5 hover:bg-surface-container-high rounded-lg text-outline-variant hover:text-primary transition-all active:scale-90 cursor-pointer"
                      title="Editar ajuste"
                    >
                      <span class="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                    <button 
                      @click="eliminarAjuste(ajuste.id)"
                      class="p-1.5 hover:bg-error/10 rounded-lg text-outline-variant hover:text-error transition-all active:scale-90 cursor-pointer"
                      title="Eliminar ajuste"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </div>
                </div>

                <!-- Contenido -->
                <div class="grid grid-cols-2 gap-sm text-body-md pt-xs">
                  <div>
                    <h4 class="font-bold text-primary text-xs uppercase tracking-wider mb-1 flex items-center gap-1">
                      <span class="material-symbols-outlined text-[14px]">track_changes</span> Propósito / Meta
                    </h4>
                    <p class="text-on-surface leading-tight font-medium">{{ ajuste.objetivos_propositos }}</p>
                  </div>
                  <div>
                    <h4 class="font-bold text-error text-xs uppercase tracking-wider mb-1 flex items-center gap-1">
                      <span class="material-symbols-outlined text-[14px]">report_problem</span> Barreras
                    </h4>
                    <p class="text-on-surface-variant leading-tight">{{ ajuste.barreras_evidenciadas }}</p>
                  </div>
                </div>

                <div class="border-t border-outline-variant/20 pt-sm mt-xs">
                  <h4 class="font-bold text-tertiary-container text-xs uppercase tracking-wider mb-1 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">tips_and_updates</span> Ajustes y Apoyos DUA
                  </h4>
                  <p class="text-on-surface leading-snug whitespace-pre-wrap font-medium">{{ ajuste.ajustes_estrategias }}</p>
                </div>

                <div v-if="ajuste.evaluacion_ajustes" class="border-t border-outline-variant/20 pt-sm mt-xs bg-[#caead6]/10 p-2.5 rounded-xl border border-[#caead6]/30">
                  <h4 class="font-bold text-tertiary text-xs uppercase tracking-wider mb-1 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">fact_check</span> Evaluación de Ajuste
                  </h4>
                  <p class="text-on-surface-variant leading-snug">{{ ajuste.evaluacion_ajustes }}</p>
                </div>
              </article>
            </div>
          </div>
        </div>

        <!-- TAB 3: RECOMENDACIONES PMI -->
        <div v-if="activeTab === 'pmi'" class="grid grid-cols-12 gap-lg items-start">
          <!-- Formulario de ingreso PMI (5 cols) -->
          <div class="col-span-12 lg:col-span-5 space-y-md">
            <section :class="['glass-card p-md border transition-all', isEditingPMI ? 'border-secondary-container shadow-md shadow-secondary/5' : 'border-outline-variant/30']">
              <div class="flex justify-between items-center border-b border-outline-variant/30 pb-xs mb-sm">
                <h3 class="font-headline-md font-bold flex items-center gap-2" :class="isEditingPMI ? 'text-secondary-container' : 'text-primary'">
                  <span class="material-symbols-outlined">{{ isEditingPMI ? 'edit_square' : 'add_circle' }}</span>
                  {{ isEditingPMI ? 'Editar Recomendación' : 'Nueva Recomendación' }}
                </h3>
                <button 
                  v-if="isEditingPMI"
                  @click="cancelarEdicionPMI"
                  class="text-label-sm text-outline hover:text-error font-bold flex items-center gap-1 cursor-pointer transition-colors"
                >
                  <span class="material-symbols-outlined text-[16px]">cancel</span> Cancelar
                </button>
              </div>

              <div class="space-y-sm">
                <!-- Actor -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant">Actor del Sistema Educativo</label>
                  <select 
                    v-model="pmiForm.actor" 
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all font-semibold"
                  >
                    <option v-for="actorOpt in ACTORES_PMI" :key="actorOpt" :value="actorOpt">{{ actorOpt }}</option>
                  </select>
                </div>

                <!-- Acciones -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant">Acciones a realizar</label>
                  <textarea 
                    v-model="pmiForm.acciones"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-24"
                    placeholder="Ej: Adecuar rampas físicas de la sede escolar o gestionar software especializado."
                  ></textarea>
                </div>

                <!-- Estrategias a implementar -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant">Estrategias a implementar</label>
                  <textarea 
                    v-model="pmiForm.estrategias"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-24"
                    placeholder="Ej: Capacitación técnica a docentes de informática, acompañamiento semanal."
                  ></textarea>
                </div>
              </div>

              <!-- Action buttons -->
              <div class="flex justify-end gap-xs pt-md mt-sm border-t border-outline-variant/30">
                <button 
                  v-if="isEditingPMI"
                  @click="cancelarEdicionPMI"
                  class="px-4 py-2.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface-variant font-bold rounded-lg transition-all cursor-pointer"
                >
                  Cancelar
                </button>
                <button 
                  @click="guardarPMI"
                  :disabled="isSavingPMI || !pmiForm.acciones || !pmiForm.estrategias"
                  class="px-5 py-2.5 bg-primary text-on-primary font-bold rounded-lg flex items-center gap-1 hover:opacity-90 active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
                >
                  <span class="material-symbols-outlined text-[20px]">
                    {{ isSavingPMI ? 'progress_activity' : 'playlist_add_check' }}
                  </span>
                  {{ isEditingPMI ? 'Guardar Cambios' : 'Agregar Recomendación' }}
                </button>
              </div>
            </section>
          </div>

          <!-- Recomendaciones por Actor (7 cols) -->
          <div class="col-span-12 lg:col-span-7 space-y-sm">
            <h3 class="text-headline-md font-bold text-on-surface flex items-center gap-2 mb-xs">
              <span class="material-symbols-outlined text-primary">view_cozy</span>
              Articulación con el Plan de Mejoramiento Institucional (PMI)
            </h3>

            <!-- Grouped by Actor -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-sm">
              <div 
                v-for="actorGroup in ACTORES_PMI" 
                :key="actorGroup"
                class="bg-surface border border-outline-variant/30 rounded-2xl p-md flex flex-col min-h-48"
              >
                <div class="flex items-center justify-between border-b border-outline-variant/20 pb-xs mb-sm">
                  <span class="font-headline-md font-bold text-primary text-sm uppercase tracking-wide flex items-center gap-1">
                    <span class="material-symbols-outlined text-[18px]">group</span>
                    {{ actorGroup }}
                  </span>
                  <span class="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs font-bold">
                    {{ getPMIForActor(actorGroup).length }}
                  </span>
                </div>

                <div class="flex-1 space-y-sm overflow-y-auto max-h-60 pr-xs">
                  <p v-if="getPMIForActor(actorGroup).length === 0" class="text-center text-outline text-xs py-8">Sin recomendaciones cargadas.</p>
                  <div 
                    v-else
                    v-for="rec in getPMIForActor(actorGroup)" 
                    :key="rec.id"
                    class="bg-surface-container-low p-3 rounded-xl border border-outline-variant/20 flex flex-col gap-1 relative group"
                  >
                    <div class="absolute top-2 right-2 flex gap-xs lg:opacity-0 group-hover:opacity-100 transition-opacity">
                      <button @click="cargarPMIParaEdicion(rec)" class="text-outline hover:text-primary transition-colors cursor-pointer" title="Editar">
                        <span class="material-symbols-outlined text-[16px]">edit</span>
                      </button>
                      <button @click="eliminarPMI(rec.id)" class="text-outline hover:text-error transition-colors cursor-pointer" title="Eliminar">
                        <span class="material-symbols-outlined text-[16px]">delete</span>
                      </button>
                    </div>

                    <div class="pr-6">
                      <p class="text-[11px] font-bold text-on-surface-variant uppercase">Acción:</p>
                      <p class="text-body-md text-on-surface leading-tight font-medium">{{ rec.acciones }}</p>
                      <p class="text-[11px] font-bold text-on-surface-variant uppercase mt-1">Estrategia:</p>
                      <p class="text-body-md text-on-surface-variant leading-tight">{{ rec.estrategias_implementar }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating Notifications -->
    <div v-if="successMessage || localError" class="fixed bottom-6 right-6 z-[9999] max-w-[28rem] animate-fade-in flex flex-col gap-2">
      <div v-if="successMessage" class="bg-[#caead6] text-[#042014] p-4 pr-6 rounded-xl shadow-lg border border-[#afceba] flex items-center gap-3">
        <span class="material-symbols-outlined text-tertiary shrink-0">check_circle</span>
        <span class="font-semibold text-body-md">{{ successMessage }}</span>
      </div>
      <div v-if="localError" class="bg-error-container text-on-error-container p-4 pr-6 rounded-xl shadow-lg border border-error/20 flex items-center gap-3">
        <span class="material-symbols-outlined text-error shrink-0">error</span>
        <span class="font-semibold text-body-md">{{ localError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { usePiarStore } from '../stores/piar'
import { useAuthStore } from '../stores/auth'
import { storeToRefs } from 'pinia'

const route = useRoute()
const piarStore = usePiarStore()
const authStore = useAuthStore()
const { activePiar, isLoading, error } = storeToRefs(piarStore)

const estudianteId = route.params.id as string
const estudiante = ref<any>(null)
const entornoSalud = ref<any>(null)

// Pestañas
const activeTab = ref('caracteristicas')

// TAB 1: Características
const docentesElaboran = ref('')
const gustos = ref('')
const habilidades = ref('')
const isSavingCarac = ref(false)

// TAB 2: Formulario Ajuste
const AREAS_VALIDAS = ['Matemáticas', 'Ciencias', 'Lenguaje', 'Convivencia', 'Socialización', 'Participación', 'Autonomía', 'Autocontrol'] as const
const dbAsignaturas = ref<any[]>([])

const ajusteForm = ref({
  id: '',
  area: 'Matemáticas' as string,
  objetivos: '',
  barreras: '',
  ajustes: '',
  evaluacion: ''
})
const isEditingAjuste = computed(() => !!ajusteForm.value.id)
const isSavingAjuste = ref(false)
const isGeneratingIA = ref(false)

// Helper buscador de currículo
const showCurriculumSearch = ref(false)
const searchType = ref<'dba' | 'ebc'>('dba')
const searchGrade = computed(() => {
  const rawGrado = estudiante.value?.grado
  if (!rawGrado) return '3' // fallback
  const cleanGrade = String(rawGrado).replace('°', '').trim().toLowerCase()
  
  if (searchType.value === 'dba') {
    return cleanGrade
  } else {
    // Map to EBC ranges
    if (['transicion', '0', '1', '2', '3'].includes(cleanGrade)) return '1-3'
    if (['4', '5'].includes(cleanGrade)) return '4-5'
    if (['6', '7'].includes(cleanGrade)) return '6-7'
    if (['8', '9'].includes(cleanGrade)) return '8-9'
    if (['10', '11'].includes(cleanGrade)) return '10-11'
    return '1-3' // fallback
  }
})
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const isSearchingCurriculum = ref(false)

// Map área de base de datos a área curricular del MEN para optimizar búsqueda
const searchArea = computed(() => {
  const asig = dbAsignaturas.value.find(a => a.nombre === ajusteForm.value.area)
  const areaNombre = asig ? asig.area_nombre : ajusteForm.value.area
  
  if (!areaNombre) return 'Matemáticas'
  
  const clean = areaNombre.toLowerCase()
  if (clean.includes('matemática') || clean.includes('geometría') || clean.includes('estadística')) {
    return 'Matemáticas'
  }
  if (clean.includes('naturales') || clean.includes('física') || clean.includes('química') || clean.includes('fisicoquímica') || clean.includes('ambiental') || clean.includes('ciencias')) {
    if (clean.includes('sociales') || clean.includes('historia') || clean.includes('geografía') || clean.includes('convivencia') || clean.includes('ciudadana')) {
      return 'Ciencias Sociales'
    }
    return 'Ciencias Naturales'
  }
  if (clean.includes('sociales') || clean.includes('historia') || clean.includes('geografía') || clean.includes('convivencia') || clean.includes('ciudadana')) {
    return 'Ciencias Sociales'
  }
  if (clean.includes('castellana') || clean.includes('español') || clean.includes('lenguaje') || clean.includes('humanidades')) {
    return 'Lenguaje'
  }
  if (clean.includes('inglés') || clean.includes('idiomas')) {
    return 'Inglés'
  }
  
  return 'Matemáticas' // fallback
})

// TAB 3: Formulario PMI
const ACTORES_PMI = ['Familia', 'Docentes', 'Directivos', 'Administrativos', 'Pares'] as const
const pmiForm = ref({
  id: '',
  actor: 'Familia' as typeof ACTORES_PMI[number],
  acciones: '',
  estrategias: ''
})
const isEditingPMI = computed(() => !!pmiForm.value.id)
const isSavingPMI = ref(false)

// Notificaciones flotantes
const successMessage = ref('')
const localError = ref('')

function showToast(message: string, isError = false) {
  if (isError) {
    localError.value = message
    setTimeout(() => { localError.value = '' }, 4000)
  } else {
    successMessage.value = message
    setTimeout(() => { successMessage.value = '' }, 4000)
  }
}

onMounted(async () => {
  await cargarEstudiante()
  await cargarPiar()
  await cargarAsignaturas()
  cargarEntornoSalud() // sin await: enriquece contexto IA en background
})

async function cargarEstudiante() {
  try {
    const res = await fetch(`http://localhost:8000/api/v1/estudiantes/${estudianteId}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      estudiante.value = await res.json()
    }
  } catch (e) {
    console.error("Error fetching student", e)
  }
}

async function cargarEntornoSalud() {
  try {
    const res = await fetch(`http://localhost:8000/api/v1/estudiantes/${estudianteId}/salud`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      entornoSalud.value = await res.json()
    }
  } catch (e) {
    // No es crítico si falla
    console.warn('No se pudo cargar el entorno de salud para contexto IA', e)
  }
}

async function cargarAsignaturas() {
  try {
    const authStore = useAuthStore()
    const res = await fetch('http://localhost:8000/api/v1/gestion/asignaturas', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      dbAsignaturas.value = await res.json()
      if (dbAsignaturas.value.length > 0 && !ajusteForm.value.area) {
        ajusteForm.value.area = dbAsignaturas.value[0].nombre
      }
    }
  } catch (e) {
    console.error("Error fetching asignaturas", e)
  }
}

async function cargarPiar() {
  await piarStore.fetchPiarForStudent(estudianteId)
  inicializarFormularios()
}

function inicializarFormularios() {
  if (activePiar.value) {
    docentesElaboran.value = activePiar.value.docentes_elaboran || (authStore.user ? `${authStore.user.nombre} ${authStore.user.apellido}` : '')
    gustos.value = activePiar.value.caracteristicas?.descripcion_gustos_intereses || ''
    habilidades.value = activePiar.value.caracteristicas?.descripcion_habilidades || ''
  } else {
    docentesElaboran.value = authStore.user ? `${authStore.user.nombre} ${authStore.user.apellido}` : ''
  }
}

// Escuchar cambios en activePiar por si se crea o carga asíncronamente
watch(activePiar, (newPiar) => {
  if (newPiar) {
    inicializarFormularios()
  }
}, { deep: true })

watch(() => authStore.user, (newUser) => {
  if (newUser && !docentesElaboran.value) {
    docentesElaboran.value = `${newUser.nombre} ${newUser.apellido}`
  }
})

watch([searchType, searchArea], () => {
  if (showCurriculumSearch.value) {
    buscarCurriculo()
  }
})

async function reintentarCarga() {
  await cargarEstudiante()
  await cargarPiar()
}

async function iniciarPiar() {
  try {
    await piarStore.createPiar(estudianteId)
    showToast("PIAR iniciado correctamente en modo borrador.")
  } catch (e: any) {
    showToast("Error al iniciar el documento PIAR.", true)
  }
}

// CRUD Tab 1: Características
async function guardarCaracteristicas() {
  isSavingCarac.value = true
  try {
    await piarStore.updatePiar(docentesElaboran.value, {
      descripcion_gustos_intereses: gustos.value,
      descripcion_habilidades: habilidades.value
    })
    showToast("Características del estudiante guardadas correctamente.")
  } catch (e: any) {
    showToast(e.message || "Error al guardar las características.", true)
  } finally {
    isSavingCarac.value = false
  }
}

// CRUD Tab 2: Ajustes Razonables
async function guardarAjuste() {
  isSavingAjuste.value = true
  try {
    if (isEditingAjuste.value) {
      await piarStore.updateAjuste(
        ajusteForm.value.id,
        ajusteForm.value.area,
        ajusteForm.value.objetivos,
        ajusteForm.value.barreras,
        ajusteForm.value.ajustes,
        ajusteForm.value.evaluacion
      )
      showToast("Ajuste razonable actualizado con éxito en la malla.")
    } else {
      await piarStore.saveAjuste(
        ajusteForm.value.area,
        ajusteForm.value.objetivos,
        ajusteForm.value.barreras,
        ajusteForm.value.ajustes
      )
      showToast("Ajuste razonable agregado a la malla escolar.")
    }
    cancelarEdicionAjuste()
  } catch (e: any) {
    showToast(e.message || "No se pudo guardar el ajuste. Verifica la conexión.", true)
  } finally {
    isSavingAjuste.value = false
  }
}

function cargarAjusteParaEdicion(ajuste: any) {
  ajusteForm.value = {
    id: ajuste.id,
    area: ajuste.area,
    objetivos: ajuste.objetivos_propositos,
    barreras: ajuste.barreras_evidenciadas,
    ajustes: ajuste.ajustes_estrategias,
    evaluacion: ajuste.evaluacion_ajustes || ''
  }
}

function cancelarEdicionAjuste() {
  ajusteForm.value = {
    id: '',
    area: 'Matemáticas',
    objetivos: '',
    barreras: '',
    ajustes: '',
    evaluacion: ''
  }
}

async function eliminarAjuste(ajusteId: string) {
  if (confirm("¿Estás seguro de que deseas eliminar este ajuste razonable de la matriz?")) {
    try {
      await piarStore.deleteAjuste(ajusteId)
      showToast("Ajuste razonable removido de la malla.")
      if (ajusteForm.value.id === ajusteId) {
        cancelarEdicionAjuste()
      }
    } catch (e: any) {
      showToast("Error al eliminar el ajuste razonable.", true)
    }
  }
}

// IA: Generar plan completo con Gemini
async function generarConIA() {
  if (!activePiar.value?.id) {
    showToast('No hay un PIAR activo para generar el plan.', true)
    return
  }
  if (!ajusteForm.value.area) {
    showToast('Selecciona un área o asignatura antes de generar con IA.', true)
    return
  }
  if (!ajusteForm.value.barreras || !ajusteForm.value.barreras.trim()) {
    showToast('Por favor, escribe las barreras identificadas en el contexto antes de generar los ajustes con IA.', true)
    return
  }

  isGeneratingIA.value = true
  try {
    // Si no hay resultados de búsqueda cargados, buscar DBA automáticamente para el área y grado
    let dbaContexto = searchResults.value.filter((r: any) => searchType.value === 'dba')
    if (dbaContexto.length === 0 && searchGrade.value) {
      try {
        const dbaUrl = `http://localhost:8000/api/v1/curriculum/dba?grado=${searchGrade.value}&area=${searchArea.value}&limit=10`
        const dbaRes = await fetch(dbaUrl, { headers: { 'Authorization': `Bearer ${authStore.token}` } })
        if (dbaRes.ok) {
          const dbaData = await dbaRes.json()
          dbaContexto = dbaData.items || []
        }
      } catch (_) { /* fallback: sin DBA */ }
    }

    const dbaTexto = dbaContexto.length > 0
      ? dbaContexto.map((d: any) => `DBA #${d.numero}: ${d.enunciado}`).join('\n')
      : null
    const ebcTexto = searchResults.value.length > 0 && searchType.value === 'ebc'
      ? searchResults.value.map((e: any) => `${e.factor}: ${e.enunciado}`).join('\n')
      : null

    // Contexto del estudiante
    const diagnostico = entornoSalud.value?.diagnostico_medico || null

    const payload = {
      area: ajusteForm.value.area,
      estudiante_nombre: `${estudiante.value?.nombres || ''} ${estudiante.value?.apellidos || ''}`.trim(),
      grado: estudiante.value?.grado || null,
      edad: estudiante.value?.edad || null,
      diagnostico_medico: diagnostico,
      gustos_intereses: activePiar.value.caracteristicas?.descripcion_gustos_intereses || null,
      habilidades_fortalezas: activePiar.value.caracteristicas?.descripcion_habilidades || null,
      dba_referencia: dbaTexto,
      ebc_referencia: ebcTexto,
      barreras_evidenciadas: ajusteForm.value.barreras,
      instrucciones_docente: null
    }

    const res = await fetch(
      `http://localhost:8000/api/v1/piars/${activePiar.value.id}/generar_plan_ia`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`
        },
        body: JSON.stringify(payload)
      }
    )

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error al contactar Gemini')
    }

    const data = await res.json()
    // Solo llenar ajustes sugeridos — las barreras y objetivos son definidos por el docente
    ajusteForm.value.ajustes = data.ajustes_estrategias

    showToast('✨ Ajustes razonables y estrategias DUA sugeridos por IA. Revisa y edita antes de guardar.')
  } catch (e: any) {
    showToast(e.message || 'Error al generar el plan con IA. Verifica la configuración de Gemini.', true)
  } finally {
    isGeneratingIA.value = false
  }
}

// Buscador Curricular
function toggleCurriculumSearch() {
  showCurriculumSearch.value = !showCurriculumSearch.value
  if (showCurriculumSearch.value && searchResults.value.length === 0) {
    buscarCurriculo()
  }
}

async function buscarCurriculo() {
  isSearchingCurriculum.value = true
  searchResults.value = []
  try {
    let url = `http://localhost:8000/api/v1/curriculum/${searchType.value}?`
    if (searchType.value === 'dba') {
      url += `grado=${searchGrade.value}&area=${searchArea.value}`
    } else {
      url += `rango_grados=${searchGrade.value}&area=${searchArea.value}`
    }
    if (searchQuery.value.trim()) {
      url += `&q=${encodeURIComponent(searchQuery.value.trim())}`
    }
    const res = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      const data = await res.json()
      searchResults.value = data.items || []
    }
  } catch (e) {
    console.error("Error buscando mallas curriculares", e)
  } finally {
    isSearchingCurriculum.value = false
  }
}

function formatGrado(grado: string | undefined | null): string {
  if (!grado) return 'No asignado'
  const clean = String(grado).replace('°', '').trim().toLowerCase()
  if (clean === 'transicion') return 'Transición'
  return `Grado ${clean}°`
}

function seleccionarCurriculo(enunciado: string) {
  // Anteponer la fuente de datos
  const prefijo = searchType.value === 'dba' ? `DBA (${formatGrado(searchGrade.value)}): ` : 'EBC: '
  ajusteForm.value.objetivos = prefijo + enunciado
  showCurriculumSearch.value = false
}

// CRUD Tab 3: Recomendaciones PMI
async function guardarPMI() {
  isSavingPMI.value = true
  try {
    if (isEditingPMI.value) {
      await piarStore.updateRecomendacionPMI(
        pmiForm.value.id,
        pmiForm.value.actor,
        pmiForm.value.acciones,
        pmiForm.value.estrategias
      )
      showToast("Recomendación PMI modificada correctamente.")
    } else {
      await piarStore.addRecomendacionPMI(
        pmiForm.value.actor,
        pmiForm.value.acciones,
        pmiForm.value.estrategias
      )
      showToast("Recomendación PMI agregada a la lista.")
    }
    cancelarEdicionPMI()
  } catch (e: any) {
    showToast(e.message || "Error al registrar la recomendación PMI.", true)
  } finally {
    isSavingPMI.value = false
  }
}

function cargarPMIParaEdicion(rec: any) {
  pmiForm.value = {
    id: rec.id,
    actor: rec.actor,
    acciones: rec.acciones,
    estrategias: rec.estrategias_implementar
  }
}

function cancelarEdicionPMI() {
  pmiForm.value = {
    id: '',
    actor: 'Familia',
    acciones: '',
    estrategias: ''
  }
}

async function eliminarPMI(pmiId: string) {
  if (confirm("¿Deseas eliminar esta recomendación de mejoramiento institucional?")) {
    try {
      await piarStore.deleteRecomendacionPMI(pmiId)
      showToast("Recomendación PMI eliminada.")
      if (pmiForm.value.id === pmiId) {
        cancelarEdicionPMI()
      }
    } catch (e: any) {
      showToast("Error al eliminar la recomendación PMI.", true)
    }
  }
}

function getPMIForActor(actor: string) {
  if (!activePiar.value || !activePiar.value.recomendaciones_pmi) return []
  return activePiar.value.recomendaciones_pmi.filter((r: any) => r.actor === actor)
}
</script>

<style scoped>
.glass-card {
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.04);
}
@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.25s ease-out forwards;
}
</style>
