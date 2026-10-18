/// <reference types="vitest/config" />
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In dev, forward API calls to the backend so the app works same-origin,
// exactly like the container (where FastAPI serves the built frontend).
const backend = 'http://localhost:8000'
const apiProxy = Object.fromEntries(
  ['/auth', '/ingest', '/query', '/health'].map((p) => [p, backend])
)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    proxy: apiProxy,
  },
  build: {
    rollupOptions: {
      output: {
        // Framework code changes rarely: its own chunks stay cached across deploys
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return 'react'
          if (id.includes('react-router')) return 'router'
          return undefined
        },
      },
    },
  },
  preview: {
    allowedHosts: ['rag-track-frontend.onrender.com', 'localhost'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})
