import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { registerSW } from 'virtual:pwa-register';

import { App } from './App';
import { queryClient } from './api/queryClient';
import { ToastProvider } from './components/Toast';
import './index.css';

// Installs/updates the PWA service worker (no-op during vite dev).
registerSW({ immediate: true });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <App />
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
