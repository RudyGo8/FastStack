import { createSSRApp } from 'vue'
import App from './App.vue'
import i18n from './locales'
import router from './router/index.js'
import 'uno.css'

const pinia = createPinia()
pinia.use(persistPlugin)
export function createApp() {
  const app = createSSRApp(App)
  app.use(router)
  app.use(pinia)
  app.use(i18n)
  return {
    app,
  }
}
