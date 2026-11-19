import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 27006,
    host: '127.0.0.1',
    proxy: {
      '/api': { target: 'http://127.0.0.1:27004', changeOrigin: true },
      '/internal': { target: 'http://127.0.0.1:27004', changeOrigin: true },
      '/healthz': { target: 'http://127.0.0.1:27004', changeOrigin: true },
      '/readyz': { target: 'http://127.0.0.1:27004', changeOrigin: true },
    },
  },
  test: { environment: 'jsdom', globals: true, exclude: ['e2e/**', 'node_modules/**'] },
})
