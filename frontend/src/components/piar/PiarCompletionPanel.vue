<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import type { PiarCompletitud } from '../../types/piar'
import PiarWizardNav from './PiarWizardNav.vue'

defineProps<{
  value: PiarCompletitud
  loading?: boolean
  pasosHabilitados?: string[]
}>()
const emit = defineEmits<{ open: [codigo: string] }>()
</script>

<template>
  <section class="rounded-2xl border border-outline-variant/30 bg-surface p-4 space-y-3">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h2 class="font-bold text-on-surface">Completitud del formato oficial</h2>
        <p class="text-sm text-on-surface-variant">El PDF final se habilita al resolver las siete secciones.</p>
      </div>
      <strong class="text-2xl text-primary">{{ value.porcentaje }}%</strong>
    </div>
    <div class="h-2 rounded-full bg-surface-container-high overflow-hidden">
      <div class="h-full bg-primary transition-all" :style="{ width: `${value.porcentaje}%` }"></div>
    </div>
    <PiarWizardNav
      :secciones="value.secciones"
      :pasos-habilitados="pasosHabilitados"
      @select="emit('open', $event)"
    />
  </section>
</template>
