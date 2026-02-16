import { cpSync } from 'node:fs';
import { resolve } from 'node:path';

const src = resolve('catalog');
const dest = resolve('dist', 'catalog');

cpSync(src, dest, { recursive: true });
console.log('Copied catalog/ to dist/catalog/');
