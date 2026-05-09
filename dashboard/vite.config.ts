import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/query': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/upsert': 'http://localhost:8000',
      '/review': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
    },
  },
})
