<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
defineProps<{
  estado: string
  versionActual: number
  puedeFinalizar: boolean
  busy?: boolean
}>()
const emit = defineEmits<{
  draft: []
  final: []
  finish: []
  reopen: []
}>()
</script>

<template>
  <section class="rounded-2xl border border-outline-variant/30 bg-surface p-4 flex flex-wrap items-center gap-3">
    <button type="button" class="px-4 py-2 rounded-xl border border-primary text-primary font-bold" @click="emit('draft')">
      Descargar borrador
    </button>
    <button
      v-if="estado !== 'firmado'"
      type="button"
      :disabled="!puedeFinalizar || busy"
      class="px-4 py-2 rounded-xl bg-primary text-white font-bold disabled:opacity-40"
      @click="emit('finish')"
    >
      Finalizar y crear versión
    </button>
    <template v-else>
      <button type="button" class="px-4 py-2 rounded-xl bg-green-700 text-white font-bold" @click="emit('final')">
        Descargar PDF final v{{ versionActual }}
      </button>
      <button type="button" class="px-4 py-2 rounded-xl border border-amber-700 text-amber-800 font-bold" @click="emit('reopen')">
        Reabrir para nueva versión
      </button>
    </template>
  </section>
</template>
