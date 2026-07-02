<template>
  <div class="flex-1 flex flex-col overflow-hidden font-body-md text-on-surface">
    <!-- PIAR Context Banner -->
    <div class="flex-shrink-0 bg-surface px-lg py-4 border-b border-outline-variant/30 shadow-sm flex justify-between items-center flex-wrap gap-3">
      <div class="flex items-center gap-4">
        <router-link to="/estudiantes" class="flex items-center justify-center w-10 h-10 rounded-full hover:bg-surface-container-high active:scale-95 transition-all text-on-surface-variant cursor-pointer">
          <span class="material-symbols-outlined">arrow_back</span>
        </router-link>
        <div>
          <h1 class="text-headline-md font-bold text-primary flex items-center gap-2">
            <span class="material-symbols-outlined">description</span>
            Anexo 2: PIAR
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
    </div>

    <!-- Loading / Error States -->
    <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center">
      <span class="material-symbols-outlined animate-spin text-primary text-5xl mb-4">progress_activity</span>
      <p class="text-on-surface-variant font-medium text-body-lg">Cargando PIAR y contexto del estudiante...</p>
    </div>

    <div v-else-if="error" class="flex-1 p-lg overflow-y-auto">
      <div class="bg-error-container text-on-error-container p-6 rounded-2xl max-w-[36rem] mx-auto shadow-md border border-error/20">
        <h3 class="font-bold text-headline-sm flex items-center gap-2 mb-2">
          <span class="material-symbols-outlined text-error">error</span> Error del servidor
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
          v-if="isDirectorOrAdmin"
          @click="activeTab = 'caracteristicas'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'caracteristicas' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">person_celebrate</span>
          1. Características del estudiante
        </button>
        <button 
          @click="activeTab = 'ajustes'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'ajustes' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">grid_on</span>
          2. Matriz de ajustes razonables
        </button>
        <button 
          v-if="isDirectorOrAdmin"
          @click="activeTab = 'pmi'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'pmi' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">groups</span>
          3. Recomendaciones PMI
        </button>
        <button 
          v-if="isDirectorOrAdmin"
          @click="activeTab = 'acta'" 
          :class="['py-4 border-b-2 font-label-md text-body-md cursor-pointer flex items-center gap-2 transition-all', activeTab === 'acta' ? 'border-primary text-primary font-bold' : 'border-transparent text-on-surface-variant hover:text-on-surface']"
        >
          <span class="material-symbols-outlined text-[20px]">assignment_turned_in</span>
          4. Acta de acuerdo (Anexo 3)
        </button>
      </div>

      <!-- Tab Content Area -->
      <div class="flex-1 p-lg overflow-y-auto bg-surface-container-lowest">


        <!-- TAB 1: CARACTERÍSTICAS -->
        <div v-if="activeTab === 'caracteristicas' && isDirectorOrAdmin" class="max-w-4xl mx-auto space-y-md">
          <section class="glass-card p-lg space-y-md border border-outline-variant/30">
            <h2 class="text-headline-md font-bold text-primary flex items-center gap-2 border-b border-outline-variant/30 pb-xs">
              <span class="material-symbols-outlined">edit_note</span>
              Sección 1: Características del estudiante, docentes y contexto
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
                Guardar características
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
                <h3 class="font-headline-md font-bold flex items-center gap-2 text-wrap" :class="isEditingAjuste ? 'text-secondary-container' : 'text-primary'">
                  <span class="material-symbols-outlined">{{ isEditingAjuste ? 'edit_square' : 'add_box' }}</span>
                  {{ isEditingAjuste ? `Editar Ajuste (${periodoEdicionNombre})` : 'Agregar Ajuste Razonable' }}
                </h3>
                <button 
                  v-if="isEditingAjuste"
                  @click="cancelarEdicionAjuste"
                  class="text-label-sm text-outline hover:text-error font-bold flex items-center gap-1 cursor-pointer transition-colors"
                >
                  <span class="material-symbols-outlined text-[16px]">cancel</span> Cancelar
                </button>
              </div>

              <!-- Active Period Banner -->
              <div v-if="periodoActivo && !isEditingAjuste" class="bg-primary/5 text-primary border border-primary/10 rounded-xl p-3 text-body-md mb-sm flex items-center gap-2 select-none">
                <span class="material-symbols-outlined text-[20px] text-primary">calendar_today</span>
                <span class="text-left leading-tight">
                  Nuevo ajuste se guardará en: <strong>{{ periodoActivo.nombre }}</strong>
                </span>
                <span class="bg-success/15 text-success px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0">Activo</span>
              </div>
              <div v-else-if="!periodoActivo && !isEditingAjuste" class="bg-error-container text-on-error-container border border-error/20 rounded-xl p-3 text-body-md mb-sm flex items-center gap-2">
                <span class="material-symbols-outlined text-[20px] text-error">warning</span>
                <span class="text-left leading-tight">
                  Sin periodo académico activo. Debes activar uno en Gestión Escolar.
                </span>
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

                <!-- Titulo del tema -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant flex items-center gap-1">Título del Tema</label>
                  <input 
                    v-model="ajusteForm.titulo_tema" 
                    type="text"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all font-semibold"
                    placeholder="Ej: Fraccionarios, Ecuaciones, Célula, etc."
                  />
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
                        Mallas curriculares oficiales (MEN)
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
                          <option value="ebc">Estándares (EBC - Lineamientos)</option>
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
                  <label class="font-label-md text-label-sm text-on-surface-variant">Barreras identificadas en el contexto</label>
                  <textarea 
                    v-model="ajusteForm.barreras"
                    class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all h-20"
                    placeholder="Barreras físicas, cognitivas o metodológicas del aula."
                  ></textarea>
                </div>

                <!-- Ajustes didácticos (DUA) -->
                <div class="flex flex-col gap-1">
                  <label class="font-label-md text-label-sm text-on-surface-variant flex items-center justify-between">
                    Ajustes razonables / Estrategias (DUA)
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
              Malla escolar inclusiva ({{ activePiar.ajustes_razonables?.length || 0 }} registros)
            </h3>

            <div v-if="!activePiar.ajustes_razonables || activePiar.ajustes_razonables.length === 0" class="bg-surface-container p-xl rounded-2xl text-center text-outline border border-dashed border-outline-variant/50">
              <span class="material-symbols-outlined text-5xl text-outline-variant mb-2">grid_off</span>
              <p class="font-semibold text-body-lg">La matriz de ajustes está vacía.</p>
              <p class="text-label-sm max-w-[24rem] mx-auto">Utiliza el formulario de la izquierda para agregar objetivos de aprendizaje y estrategias adaptadas para el estudiante.</p>
            </div>

            <div v-else class="space-y-sm max-h-[70vh] overflow-y-auto pr-xs">
              <div v-for="grupo in periodosConAjustes" :key="grupo.periodo.id">
                <!-- Header del periodo — acordeón -->
                <button
                  @click="togglePeriodo(grupo.periodo.id)"
                  class="w-full flex items-center gap-2 py-2.5 border-b border-outline-variant/20 hover:bg-surface-container-low/50 transition-colors rounded-lg px-2 cursor-pointer"
                >
                  <span class="material-symbols-outlined text-outline-variant text-[20px] transition-transform duration-200"
                    :class="periodosExpandidos[grupo.periodo.id] ? 'rotate-90' : ''"
                  >chevron_right</span>
                  <span class="material-symbols-outlined text-primary text-[20px]">calendar_today</span>
                  <span class="font-bold text-on-surface text-body-md">
                    {{ grupo.periodo.nombre }}
                  </span>
                  <span class="bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded-full text-[11px] font-bold">
                    {{ grupo.ajustes?.length || 0 }}
                  </span>
                  <span v-if="grupo.periodo.activo" class="bg-success/15 text-success border border-success/30 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ml-auto">
                    Activo
                  </span>
                </button>

                <!-- Lista de ajustes para este periodo -->
                <div v-show="periodosExpandidos[grupo.periodo.id]" class="space-y-sm pl-7 pt-2 pb-1">
                  <article 
                    v-for="ajuste in grupo.ajustes" 
                    :key="ajuste.id" 
                    class="bg-surface border border-outline-variant/30 rounded-2xl p-md shadow-sm flex flex-col gap-2 hover:border-primary/40 transition-all relative group"
                  >
                    <!-- Card Header -->
                    <div class="flex justify-between items-start">
                      <div class="flex flex-wrap items-center gap-xs">
                        <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-md font-bold text-xs uppercase">
                          {{ ajuste.area }}
                        </span>
                        <span v-if="ajuste.titulo_tema" class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-label-md font-bold text-xs">
                          Tema: {{ ajuste.titulo_tema }}
                        </span>
                      </div>
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

                    <!-- Puntuación del ajuste (solo visible para el creador) -->
                    <div v-if="ajuste.creado_por === authStore.user?.id" class="border-t border-outline-variant/20 pt-sm mt-xs">
                      <div class="flex items-center justify-between mb-1.5">
                        <h4 class="font-bold text-amber-700 text-xs uppercase tracking-wider flex items-center gap-1">
                          <span class="material-symbols-outlined text-[14px]">star</span>
                          {{ ajuste.puntuacion ? 'Tu valoración' : '¿Te funcionó este ajuste?' }}
                        </h4>
                        <span v-if="ajuste.puntuacion" class="text-[10px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-bold">
                          {{ ajuste.puntuacion }}/5
                        </span>
                      </div>
                      <p v-if="!ajuste.puntuacion" class="text-[11px] text-on-surface-variant mb-1.5">
                        Califica del 1 al 5 qué tan efectivo fue en el aula.
                      </p>
                      <div class="flex items-center gap-0.5 mb-1.5">
                        <button
                          v-for="star in 5"
                          :key="star"
                          @click="puntuarAjuste(ajuste, star)"
                          class="text-xl transition-all cursor-pointer hover:scale-125"
                          :class="(ajuste.puntuacion || 0) >= star ? 'text-amber-500' : 'text-outline-variant'"
                          :title="`${star} estrella(s)`"
                        >
                          {{ (ajuste.puntuacion || 0) >= star ? '★' : '☆' }}
                        </button>
                      </div>
                      <div v-if="ajuste.puntuacion" class="space-y-1.5">
                        <textarea
                          v-model="ajuste._comentarioPuntuacion"
                          class="w-full bg-surface border border-outline-variant rounded-lg p-2 text-body-sm outline-none focus:border-amber-500 transition-all resize-none text-xs h-14"
                          placeholder="Explica brevemente por qué funcionó o no este ajuste..."
                        ></textarea>
                        <div class="flex items-center justify-between">
                          <span v-if="ajuste._comentarioPuntuacion === ajuste._comentarioGuardado && ajuste._comentarioGuardado" class="text-[10px] text-green-600 flex items-center gap-0.5">
                            <span class="material-symbols-outlined text-[14px]">check_circle</span> Guardado
                          </span>
                          <span v-else class="text-[10px] text-amber-600">
                            Sin guardar
                          </span>
                          <button
                            @click="guardarComentarioPuntuacion(ajuste)"
                            :disabled="ajuste._comentarioPuntuacion === ajuste._comentarioGuardado"
                            class="text-[11px] font-bold px-3 py-1 rounded-lg transition-all cursor-pointer"
                            :class="ajuste._comentarioPuntuacion === ajuste._comentarioGuardado
                              ? 'bg-green-50 text-green-600 cursor-default'
                              : 'bg-amber-500 text-white hover:bg-amber-600'"
                          >
                            Guardar comentario
                          </button>
                        </div>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: RECOMENDACIONES PMI -->
        <div v-if="activeTab === 'pmi' && isDirectorOrAdmin" class="grid grid-cols-12 gap-lg items-start">
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

        <!-- TAB 4: ACTA DE ACUERDO -->
        <div v-if="activeTab === 'acta' && isDirectorOrAdmin" class="grid grid-cols-12 gap-lg items-start">
          <!-- Columna izquierda: Formularios de compromisos -->
          <div class="col-span-8 space-y-md">
            <!-- Sección 1: Compromisos Aula -->
            <div class="glass-card p-lg space-y-md border border-outline-variant/30">
              <h3 class="text-title-lg font-bold text-primary flex items-center gap-2 border-b border-outline-variant/30 pb-xs">
                <span class="material-symbols-outlined">school</span>
                1. Compromisos del establecimiento educativo (aula)
              </h3>
              <p class="text-body-md text-on-surface-variant">
                Define las acciones, adaptaciones curriculares y apoyos específicos que la escuela y los docentes implementarán en el aula de clases.
              </p>
              <div class="flex flex-col gap-1">
                <textarea 
                  v-model="actaForm.compromisosAula" 
                  rows="4"
                  class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all font-semibold resize-y"
                  placeholder="Ej: Se ubicará al estudiante en primera fila, se dará apoyo visual durante explicaciones y se flexibilizarán los tiempos de evaluación escrita..."
                ></textarea>
                <button 
                  @click="guardarActaAcuerdo"
                  :disabled="isSavingActa"
                  class="bg-secondary-container text-on-secondary-container font-bold text-label-sm px-4 py-2 rounded-xl flex items-center gap-1.5 hover:opacity-90 active:scale-95 transition-all disabled:opacity-50 self-end"
                >
                  <span v-if="isSavingActa" class="w-4 h-4 border-2 border-on-secondary-container border-t-transparent rounded-full animate-spin"></span>
                  <span v-else class="material-symbols-outlined text-[18px]">save</span>
                  Guardar compromisos
                </button>
              </div>
            </div>

            <!-- Sección 2: Compromisos Casa (Dynamic Table) -->
            <div class="glass-card p-lg space-y-md border border-outline-variant/30">
              <div class="flex justify-between items-center border-b border-outline-variant/30 pb-xs">
                <h3 class="text-title-lg font-bold text-primary flex items-center gap-2">
                  <span class="material-symbols-outlined">home</span>
                  2. Compromisos de apoyo familiar (Casa)
                </h3>
                <button 
                  @click="agregarCompromisoCasa"
                  class="bg-primary text-on-primary font-bold text-label-md px-3 py-1.5 rounded-full flex items-center gap-1 hover:opacity-90 active:scale-95 transition-all shadow-md"
                >
                  <span class="material-symbols-outlined text-[18px]">add</span>
                  Agregar Actividad
                </button>
              </div>
              <p class="text-body-md text-on-surface-variant">
                Planifica las actividades y estrategias que la familia realizará en el hogar para dar continuidad a los procesos escolares.
              </p>

              <div class="overflow-x-auto">
                <table class="w-full border-collapse">
                  <thead>
                    <tr class="bg-surface-container-high border-b border-outline-variant">
                      <th class="p-3 text-left font-bold text-label-md text-on-surface-variant w-[25%]">Actividad</th>
                      <th class="p-3 text-left font-bold text-label-md text-on-surface-variant w-[50%]">Estrategia / Descripción</th>
                      <th class="p-3 text-left font-bold text-label-md text-on-surface-variant w-[20%]">Frecuencia</th>
                      <th class="p-3 text-center font-bold text-label-md text-on-surface-variant w-[5%]"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="actaForm.compromisosCasa.length === 0">
                      <td colspan="4" class="p-8 text-center text-body-md text-on-surface-variant italic">
                        No hay actividades en casa registradas. Haz clic en "Agregar Actividad" para comenzar.
                      </td>
                    </tr>
                    <tr 
                      v-else 
                      v-for="(comp, index) in actaForm.compromisosCasa" 
                      :key="index"
                      class="border-b border-outline-variant/30 hover:bg-surface-container-low transition-all"
                    >
                      <td class="p-2">
                        <input 
                          v-model="comp.nombre_actividad"
                          type="text"
                          class="w-full bg-surface border border-outline-variant rounded-lg p-2 text-body-sm outline-none focus:border-primary transition-all font-semibold"
                          placeholder="Ej: Lectura diaria"
                        />
                      </td>
                      <td class="p-2">
                        <textarea 
                          v-model="comp.descripcion_estrategia"
                          rows="1"
                          class="w-full bg-surface border border-outline-variant rounded-lg p-2 text-body-sm outline-none focus:border-primary transition-all font-semibold resize-y"
                          placeholder="Ej: Acompañar al niño a leer 15 minutos en las tardes y hacer preguntas sobre el texto..."
                        ></textarea>
                      </td>
                      <td class="p-2">
                        <select 
                          v-model="comp.frecuencia"
                          class="w-full bg-surface border border-outline-variant rounded-lg p-2 text-body-sm outline-none focus:border-primary transition-all font-semibold"
                        >
                          <option value="diaria">Diaria</option>
                          <option value="semanal">Semanal</option>
                          <option value="permanente">Permanente</option>
                        </select>
                      </td>
                      <td class="p-2 text-center">
                        <div class="flex items-center justify-center gap-0.5">
                          <button 
                            @click="guardarActaAcuerdo"
                            :disabled="isSavingActa"
                            class="text-primary hover:bg-primary/10 p-1.5 rounded-lg active:scale-95 transition-all disabled:opacity-50"
                            title="Guardar actividad"
                          >
                            <span v-if="isSavingActa" class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin block"></span>
                            <span v-else class="material-symbols-outlined text-[20px]">save</span>
                          </button>
                          <button 
                            @click="removerCompromisoCasa(index)"
                            class="text-error hover:bg-error-container/20 p-1.5 rounded-lg active:scale-95 transition-all"
                            title="Eliminar actividad"
                          >
                            <span class="material-symbols-outlined text-[20px]">delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Columna derecha: Firmas y descargas -->
          <div class="col-span-4 space-y-md">
            <!-- Card de Firmas -->
            <div class="glass-card p-lg space-y-md border border-outline-variant/30 bg-surface">
              <h3 class="text-title-lg font-bold text-primary flex items-center gap-2 border-b border-outline-variant/30 pb-xs">
                <span class="material-symbols-outlined">draw</span>
                3. Firmas y fecha
              </h3>
              
              <!-- Fecha de firma -->
              <div class="flex flex-col gap-1">
                <label class="font-label-md text-label-sm text-on-surface-variant">Fecha de Firma del acta</label>
                <input 
                  v-model="actaForm.fechaFirma"
                  type="date"
                  class="bg-surface border border-outline-variant rounded-xl p-3 text-body-md outline-none focus:border-primary transition-all font-semibold"
                />
              </div>

              <!-- Listado de actores que firmaron -->
              <div class="space-y-sm">
                <label class="font-label-md text-label-sm text-on-surface-variant block">Actores comprometidos (firmantes)</label>
                
                <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-low cursor-pointer transition-all">
                  <input 
                    v-model="actaForm.firmadoEstudiante"
                    type="checkbox"
                    class="accent-primary w-[18px] h-[18px]"
                  />
                  <span class="text-body-md font-semibold text-on-surface">Estudiante</span>
                </label>

                <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-low cursor-pointer transition-all">
                  <input 
                    v-model="actaForm.firmadoAcudiente"
                    type="checkbox"
                    class="accent-primary w-[18px] h-[18px]"
                  />
                  <span class="text-body-md font-semibold text-on-surface">Acudiente / Familia</span>
                </label>

                <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-low cursor-pointer transition-all">
                  <input 
                    v-model="actaForm.firmadoDocenteApoyo"
                    type="checkbox"
                    class="accent-primary w-[18px] h-[18px]"
                  />
                  <span class="text-body-md font-semibold text-on-surface">Docente de Apoyo (Opcional)</span>
                </label>

                <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-low cursor-pointer transition-all">
                  <input 
                    v-model="actaForm.firmadoDocentesAula"
                    type="checkbox"
                    class="accent-primary w-[18px] h-[18px]"
                  />
                  <span class="text-body-md font-semibold text-on-surface">Docentes de Aula <span v-if="activePiar?.director_nombre" class="text-on-surface-variant font-normal text-label-sm">— {{ activePiar.director_nombre }}</span></span>
                </label>

                <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container-low cursor-pointer transition-all">
                  <input 
                    v-model="actaForm.firmadoDirectivo"
                    type="checkbox"
                    class="accent-primary w-[18px] h-[18px]"
                  />
                  <span class="text-body-md font-semibold text-on-surface">Directivo docente (Rector)</span>
                </label>
              </div>

              <!-- Botones de Acción -->
              <div class="flex flex-col gap-sm pt-xs border-t border-outline-variant/30">
                <button 
                  @click="guardarActaAcuerdo"
                  :disabled="isSavingActa"
                  class="bg-primary text-on-primary font-bold text-label-lg w-full py-3.5 rounded-xl flex items-center justify-center gap-2 hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 shadow-md"
                >
                  <span v-if="isSavingActa" class="w-5 h-5 border-2 border-on-primary border-t-transparent rounded-full animate-spin"></span>
                  <span v-else class="material-symbols-outlined text-[20px]">save</span>
                  Guardar acta y compromisos
                </button>

                <button
                  v-if="piarPuedeFirmarse && activePiar?.estado !== 'firmado'"
                  @click="finalizarPiar"
                  :disabled="isFirmando"
                  class="bg-emerald-600 text-white font-bold text-label-lg w-full py-3.5 rounded-xl flex items-center justify-center gap-2 hover:bg-emerald-700 active:scale-98 transition-all disabled:opacity-50 shadow-md"
                >
                  <span v-if="isFirmando" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span v-else class="material-symbols-outlined text-[20px]">check_circle</span>
                  Finalizar PIAR
                </button>

                <div v-if="activePiar?.estado === 'borrador' && activePiar?.acta_acuerdo && !firmasCompletas" class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-800 text-label-sm">
                  Marca las 4 firmas obligatorias para finalizar (docente de apoyo es opcional).
                </div>

                <button 
                  @click="descargarPDFActa"
                  :disabled="!activePiar?.acta_acuerdo"
                  class="bg-secondary-container text-on-secondary-container font-bold text-label-lg w-full py-3.5 rounded-xl flex items-center justify-center gap-2 hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 shadow-sm border border-outline-variant/30"
                >
                  <span class="material-symbols-outlined text-[20px]">download</span>
                  Descargar PDF oficial
                </button>

                <button 
                  v-if="authStore.user?.rol === 'directivo'"
                  @click="abrirModalExportar"
                  class="bg-primary text-on-primary font-bold text-label-lg w-full py-3.5 rounded-xl flex items-center justify-center gap-2 hover:opacity-90 active:scale-98 transition-all shadow-sm border border-outline-variant/30 mt-3"
                >
                  <span class="material-symbols-outlined text-[20px]">shield</span>
                  Exportar expediente seguro (.openpiar)
                </button>
              </div>

              <div v-if="!activePiar?.acta_acuerdo" class="bg-surface-container-high/50 p-3 rounded-lg border border-outline-variant/30 text-xs text-on-surface-variant">
                ⚠️ Primero debes guardar el acta para habilitar la descarga del PDF.
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

    <!-- Modal de exportar archivo portable .openpiar -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showExportModal"
          class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
          style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
          @click.self="cancelarExportar"
        >
          <div
            style="background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.25); width:100%; max-width:440px; padding:28px; box-sizing:border-box;"
          >
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
              <div style="flex-shrink:0; width:44px; height:44px; border-radius:50%; background:#e0e7ff; display:flex; align-items:center; justify-content:center;">
                <span class="material-symbols-outlined" style="color:#4f46e5; font-size:22px;">shield</span>
              </div>
              <h3 style="font-size:17px; font-weight:700; color:#111827; margin:0;">Exportar expediente seguro</h3>
            </div>

            <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 16px 0;">
              Estás exportando el historial de <strong style="color:#111827;">{{ estudiante?.nombres }} {{ estudiante?.apellidos }}</strong>.
              Se ha generado una clave aleatoria segura de 16 caracteres para cifrar este archivo.
            </p>

            <!-- Clave de cifrado generada -->
            <div style="margin-bottom:12px;">
              <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:6px;">Clave segura generada</label>
              <div style="position:relative; display:flex; align-items:center;">
                <input
                  :type="showPassword ? 'text' : 'password'"
                  v-model="exportPassword"
                  readonly
                  style="width:100%; padding:12px 48px 12px 14px; border:2px solid #e5e7eb; border-radius:10px; font-size:15px; font-family:monospace; font-weight:600; color:#111827; background:#f9fafb; box-sizing:border-box; letter-spacing:0.05em;"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  style="position:absolute; right:12px; background:none; border:none; color:#6b7280; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0;"
                >
                  <span class="material-symbols-outlined" style="font-size:20px;">
                    {{ showPassword ? 'visibility_off' : 'visibility' }}
                  </span>
                </button>
              </div>
            </div>

            <!-- Botones de respaldo -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px;">
              <button
                type="button"
                @click="copiarClave"
                style="display:flex; align-items:center; justify-content:center; gap:8px; padding:10px; border-radius:8px; border:1px solid #d1d5db; background:#fff; font-size:13px; font-weight:600; color:#374151; cursor:pointer; transition:all 0.2s;"
                :style="hasCopiedPassword ? { borderColor:'#10b981', background:'#ecfdf5', color:'#047857' } : {}"
              >
                <span class="material-symbols-outlined" style="font-size:18px;">
                  {{ hasCopiedPassword ? 'check_circle' : 'content_copy' }}
                </span>
                {{ hasCopiedPassword ? 'Copiada' : 'Copiar Clave' }}
              </button>
              <button
                type="button"
                @click="descargarClaveTxt"
                style="display:flex; align-items:center; justify-content:center; gap:8px; padding:10px; border-radius:8px; border:1px solid #d1d5db; background:#fff; font-size:13px; font-weight:600; color:#374151; cursor:pointer; transition:all 0.2s;"
                :style="hasDownloadedPassword ? { borderColor:'#10b981', background:'#ecfdf5', color:'#047857' } : {}"
              >
                <span class="material-symbols-outlined" style="font-size:18px;">
                  {{ hasDownloadedPassword ? 'check_circle' : 'download' }}
                </span>
                {{ hasDownloadedPassword ? 'Descargada' : 'Descargar .txt' }}
              </button>
            </div>

            <!-- Advertencia de seguridad -->
            <div style="background:#fffbeb; border:1px solid #fef3c7; border-radius:10px; padding:12px; display:flex; gap:10px; margin-bottom:18px;">
              <span class="material-symbols-outlined" style="color:#d97706; font-size:20px; flex-shrink:0;">warning</span>
              <span style="font-size:12px; color:#92400e; line-height:1.5;">
                Guarda esta clave. Sin ella, no se podrá descifrar la información en el colegio de destino. No se puede recuperar después de exportar.
              </span>
            </div>

            <!-- Error -->
            <div
              v-if="exportError"
              style="background:#fee2e2; color:#dc2626; border-radius:10px; padding:12px 16px; font-size:13px; margin-bottom:16px;"
            >
              {{ exportError }}
            </div>

            <!-- Actions -->
            <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px;">
              <span v-if="!hasCopiedPassword && !hasDownloadedPassword" style="font-size:11px; color:#ef4444; font-weight:500; margin-right:auto;">
                Respalda la clave para continuar
              </span>
              <button
                @click="cancelarExportar"
                :disabled="isExporting"
                style="padding:10px 16px; border-radius:10px; font-size:14px; font-weight:500; color:#374151; background:transparent; border:1px solid #e5e7eb; cursor:pointer; transition:background .15s;"
                @mouseenter="($event.target as HTMLElement).style.background='#f9fafb'"
                @mouseleave="($event.target as HTMLElement).style.background='transparent'"
              >
                Cancelar
              </button>
              <button
                @click="ejecutarExportar"
                :disabled="isExporting || (!hasCopiedPassword && !hasDownloadedPassword)"
                style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:600; color:#fff; background:#4f46e5; border:none; cursor:pointer; transition:opacity .15s;"
                :style="{ opacity: (isExporting || (!hasCopiedPassword && !hasDownloadedPassword)) ? 0.5 : 1, cursor: (isExporting || (!hasCopiedPassword && !hasDownloadedPassword)) ? 'not-allowed' : 'pointer' }"
              >
                <span v-if="isExporting">Exportando...</span>
                <span v-else>Cifrar y Descargar</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Modal de confirmación para finalizar PIAR -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showConfirmFirmar"
          class="fixed inset-0 z-[9999] flex items-center justify-center p-6"
          style="background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);"
          @click.self="cancelarFirmar"
        >
          <div
            style="background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.25); width:100%; max-width:440px; padding:28px; box-sizing:border-box;"
          >
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
              <div style="flex-shrink:0; width:44px; height:44px; border-radius:50%; background:#fef3c7; display:flex; align-items:center; justify-content:center;">
                <span class="material-symbols-outlined" style="color:#d97706; font-size:22px;">warning</span>
              </div>
              <h3 style="font-size:17px; font-weight:700; color:#111827; margin:0;">Finalizar PIAR</h3>
            </div>

            <p style="font-size:14px; color:#6b7280; line-height:1.6; margin:0 0 20px 0;">
              ¿Estás seguro de finalizar este PIAR? Podrás seguir editando los ajustes razonables durante todo el año lectivo. Asegúrate de haber impreso el acta y recogido las firmas físicas de todos los actores.
            </p>

            <div style="display:flex; justify-content:flex-end; gap:12px;">
              <button
                @click="cancelarFirmar"
                :disabled="isFirmando"
                style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:500; color:#374151; background:transparent; border:1px solid #e5e7eb; cursor:pointer; transition:background .15s;"
                @mouseenter="($event.target as HTMLElement).style.background='#f9fafb'"
                @mouseleave="($event.target as HTMLElement).style.background='transparent'"
              >
                Cancelar
              </button>
              <button
                @click="confirmarFirmar"
                :disabled="isFirmando"
                style="padding:10px 20px; border-radius:10px; font-size:14px; font-weight:600; color:#fff; background:#059669; border:none; cursor:pointer; display:flex; align-items:center; gap:8px; transition:background .15s;"
                @mouseenter="($event.target as HTMLElement).style.background='#047857'"
                @mouseleave="($event.target as HTMLElement).style.background='#059669'"
              >
                <span v-if="isFirmando" class="material-symbols-outlined" style="font-size:18px; animation:spin 1s linear infinite;">progress_activity</span>
                <span v-else class="material-symbols-outlined" style="font-size:18px;">check_circle</span>
                {{ isFirmando ? 'Firmando...' : 'Sí, finalizar' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { usePiarStore } from '../stores/piar'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'
import { storeToRefs } from 'pinia'

const route = useRoute()
const piarStore = usePiarStore()
const authStore = useAuthStore()
const studentsStore = useStudentsStore()
const { activePiar, isLoading, error } = storeToRefs(piarStore)

const estudianteId = route.params.id as string
const estudiante = ref<any>(null)
const entornoSalud = ref<any>(null)

// Exportar expediente portable .openpiar
const showExportModal = ref(false)
const exportPassword = ref('')
const showPassword = ref(false)
const hasCopiedPassword = ref(false)
const hasDownloadedPassword = ref(false)
const isExporting = ref(false)
const exportError = ref('')

function generarClaveSegura(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  const len = 16
  let password = ''
  const temp = new Uint8Array(1)
  while (password.length < len) {
    window.crypto.getRandomValues(temp)
    const val = temp[0] ?? 0
    if (val < 248) {
      password += chars[val % chars.length]
    }
  }
  return password
}

function abrirModalExportar() {
  showExportModal.value = true
  exportPassword.value = generarClaveSegura()
  showPassword.value = false
  hasCopiedPassword.value = false
  hasDownloadedPassword.value = false
  exportError.value = ''
}

function cancelarExportar() {
  showExportModal.value = false
  exportPassword.value = ''
  showPassword.value = false
  hasCopiedPassword.value = false
  hasDownloadedPassword.value = false
  exportError.value = ''
}

async function copiarClave() {
  try {
    await navigator.clipboard.writeText(exportPassword.value)
    hasCopiedPassword.value = true
    showToast('Clave copiada al portapapeles.')
  } catch (e) {
    alert('No se pudo copiar automáticamente. Por favor selecciónala y cópiala manualmente.')
  }
}

function descargarClaveTxt() {
  const content = `CLAVE DE SEGURIDAD OPENPIAR\n` +
                  `==========================\n` +
                  `Estudiante: ${estudiante.value?.nombres} ${estudiante.value?.apellidos}\n` +
                  `Fecha de Exportación: ${new Date().toLocaleString()}\n` +
                  `Clave de Cifrado (16 caracteres): ${exportPassword.value}\n\n` +
                  `IMPORTANTE:\n` +
                  `Guarda este archivo en un lugar seguro. Necesitarás esta clave para importar\n` +
                  `el expediente (.openpiar) en el colegio de destino.\n`
                  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `clave_openpiar_${estudiante.value?.nombres || 'estudiante'}_${estudiante.value?.apellidos || 'expediente'}.txt`.toLowerCase().replace(/\s+/g, '_')
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
  hasDownloadedPassword.value = true
  showToast('Archivo de clave descargado.')
}

async function ejecutarExportar() {
  if (exportPassword.value.length < 16) {
    exportError.value = 'La clave debe tener al menos 16 caracteres.'
    return
  }
  if (!hasCopiedPassword.value && !hasDownloadedPassword.value) {
    exportError.value = 'Debes copiar o descargar la clave para continuar.'
    return
  }

  isExporting.value = true
  exportError.value = ''
  try {
    await studentsStore.exportStudent(estudianteId, exportPassword.value)
    showToast('Expediente exportado exitosamente.')
    showExportModal.value = false
  } catch (e: any) {
    exportError.value = e.message || 'Error al exportar el expediente.'
  } finally {
    isExporting.value = false
  }
}

// Pestañas
const activeTab = ref('caracteristicas')

const isDirectorOrAdmin = computed(() => {
  if (!authStore.user) return false
  if (authStore.user.rol === 'directivo') return true
  if (estudiante.value && estudiante.value.grupo_director_id === authStore.user.id) return true
  return false
})

// TAB 1: Características
const docentesElaboran = ref('')
const gustos = ref('')
const habilidades = ref('')
const isSavingCarac = ref(false)

// TAB 4: Acta de Acuerdo (Anexo 3)
const actaForm = ref({
  fechaFirma: '',
  compromisosAula: '',
  firmadoEstudiante: false,
  firmadoAcudiente: false,
  firmadoDocenteApoyo: false,
  firmadoDocentesAula: false,
  firmadoDirectivo: false,
  compromisosCasa: [] as Array<{ nombre_actividad: string, descripcion_estrategia: string, frecuencia: string }>
})
const isSavingActa = ref(false)

const cargarActaDesdePiar = () => {
  if (activePiar.value?.acta_acuerdo) {
    const acta = activePiar.value.acta_acuerdo
    actaForm.value = {
      fechaFirma: acta.fecha_firma || '',
      compromisosAula: acta.compromisos_aula || '',
      firmadoEstudiante: !!acta.firmado_estudiante,
      firmadoAcudiente: !!acta.firmado_acudiente,
      firmadoDocenteApoyo: !!acta.firmado_docente_apoyo,
      firmadoDocentesAula: !!acta.firmado_docentes_aula,
      firmadoDirectivo: !!acta.firmado_directivo,
      compromisosCasa: acta.compromisos_casa ? acta.compromisos_casa.map((c: any) => ({
        nombre_actividad: c.nombre_actividad,
        descripcion_estrategia: c.descripcion_estrategia,
        frecuencia: c.frecuencia
      })) : []
    }
  } else {
    actaForm.value = {
      fechaFirma: '',
      compromisosAula: '',
      firmadoEstudiante: false,
      firmadoAcudiente: false,
      firmadoDocenteApoyo: false,
      firmadoDocentesAula: false,
      firmadoDirectivo: false,
      compromisosCasa: []
    }
  }
}

const agregarCompromisoCasa = () => {
  actaForm.value.compromisosCasa.push({
    nombre_actividad: '',
    descripcion_estrategia: '',
    frecuencia: 'diaria'
  })
}

const removerCompromisoCasa = (index: number) => {
  actaForm.value.compromisosCasa.splice(index, 1)
}

const guardarActaAcuerdo = async () => {
  isSavingActa.value = true
  const copiaCompromisos = [...actaForm.value.compromisosCasa]
  try {
    for (const comp of copiaCompromisos) {
      if (!comp.nombre_actividad.trim() || !comp.descripcion_estrategia.trim()) {
        throw new Error('Todas las actividades y estrategias en casa deben tener contenido.')
      }
    }
    
    await piarStore.saveActaAcuerdo({
      fechaFirma: actaForm.value.fechaFirma || null,
      compromisosAula: actaForm.value.compromisosAula,
      firmadoEstudiante: actaForm.value.firmadoEstudiante,
      firmadoAcudiente: actaForm.value.firmadoAcudiente,
      firmadoDocenteApoyo: actaForm.value.firmadoDocenteApoyo,
      firmadoDocentesAula: actaForm.value.firmadoDocentesAula,
      firmadoDirectivo: actaForm.value.firmadoDirectivo,
      compromisosCasa: copiaCompromisos.map(c => ({
        nombre_actividad: c.nombre_actividad.trim(),
        descripcion_estrategia: c.descripcion_estrategia.trim(),
        frecuencia: c.frecuencia
      }))
    })
    showToast('Acta de Acuerdo (Anexo 3) guardada con éxito.')
  } catch (e: any) {
    showToast(e.message || 'Error al guardar el acta.', true)
  } finally {
    actaForm.value.compromisosCasa = copiaCompromisos
    isSavingActa.value = false
  }
}

const descargarPDFActa = () => {
  piarStore.downloadActaPDF()
}

const firmasCompletas = computed(() => {
  return actaForm.value.firmadoEstudiante &&
    actaForm.value.firmadoAcudiente &&
    actaForm.value.firmadoDocentesAula &&
    actaForm.value.firmadoDirectivo
})

const piarPuedeFirmarse = computed(() => {
  if (!activePiar.value) return false
  const estado = activePiar.value.estado
  return (estado === 'borrador' || estado === 'en_revision') && firmasCompletas.value && !!activePiar.value.acta_acuerdo
})

const isFirmando = ref(false)
const showConfirmFirmar = ref(false)

const finalizarPiar = () => {
  showConfirmFirmar.value = true
}

const cancelarFirmar = () => {
  showConfirmFirmar.value = false
}

const confirmarFirmar = async () => {
  showConfirmFirmar.value = false
  isFirmando.value = true
  try {
    await piarStore.firmarPiar()
    showToast('PIAR finalizado y firmado. Puedes seguir añadiendo ajustes durante el periodo activo.')
  } catch (e: any) {
    showToast(e.message || 'Error al finalizar el PIAR.', true)
  } finally {
    isFirmando.value = false
  }
}

// Periodos Académicos
const periodos = ref<any[]>([])

async function cargarPeriodos() {
  try {
    const res = await fetch('/api/v1/gestion/periodos', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      periodos.value = await res.json()
    }
  } catch (e) {
    console.error("Error fetching periodos", e)
  }
}

const periodoActivo = computed(() => {
  return periodos.value.find((p: any) => p.activo)
})

function getPeriodoNombre(periodoId: number): string {
  const p = periodos.value.find((per: any) => per.id === periodoId)
  return p ? p.nombre : `Periodo #${periodoId}`
}

function isPeriodoActivo(periodoId: number): boolean {
  const p = periodos.value.find((per: any) => per.id === periodoId)
  return p ? p.activo : false
}

const periodoEdicionNombre = computed(() => {
  if (!isEditingAjuste.value) return ''
  const ajuste = activePiar.value?.ajustes_razonables?.find((a: any) => a.id === ajusteForm.value.id)
  if (ajuste) {
    return getPeriodoNombre(ajuste.periodo_id)
  }
  return ''
})

// Acordeón de periodos
const periodosExpandidos = ref<Record<number, boolean>>({})

function togglePeriodo(periodoId: number) {
  periodosExpandidos.value[periodoId] = !periodosExpandidos.value[periodoId]
}

const ajustesPorPeriodo = computed(() => {
  if (!activePiar.value || !activePiar.value.ajustes_razonables) return {}
  const grouped: Record<number, any[]> = {}
  activePiar.value.ajustes_razonables.forEach((ajuste: any) => {
    const pid = ajuste.periodo_id
    if (!grouped[pid]) {
      grouped[pid] = []
    }
    grouped[pid].push(ajuste)
  })
  return grouped
})

const periodosConAjustes = computed(() => {
  const grouped = ajustesPorPeriodo.value
  const list = periodos.value
    .filter((p: any) => !!grouped[p.id])
    .map((p: any) => ({
      periodo: p,
      ajustes: grouped[p.id]
    }))
    
  // Fallback for periods not found in periodos.value
  const foundIds = new Set(periodos.value.map((p: any) => p.id))
  Object.keys(grouped).forEach((pidStr: string) => {
    const pid = Number(pidStr)
    if (!foundIds.has(pid)) {
      list.push({
        periodo: { id: pid, nombre: `Periodo #${pid}`, activo: false },
        ajustes: grouped[pid]
      })
    }
  })
  
  return list
})

watch(periodosConAjustes, (grupos) => {
  grupos.forEach((g) => {
    if (g.periodo.activo && periodosExpandidos.value[g.periodo.id] === undefined) {
      periodosExpandidos.value[g.periodo.id] = true
    }
  })
}, { immediate: true })

// TAB 2: Formulario Ajuste
const AREAS_VALIDAS = ['Matemáticas', 'Ciencias', 'Lenguaje', 'Convivencia', 'Socialización', 'Participación', 'Autonomía', 'Autocontrol'] as const
const dbAsignaturas = ref<any[]>([])

const ajusteForm = ref({
  id: '',
  area: 'Matemáticas' as string,
  titulo_tema: '',
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
    if (['pre-jardin', 'pre-jardín', 'jardin', 'jardín', 'preescolar', 'transicion', 'transición', '0'].includes(cleanGrade)) {
      return 'transicion'
    }
    return cleanGrade
  } else {
    // Map to EBC ranges
    if (['transicion', 'transición', 'preescolar', 'jardin', 'jardín', 'pre-jardin', 'pre-jardín', '0', '1', '2', '3'].includes(cleanGrade)) return '1-3'
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
  await cargarPeriodos()
  cargarEntornoSalud() // sin await: enriquece contexto IA en background
})

async function cargarEstudiante() {
  try {
    const res = await fetch(`/api/v1/estudiantes/${estudianteId}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      estudiante.value = await res.json()
      if (!isDirectorOrAdmin.value) {
        activeTab.value = 'ajustes'
      }
    }
  } catch (e) {
    console.error("Error fetching student", e)
  }
}

async function cargarEntornoSalud() {
  try {
    const res = await fetch(`/api/v1/estudiantes/${estudianteId}/salud`, {
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
    const res = await fetch('/api/v1/gestion/asignaturas', {
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
  if (activePiar.value?.ajustes_razonables) {
    activePiar.value.ajustes_razonables.forEach((a: any) => {
      if (a._comentarioPuntuacion === undefined) {
        a._comentarioPuntuacion = a.comentario_puntuacion || ''
        a._comentarioGuardado = a.comentario_puntuacion || ''
      }
    })
  }
}

function inicializarFormularios() {
  if (activePiar.value) {
    docentesElaboran.value = authStore.user ? `${authStore.user.nombre} ${authStore.user.apellido}` : ''
    gustos.value = activePiar.value.caracteristicas?.descripcion_gustos_intereses || ''
    habilidades.value = activePiar.value.caracteristicas?.descripcion_habilidades || ''
    cargarActaDesdePiar()
  } else {
    docentesElaboran.value = authStore.user ? `${authStore.user.nombre} ${authStore.user.apellido}` : ''
    cargarActaDesdePiar()
  }
}

// Escuchar cambios en activePiar por si se crea o carga asíncronamente
watch(activePiar, (newPiar) => {
  if (newPiar && !isSavingActa.value) {
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
      await piarStore.updateAjuste({
        ajusteId: ajusteForm.value.id,
        area: ajusteForm.value.area,
        tituloTema: ajusteForm.value.titulo_tema,
        objetivos: ajusteForm.value.objetivos,
        barreras: ajusteForm.value.barreras,
        ajustes: ajusteForm.value.ajustes,
        evaluacion: ajusteForm.value.evaluacion
      })
      showToast("Ajuste razonable actualizado con éxito en la malla.")
    } else {
      await piarStore.saveAjuste({
        area: ajusteForm.value.area,
        tituloTema: ajusteForm.value.titulo_tema,
        objetivos: ajusteForm.value.objetivos,
        barreras: ajusteForm.value.barreras,
        ajustes: ajusteForm.value.ajustes
      })
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
    titulo_tema: ajuste.titulo_tema || '',
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
    titulo_tema: '',
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

async function puntuarAjuste(ajuste: any, star: number) {
  if (!authStore.user) return
  ajuste.puntuacion = star
  const comentario = ajuste._comentarioPuntuacion || ''
  try {
    const updated = await piarStore.puntuarAjuste(ajuste.id, star, comentario)
    // Re-sincronizar desde el array actualizado
    const current = activePiar.value?.ajustes_razonables?.find((a: any) => a.id === ajuste.id)
    if (current) {
      current._comentarioGuardado = comentario
      current._comentarioPuntuacion = comentario
      current.puntuacion = updated.puntuacion ?? star
      current.comentario_puntuacion = updated.comentario_puntuacion
    }
    showToast(`Ajuste valorado con ${star} estrella(s).`)
  } catch (e: any) {
    showToast(e.message || 'Error al puntuar.', true)
  }
}

async function guardarComentarioPuntuacion(ajuste: any) {
  if (!ajuste.puntuacion) return
  const comentario = ajuste._comentarioPuntuacion || ''
  try {
    const updated = await piarStore.puntuarAjuste(ajuste.id, ajuste.puntuacion, comentario)
    // Re-sincronizar desde el array actualizado
    const current = activePiar.value?.ajustes_razonables?.find((a: any) => a.id === ajuste.id)
    if (current) {
      current._comentarioGuardado = comentario
      current._comentarioPuntuacion = comentario
      current.comentario_puntuacion = updated.comentario_puntuacion
    }
    showToast('Comentario guardado.')
  } catch (e: any) {
    showToast(e.message || 'Error al guardar comentario.', true)
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
        const dbaUrl = `/api/v1/curriculum/dba?grado=${searchGrade.value}&area=${searchArea.value}&limit=10`
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
      titulo_tema: ajusteForm.value.titulo_tema || null,
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
      `/api/v1/piars/${activePiar.value.id}/generar_plan_ia`,
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
    let url = `/api/v1/curriculum/${searchType.value}?`
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
  if (clean === 'transicion' || clean === 'preescolar') return 'Preescolar / Transición'
  if (clean === 'jardin' || clean === 'jardín') return 'Jardín'
  if (clean === 'pre-jardin' || clean === 'pre-jardín') return 'Pre-jardín'
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
