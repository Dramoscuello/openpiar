// Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/setup',
      name: 'setup',
      component: () => import('../views/SetupWizardView.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/estudiantes',
      name: 'students',
      component: () => import('../views/StudentsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/estudiantes/formulario/:id?',
      name: 'student-form',
      component: () => import('../views/StudentFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/estudiantes/:id/piar',
      name: 'piar-view',
      component: () => import('../views/PiarView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/gestion-escolar',
      name: 'school-management',
      component: () => import('../views/SchoolManagementView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/directorio',
      name: 'directorio',
      component: () => import('../views/DirectorioView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/gestion-directiva',
      name: 'gestion-directiva',
      component: () => import('../views/DirectivoManagementView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/familia/:codigo',
      name: 'familia',
      component: () => import('../views/FamiliaView.vue'),
    },
    // Fallback redirect
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Inicializar estado del setup wizard si no existe
  if (authStore.setupStatus === null) {
    await authStore.checkSetupStatus()
  }

  const setupCompleted = authStore.isSetupCompleted

  // Regla de Setup Wizard: Si no está completado, obligar a ir a /setup
  if (!setupCompleted && to.name !== 'setup' && to.name !== 'familia') {
    return next({ name: 'setup' })
  }

  // Si está completado, no permitir ir al Setup Wizard
  if (setupCompleted && to.name === 'setup') {
    return next(authStore.isAuthenticated ? { name: 'dashboard' } : { name: 'login' })
  }

  // Rutas con requerimiento de autenticación
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'login' })
  }

  // Rutas con requerimiento de huésped (solo sin autenticar, ej: Login)
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return next({ name: 'dashboard' })
  }

  next()
})

export default router
