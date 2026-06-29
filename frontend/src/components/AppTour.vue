<!-- Copyright (c) 2026 OpenPiar Contributors — GPL-3.0 -->
<script setup lang="ts">
import { onMounted, watch, nextTick } from 'vue'
import Shepherd from 'shepherd.js'
import 'shepherd.js/dist/css/shepherd.css'
import { useTourStore } from '../stores/tour'

const tourStore = useTourStore()

function buildTour() {
  const tour = new Shepherd.Tour({
    useModalOverlay: true,
    defaultStepOptions: {
      classes: 'shadow-2xl rounded-2xl',
      scrollTo: true,
      cancelIcon: { enabled: true },
    },
  })

  tour.addStep({
    id: 'sidebar',
    title: 'Menú de navegación',
    text: 'Desde aquí puedes moverte entre el <strong>Dashboard</strong>, la lista de <strong>Estudiantes</strong> y la <strong>Gestión Escolar</strong>.',
    attachTo: { element: 'aside', on: 'right' },
    buttons: [
      {
        text: 'Omitir Tour',
        action: () => { tourStore.skip(); tour.cancel() },
        classes: 'shepherd-button-secondary',
      },
      {
        text: 'Siguiente',
        action: tour.next,
      },
    ],
  })

  tour.addStep({
    id: 'topbar',
    title: 'Barra superior',
    text: 'Aquí puedes cambiar entre <strong>modo claro y oscuro</strong>, ver notificaciones, acceder a tu perfil y <strong>cerrar sesión</strong>.',
    attachTo: { element: 'header', on: 'bottom' },
    buttons: [
      {
        text: 'Omitir Tour',
        action: () => { tourStore.skip(); tour.cancel() },
        classes: 'shepherd-button-secondary',
      },
      {
        text: 'Siguiente',
        action: tour.next,
      },
    ],
  })

  tour.addStep({
    id: 'menu-estudiantes',
    title: 'Gestión de estudiantes',
    text: 'Desde el menú lateral, haz clic en <strong>Estudiantes</strong> para ver, registrar o editar los registros pedagógicos (Anexo 1) de tus estudiantes.',
    attachTo: { element: 'aside nav a[href="/estudiantes"], aside nav a[href$="estudiantes"]', on: 'right' },
    buttons: [
      {
        text: 'Omitir Tour',
        action: () => { tourStore.skip(); tour.cancel() },
        classes: 'shepherd-button-secondary',
      },
      {
        text: 'Siguiente',
        action: tour.next,
      },
    ],
  })

  tour.addStep({
    id: 'piar',
    title: 'Crear un PIAR',
    text: 'Una vez registrado un estudiante, puedes iniciar su <strong>Plan Individual de Ajustes Razonables (PIAR)</strong> con ayuda del Agente de IA basado en DUA.',
    attachTo: { element: 'aside nav', on: 'right' },
    buttons: [
      {
        text: 'Omitir Tour',
        action: () => { tourStore.skip(); tour.cancel() },
        classes: 'shepherd-button-secondary',
      },
      {
        text: 'Finalizar Tour',
        action: () => { tourStore.markCompleted(); tour.complete() },
      },
    ],
  })

  return tour
}

watch(() => tourStore.isActive, async (active) => {
  if (active) {
    await nextTick()
    const tour = buildTour()
    tour.start()
  }
})

onMounted(async () => {
  await tourStore.checkAndStart()
})
</script>

<template>
  <div v-if="false" />
</template>
