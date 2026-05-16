import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, basename, relative, dirname, join } from 'node:path';
import yaml from 'js-yaml';

const catalogDir = resolve('catalog');
let errors = 0;
let warnings = 0;

function error(file, msg) {
  console.error(`  ERROR  ${file}: ${msg}`);
  errors++;
}
function warn(file, msg) {
  console.warn(`  WARN   ${file}: ${msg}`);
  warnings++;
}

function collectYamlFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = resolve(dir, entry.name);
    if (entry.isDirectory()) results.push(...collectYamlFiles(full));
    else if (entry.name.endsWith('.yaml')) results.push(full);
  }
  return results;
}

const validEntryTypes = new Set(['app', 'cli-tool', 'font', 'tweak', 'dotfile']);
const validDisplay = new Set(['hot', 'visible', 'hidden']);
const validProfiles = new Set(['developer', 'power-user', 'casual', 'gamer', 'creative']);
const validOs = new Set(['windows', 'linux', 'macos']);
const validRegistryTypes = new Set(['dword', 'string', 'qword', 'expandstring', 'multistring', 'binary']);
const validPattern = new Set(['drill-down', 'direct']);

// A parent tile sits at <folder>/<foldername>.yaml.
function isParentTile(file) {
  const base = basename(file, '.yaml');
  return basename(dirname(file)) === base;
}

function validateCategory(rel, content) {
  if (content.name === undefined) error(rel, 'parent tile missing: name');
  if (content.sort === undefined) error(rel, 'parent tile missing: sort');
  else if (typeof content.sort !== 'number') error(rel, `sort must be a number, got ${typeof content.sort}`);
  if (content.pattern && !validPattern.has(content.pattern)) {
    error(rel, `invalid pattern: '${content.pattern}' (valid: ${[...validPattern].join(', ')})`);
  }
  const allowed = new Set(['type', 'name', 'sort', 'pattern', 'description']);
  for (const k of Object.keys(content)) {
    if (!allowed.has(k)) warn(rel, `unexpected field on parent tile: '${k}'`);
  }
}

function validateApp(rel, content) {
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.tags?.length) warn(rel, 'missing or empty: tags');
  if (!content.description) warn(rel, 'missing: description');

  if (content.type && content.type !== 'app' && content.type !== 'cli-tool') {
    error(rel, `invalid type for apps/: '${content.type}'`);
  }
  if (content.display && !validDisplay.has(content.display)) {
    error(rel, `invalid display: '${content.display}'`);
  }
  if (content.profiles) {
    for (const p of content.profiles) if (!validProfiles.has(p)) error(rel, `invalid profile: '${p}'`);
  }
  if (content.os) {
    for (const o of content.os) if (!validOs.has(o)) error(rel, `invalid os: '${o}'`);
  }
  if (!content.install) warn(rel, 'app entry has no install section');
  validateLinks(rel, content);
}

function validateFont(rel, content) {
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.install) warn(rel, 'missing: install');
}

function validateTweak(rel, content) {
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.tags?.length) warn(rel, 'missing or empty: tags');
  if (!content.description) warn(rel, 'missing: description');
  const hasRegistry = content.registry?.length > 0;
  const hasScript = !!content.script;
  if (!hasRegistry && !hasScript) error(rel, 'tweak must have registry entries or a script');
  if (content.registry) {
    for (const entry of content.registry) {
      if (!entry.key) error(rel, 'registry entry missing: key');
      if (entry.name === undefined) error(rel, 'registry entry missing: name');
      if (entry.type && !validRegistryTypes.has(entry.type)) {
        error(rel, `invalid registry type: '${entry.type}'`);
      }
    }
  }
  if (content.profiles) {
    for (const p of content.profiles) if (!validProfiles.has(p)) error(rel, `invalid profile: '${p}'`);
  }
}

function validateLinks(rel, content) {
  if (content.links?.github && !content.links.github.startsWith('https://github.com/')) {
    warn(rel, `suspicious github link: '${content.links.github}'`);
  }
}

function ensureParentChain(file) {
  // Every folder between catalog/<root>/ and the entry must contain a parent tile.
  const rel = relative(catalogDir, file);
  let dir = dirname(file);
  const roots = new Set([
    resolve(catalogDir, 'apps'),
    resolve(catalogDir, 'fonts'),
    resolve(catalogDir, 'tweaks'),
  ]);
  while (!roots.has(dir) && dir.startsWith(catalogDir)) {
    const tile = join(dir, basename(dir) + '.yaml');
    try {
      statSync(tile);
    } catch {
      warn(relative(catalogDir, file), `missing parent tile at ${relative(catalogDir, tile)}`);
      return;
    }
    dir = dirname(dir);
  }
}

// --- Run ---
console.log('Validating catalog...\n');

const sections = [
  { dir: 'apps', entryValidator: validateApp },
  { dir: 'fonts', entryValidator: validateFont },
  { dir: 'tweaks', entryValidator: validateTweak },
];

const allEntryIds = new Map();
let totals = { apps: 0, fonts: 0, tweaks: 0, categories: 0 };

for (const { dir, entryValidator } of sections) {
  const files = collectYamlFiles(resolve(catalogDir, dir));
  for (const file of files) {
    const rel = relative(catalogDir, file);
    let content;
    try { content = yaml.load(readFileSync(file, 'utf8')); }
    catch (e) { error(rel, `YAML parse error: ${e.message}`); continue; }

    if (content?.type === 'category') {
      if (!isParentTile(file)) {
        error(rel, 'type=category must be at <folder>/<folder>.yaml');
      }
      validateCategory(rel, content);
      totals.categories++;
      continue;
    }

    // Entry
    totals[dir]++;
    entryValidator(rel, content);
    ensureParentChain(file);

    // Duplicate ID detection (basename-based, like the legacy index)
    const id = basename(file, '.yaml');
    if (allEntryIds.has(id)) {
      error(rel, `duplicate id '${id}' (also at ${allEntryIds.get(id)})`);
    }
    allEntryIds.set(id, rel);
  }
}

console.log(`\nValidated: ${totals.apps} apps, ${totals.fonts} fonts, ${totals.tweaks} tweaks, ${totals.categories} parent tiles`);
console.log(`Results: ${errors} errors, ${warnings} warnings`);
process.exit(errors > 0 ? 1 : 0);
