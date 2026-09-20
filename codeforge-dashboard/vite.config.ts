import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Inside docker-compose the backend is reachable as http://backend:8000
const target = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      // ws: true is required for /api/v1/ws/{task_id} to upgrade through the proxy
      '/api': { target, changeOrigin: true, ws: true },
      '/health': { target, changeOrigin: true },
    },
  },
});
