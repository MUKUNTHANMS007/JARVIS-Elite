import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  // Only VITE_-prefixed variables are injected into the browser bundle.
  // Unprefixed secrets (e.g. GEMINI_API_KEY) remain server-side only.
  const env = loadEnv(mode, '.', 'VITE_');

  // DISABLE_HMR is a build-tool flag, not a browser variable — read it from
  // process.env (populated by the shell / dotenv-cli) rather than Vite's bundle env.
  const disableHmr = process.env.DISABLE_HMR === 'true';

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      port: 3001,
      // Optimized: Ignore backend changes to prevent dashboard flickering
      watch: {
        ignored: ['**/backend/**'],
      },
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify — file watching is disabled to prevent flickering during agent edits.
      hmr: !disableHmr,
    },
  };
});
