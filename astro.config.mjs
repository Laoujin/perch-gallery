import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://laoujin.github.io',
  base: '/perch-gallery/',
  build: {
    assets: '_assets',
  },
});
