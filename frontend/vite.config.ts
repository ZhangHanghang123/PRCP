import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/prcp/',
  build: { chunkSizeWarningLimit: 1500 },
  server: {
    port: 5176,
    proxy: {
      '/prcp/api': {
        target: 'http://127.0.0.1:8006',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/prcp/, '')
      }
    }
  }
})