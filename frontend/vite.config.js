import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// The dashboard is served under a base path (default /dashboard) so it can
// coexist with other apps on the same host. Override at build time with:
//   DASHBOARD_BASE_PATH=/something npm run build
// Keep this in sync with DASHBOARD_BASE_PATH in the backend .env.
export default defineConfig(() => {
  const base = (process.env.DASHBOARD_BASE_PATH || '/dashboard').replace(/\/$/, '') + '/'
  return {
    base,
    plugins: [react()],
    server: {
      // Dev proxy: forward API + asset routes (under the base path) to the backend.
      proxy: {
        [base + 'api']: { target: 'http://localhost:8000', changeOrigin: true },
        [base + 'previews']: { target: 'http://localhost:8000', changeOrigin: true },
        [base + 'media']: { target: 'http://localhost:8000', changeOrigin: true },
      },
    },
    build: { outDir: 'dist' },
  }
})
