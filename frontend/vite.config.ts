import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// In local dev the backend runs on :8000; proxying /api and /auth mirrors the
// production Traefik routing so cookies stay first-party in both setups.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: process.env.DEV_BACKEND_URL ?? 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: process.env.DEV_BACKEND_URL ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
});
