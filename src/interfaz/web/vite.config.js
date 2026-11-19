import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const directorioWeb = dirname(fileURLToPath(import.meta.url));
const raizProyecto = resolve(directorioWeb, '../../..');

export default defineConfig(({ mode }) => {
  const variables = loadEnv(mode, raizProyecto, '');

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: variables.API_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (ruta) => ruta.replace(/^\/api/, ''),
          configure: (proxy) => {
            if (variables.API_AUTH_TOKEN) {
              proxy.on('proxyReq', (solicitud) => {
                solicitud.setHeader(
                  'Authorization',
                  `Bearer ${variables.API_AUTH_TOKEN}`,
                );
              });
            }
          },
        },
      },
    },
  };
});
