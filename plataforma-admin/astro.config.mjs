import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  base: '/plataforma',
  server: {
    port: 4322,
    host: 'localhost'
  },
  integrations: [
    tailwind({
      applyBaseStyles: false
    })
  ]
});

