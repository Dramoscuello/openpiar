<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
withDefaults(defineProps<{
  estado: string
  versionActual: number
  puedeFinalizar: boolean
  busy?: boolean
  puedeGestionar?: boolean
}>(), {
  puedeGestionar: true,
})
const emit = defineEmits<{
  draft: []
  final: []
  finish: []
  reopen: []
}>()
</script>

<template>
  <section
    v-if="puedeGestionar || estado === 'firmado'"
    class="rounded-2xl border border-outline-variant/30 bg-surface p-4 flex flex-wrap items-center gap-3"
  >
    <button
      v-if="puedeGestionar"
      type="button"
      class="px-4 py-2 rounded-xl border border-primary text-primary font-bold"
      @click="emit('draft')"
    >
      Descargar borrador
    </button>
    <button
      v-if="puedeGestionar && estado !== 'firmado'"
      type="button"
      :disabled="!puedeFinalizar || busy"
      class="px-4 py-2 rounded-xl bg-primary text-white font-bold disabled:opacity-40"
      @click="emit('finish')"
    >
      Finalizar y crear versión
    </button>
    <template v-if="estado === 'firmado'">
      <button type="button" class="px-4 py-2 rounded-xl bg-green-700 text-white font-bold" @click="emit('final')">
        Descargar PDF final v{{ versionActual }}
      </button>
      <button
        v-if="puedeGestionar"
        type="button"
        class="px-4 py-2 rounded-xl border border-amber-700 text-amber-800 font-bold"
        @click="emit('reopen')"
      >
        Reabrir para nueva versión
      </button>
    </template>
  </section>
</template>
