import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// On Vercel the SPA is the whole site (base '/'); the API is reached via the
// same-origin rewrites in vercel.json. In dev, proxy the JSON + auth endpoints
// to the running FastAPI backend (default localhost:8080) for real data.
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8080'

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/v1': { target: API_TARGET, changeOrigin: true },
      '/login': { target: API_TARGET, changeOrigin: true },
      '/logout': { target: API_TARGET, changeOrigin: true },
      '/healthz': { target: API_TARGET, changeOrigin: true },
    },
  },
})
