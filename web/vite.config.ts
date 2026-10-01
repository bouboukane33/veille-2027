import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { handleApi } from './server/backend.ts';

export default defineConfig(({ mode }) => {
  const localEnv = { ...loadEnv(mode, process.cwd(), ''), ...process.env };
  return {
    plugins: [
      react(),
      {
        name: 'ccr-local-api',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            const path = req.url?.split('?')[0];
            if (!path?.startsWith('/api/')) return next();
            const headers = new Headers();
            for (const [key, value] of Object.entries(req.headers)) {
              if (value !== undefined)
                headers.set(key, Array.isArray(value) ? value.join(',') : value);
            }
            const response = await handleApi(
              path,
              new Request('http://localhost' + path, { method: req.method, headers }),
              localEnv,
            );
            response.headers.forEach((value, key) => res.setHeader(key, value));
            res.statusCode = response.status;
            res.end(await response.text());
          });
        },
      },
    ],
    build: { chunkSizeWarningLimit: 700 },
    server: { port: 5173 },
  };
});
