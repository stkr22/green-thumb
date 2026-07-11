import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

// In local dev the backend runs on :8000; proxying /api and /auth mirrors the
// production Traefik routing so cookies stay first-party in both setups.
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // injectManifest (not generateSW) because src/sw.ts carries Web Push
    // handlers on top of workbox precaching.
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'autoUpdate',
      includeAssets: ['icons/*.png'],
      manifest: {
        name: 'Green Thumb',
        short_name: 'Green Thumb',
        description: 'Self-hosted plant care tracker',
        start_url: '/',
        display: 'standalone',
        background_color: '#f5f5f4',
        theme_color: '#059669',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: process.env.DEV_BACKEND_URL ?? 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: process.env.DEV_BACKEND_URL ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
});
