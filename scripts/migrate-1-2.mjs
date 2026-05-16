// One-shot migration script for Story 1.2.
// Transforms in-place:
//   - `type: app` + `cli-tool: true` → `type: cli-tool` (cli-tool line removed)
//   - `hot: true` → `display: hot` (in place, preserving position)
// Operates on raw text to preserve YAML formatting, comments, and field order.

import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const catalogDir = resolve('catalog/apps');
let cliToolMigrated = 0;
let hotMigrated = 0;
let visited = 0;

function collect(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) out.push(...collect(p));
    else if (e.name.endsWith('.yaml')) out.push(p);
  }
  return out;
}

for (const file of collect(catalogDir)) {
  visited++;
  const orig = readFileSync(file, 'utf8');
  let text = orig;

  const hadCliTool = /^cli-tool:\s*true\s*$/m.test(text);
  if (hadCliTool) {
    // Promote type: app → type: cli-tool. Tolerate quotes / trailing whitespace.
    text = text.replace(/^type:\s*app\s*$/m, 'type: cli-tool');
    // Remove the now-redundant boolean line, including its trailing newline.
    text = text.replace(/^cli-tool:\s*true\s*\r?\n/m, '');
    cliToolMigrated++;
  }

  const hadHot = /^hot:\s*true\s*$/m.test(text);
  if (hadHot) {
    text = text.replace(/^hot:\s*true\s*$/m, 'display: hot');
    hotMigrated++;
  }

  if (text !== orig) writeFileSync(file, text, 'utf8');
}

console.log(`visited ${visited} files; migrated ${cliToolMigrated} cli-tool, ${hotMigrated} hot`);
