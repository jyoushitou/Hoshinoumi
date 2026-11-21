import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// Electron 壳能力标记：仅用于壳内兼容 class，不影响 Web 行为。
const desktop = (window as unknown as { desktopShell?: { capabilities?: { chrome?: string } } }).desktopShell
if (desktop) {
  const major = Number.parseInt(desktop.capabilities?.chrome ?? '0', 10)
  document.documentElement.dataset.desktopShell = 'electron'
  document.documentElement.dataset.chromium = String(major)
  if (major > 0 && major < 120) document.documentElement.classList.add('desktop-compat')
}
