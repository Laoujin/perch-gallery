import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, basename } from 'node:path';
import yaml from 'js-yaml';

const catalogDir = resolve('catalog');

function readEntries(subdir) {
  const dir = resolve(catalogDir, subdir);
  const files = readdirSync(dir).filter(f => f.endsWith('.yaml'));

  return files.map(file => {
    const id = basename(file, '.yaml');
    const content = yaml.load(readFileSync(resolve(dir, file), 'utf8'));

    const entry = { id, name: content.name, category: content.category, tags: content.tags };
    if (content.kind) entry.kind = content.kind;

    return entry;
  }).sort((a, b) => a.name.localeCompare(b.name));
}

const index = {
  apps: readEntries('apps'),
  fonts: readEntries('fonts'),
  tweaks: readEntries('tweaks'),
};

const header = '# Auto-generated from catalog entries. Do not edit manually.\n# Run: node scripts/generate-index.mjs\n\n';
const output = header + yaml.dump(index, { lineWidth: 120, flowLevel: 3 });

writeFileSync(resolve(catalogDir, 'index.yaml'), output, 'utf8');

console.log(`Generated index.yaml: ${index.apps.length} apps, ${index.fonts.length} fonts, ${index.tweaks.length} tweaks`);
