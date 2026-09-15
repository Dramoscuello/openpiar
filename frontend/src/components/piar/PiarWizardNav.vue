<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import type { PiarSeccionCompletitud } from '../../types/piar'

const props = defineProps<{ secciones: PiarSeccionCompletitud[]; pasosHabilitados?: string[] }>()
const emit = defineEmits<{ select: [codigo: string] }>()

function habilitado(codigo: string): boolean {
  return !props.pasosHabilitados || props.pasosHabilitados.includes(codigo)
}
</script>

<template>
  <nav aria-label="Pasos del PIAR" class="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-2">
    <button
      v-for="(seccion, index) in secciones"
      :key="seccion.codigo"
      type="button"
      :disabled="!habilitado(seccion.codigo)"
      class="rounded-xl border px-3 py-2 text-left transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      :class="seccion.completa ? 'border-green-600/30 bg-green-600/10' : 'border-amber-600/30 bg-amber-500/10'"
      @click="emit('select', seccion.codigo)"
    >
      <span class="block text-xs font-bold text-outline">Paso {{ index + 1 }}</span>
      <span class="block text-sm font-semibold text-on-surface">{{ seccion.nombre }}</span>
      <span class="block text-xs mt-1" :class="seccion.completa ? 'text-green-700' : 'text-amber-700'">
        {{ seccion.completa ? 'Completo' : `${seccion.faltantes.length} pendiente(s)` }}
      </span>
    </button>
  </nav>
</template>
