import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { installApiInterceptor, setAuthHandlers } from './api/client'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const authStore = useAuthStore(pinia)
setAuthHandlers({
  getToken: () => authStore.token,
  refresh: () => authStore.refreshSession(),
  onSessionExpired: () => authStore.sessionExpired(),
})
installApiInterceptor()

app.mount('#app')
