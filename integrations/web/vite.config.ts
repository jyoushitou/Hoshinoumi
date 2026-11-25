import { fileURLToPath, URL } from 'node:url'
import packageJson from './package.json'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
const apiProxy = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:27005'
export default defineConfig({
  base: './',
  define: { __APP_VERSION__: JSON.stringify(packageJson.version) },
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 27006,
    host: '0.0.0.0',
    proxy: {
      '/api': { target: apiProxy, changeOrigin: true },
      '/internal': { target: apiProxy, changeOrigin: true },
      '/healthz': { target: apiProxy, changeOrigin: true },
      '/readyz': { target: apiProxy, changeOrigin: true },
    },
  },
  test: { environment: 'jsdom', globals: true, exclude: ['e2e/**', 'node_modules/**'] },
})
