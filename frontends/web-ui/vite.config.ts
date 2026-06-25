import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // BossSignal backend (port 8080)
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      // HiveAPI backend (port 8090) — uses /v1/* (no /api/ prefix)
      '/v1': {
        target: 'http://localhost:8090',
        changeOrigin: true,
      },
    },
  },
})
