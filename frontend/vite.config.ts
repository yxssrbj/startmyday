import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: Number(process.env.MORNING_VITE_PORT ?? 5173),
    strictPort: true,
    proxy: { '/api': process.env.MORNING_API_ORIGIN ?? 'http://127.0.0.1:8000' },
  },
});
