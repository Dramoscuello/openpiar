<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { PiarAsignaturaCobertura } from '../../types/piar'

const props = defineProps<{ asignaturas: PiarAsignaturaCobertura[]; currentUserId?: string; readonly?: boolean }>()
const emit = defineEmits<{ resolve: [asignaturaId: string, estado: 'pendiente' | 'no_requiere', justificacion: string] }>()
const justificaciones = reactive<Record<string, string>>({})
const asignaturasPropias = computed(() => props.currentUserId
  ? props.asignaturas.filter(item => item.docente_id === props.currentUserId)
  : [])
const puedeEditar = (item: PiarAsignaturaCobertura) =>
  !props.readonly && !!props.currentUserId && item.docente_id === props.currentUserId
</script>

<template>
  <section v-if="asignaturasPropias.length" class="rounded-2xl border border-outline-variant/30 bg-surface p-4 space-y-3">
    <div>
      <h3 class="font-bold text-on-surface">Cobertura de asignaturas</h3>
      <p class="text-sm text-on-surface-variant">Cada asignatura debe tener un ajuste o una justificación de por qué no lo requiere.</p>
      <p class="text-sm text-on-surface-variant">Solo el docente asignado puede modificar su cobertura. La justificación se incluye en la matriz del Anexo 2 del PDF, en «Descripción de tipo de ajustes y apoyos».</p>
    </div>
    <div v-for="item in asignaturasPropias" :key="item.id" class="rounded-xl border border-outline-variant/30 p-3 grid md:grid-cols-[1fr_2fr_auto] gap-3 items-center">
      <div>
        <strong class="block">{{ item.nombre_asignatura }}</strong>
        <span v-if="item.area_nombre" class="block text-xs text-outline">{{ item.area_nombre }}</span>
        <span class="text-xs text-outline">{{ item.docente_nombre || 'Sin docente asignado' }}</span>
      </div>
      <input
        v-if="item.estado !== 'con_ajuste' && puedeEditar(item)"
        v-model="justificaciones[item.asignatura_id]"
        :placeholder="item.justificacion || 'Justificación cuando no requiere ajuste'"
        class="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-low"
      />
      <span v-else class="text-sm">{{ item.estado === 'con_ajuste' ? 'Ajuste registrado' : item.justificacion }}</span>
      <div class="flex gap-2">
        <button
          v-if="item.estado !== 'con_ajuste' && puedeEditar(item)"
          type="button"
          class="px-3 py-2 rounded-lg bg-surface-container-high text-sm font-bold"
          @click="emit('resolve', item.asignatura_id, 'no_requiere', justificaciones[item.asignatura_id] ?? item.justificacion ?? '')"
        >No requiere</button>
        <button
          v-if="item.estado === 'no_requiere' && puedeEditar(item)"
          type="button"
          class="px-3 py-2 rounded-lg border text-sm"
          @click="emit('resolve', item.asignatura_id, 'pendiente', '')"
        >Reabrir</button>
      </div>
    </div>
  </section>
</template>
