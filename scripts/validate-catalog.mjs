import { readdirSync, readFileSync } from 'node:fs';
import { resolve, basename, relative } from 'node:path';
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
    const fullPath = resolve(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectYamlFiles(fullPath));
    } else if (entry.name.endsWith('.yaml')) {
      results.push(fullPath);
    }
  }
  return results;
}

// --- Load categories ---
const categoriesFile = resolve(catalogDir, 'categories.yaml');
const categoriesRaw = yaml.load(readFileSync(categoriesFile, 'utf8'));

function flattenCategories(obj, prefix = '') {
  const result = new Set();
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}/${key}` : key;
    result.add(fullKey);
    if (value?.children) {
      for (const sub of flattenCategories(value.children, fullKey)) {
        result.add(sub);
      }
    }
  }
  return result;
}

const validCategories = flattenCategories(categoriesRaw);

// --- Valid enum values ---
const validKinds = new Set(['app', 'cli-tool', 'runtime', 'dotfile']);
const validProfiles = new Set(['developer', 'power-user', 'casual', 'gamer', 'creative']);
const validOs = new Set(['windows', 'linux', 'macos']);
const validTypes = new Set(['app', 'font', 'tweak']);
const validRegistryTypes = new Set(['dword', 'string', 'qword', 'expandstring', 'multistring', 'binary']);

// --- Validate entries ---
function validateApp(file, content) {
  const rel = relative(catalogDir, file);
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.category) error(rel, 'missing required field: category');
  if (!content.tags?.length) warn(rel, 'missing or empty: tags');
  if (!content.description) warn(rel, 'missing: description');

  if (content.kind && !validKinds.has(content.kind)) {
    error(rel, `invalid kind: '${content.kind}' (valid: ${[...validKinds].join(', ')})`);
  }

  if (content.profiles) {
    for (const p of content.profiles) {
      if (!validProfiles.has(p)) error(rel, `invalid profile: '${p}'`);
    }
  }

  if (content.os) {
    for (const o of content.os) {
      if (!validOs.has(o)) error(rel, `invalid os: '${o}'`);
    }
  }

  if (content.category && !validCategories.has(content.category)) {
    warn(rel, `category '${content.category}' not in categories.yaml`);
  }

  if (content.kind !== 'dotfile' && !content.install) {
    warn(rel, 'non-dotfile app has no install section');
  }

  validateLinks(rel, content);
}

function validateFont(file, content) {
  const rel = relative(catalogDir, file);
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.category) error(rel, 'missing required field: category');
  if (!content.install) warn(rel, 'missing: install');

  if (content.category && !validCategories.has(content.category)) {
    warn(rel, `category '${content.category}' not in categories.yaml`);
  }
}

function validateTweak(file, content) {
  const rel = relative(catalogDir, file);
  if (!content.name) error(rel, 'missing required field: name');
  if (!content.category) error(rel, 'missing required field: category');
  if (!content.tags?.length) warn(rel, 'missing or empty: tags');
  if (!content.description) warn(rel, 'missing: description');

  const hasRegistry = content.registry?.length > 0;
  const hasScript = !!content.script;
  if (!hasRegistry && !hasScript) {
    error(rel, 'tweak must have registry entries or a script');
  }

  if (content.registry) {
    for (const entry of content.registry) {
      if (!entry.key) error(rel, 'registry entry missing: key');
      if (entry.name === undefined) error(rel, 'registry entry missing: name');
      if (entry.type && !validRegistryTypes.has(entry.type)) {
        error(rel, `invalid registry type: '${entry.type}'`);
      }
    }
  }

  if (content.category && !validCategories.has(content.category)) {
    warn(rel, `category '${content.category}' not in categories.yaml`);
  }

  if (content.profiles) {
    for (const p of content.profiles) {
      if (!validProfiles.has(p)) error(rel, `invalid profile: '${p}'`);
    }
  }
}

function validateLinks(rel, content) {
  if (content.links) {
    if (content.links.github && !content.links.github.startsWith('https://github.com/')) {
      warn(rel, `suspicious github link: '${content.links.github}'`);
    }
  }
}

// --- Check for duplicate IDs ---
function checkDuplicates(files, type) {
  const ids = new Map();
  for (const file of files) {
    const id = basename(file, '.yaml');
    if (ids.has(id)) {
      error(relative(catalogDir, file), `duplicate ${type} id '${id}' (also at ${ids.get(id)})`);
    }
    ids.set(id, relative(catalogDir, file));
  }
}

// --- Run validation ---
console.log('Validating catalog...\n');

const appFiles = collectYamlFiles(resolve(catalogDir, 'apps'));
const fontFiles = collectYamlFiles(resolve(catalogDir, 'fonts'));
const tweakFiles = collectYamlFiles(resolve(catalogDir, 'tweaks'));

checkDuplicates(appFiles, 'app');
checkDuplicates(fontFiles, 'font');
checkDuplicates(tweakFiles, 'tweak');

for (const file of appFiles) {
  try {
    const content = yaml.load(readFileSync(file, 'utf8'));
    validateApp(file, content);
  } catch (e) {
    error(relative(catalogDir, file), `YAML parse error: ${e.message}`);
  }
}

for (const file of fontFiles) {
  try {
    const content = yaml.load(readFileSync(file, 'utf8'));
    validateFont(file, content);
  } catch (e) {
    error(relative(catalogDir, file), `YAML parse error: ${e.message}`);
  }
}

for (const file of tweakFiles) {
  try {
    const content = yaml.load(readFileSync(file, 'utf8'));
    validateTweak(file, content);
  } catch (e) {
    error(relative(catalogDir, file), `YAML parse error: ${e.message}`);
  }
}

// --- Verify index matches files ---
const indexFile = resolve(catalogDir, 'index.yaml');
try {
  const index = yaml.load(readFileSync(indexFile, 'utf8'));
  const appIds = new Set(appFiles.map(f => basename(f, '.yaml')));
  const fontIds = new Set(fontFiles.map(f => basename(f, '.yaml')));
  const tweakIds = new Set(tweakFiles.map(f => basename(f, '.yaml')));

  for (const entry of index.apps || []) {
    if (!appIds.has(entry.id)) error('index.yaml', `app '${entry.id}' in index but no file found`);
  }
  for (const entry of index.fonts || []) {
    if (!fontIds.has(entry.id)) error('index.yaml', `font '${entry.id}' in index but no file found`);
  }
  for (const entry of index.tweaks || []) {
    if (!tweakIds.has(entry.id)) error('index.yaml', `tweak '${entry.id}' in index but no file found`);
  }

  const indexAppIds = new Set((index.apps || []).map(e => e.id));
  const indexFontIds = new Set((index.fonts || []).map(e => e.id));
  const indexTweakIds = new Set((index.tweaks || []).map(e => e.id));

  for (const id of appIds) {
    if (!indexAppIds.has(id)) warn('index.yaml', `app file '${id}' exists but missing from index`);
  }
  for (const id of fontIds) {
    if (!indexFontIds.has(id)) warn('index.yaml', `font file '${id}' exists but missing from index`);
  }
  for (const id of tweakIds) {
    if (!indexTweakIds.has(id)) warn('index.yaml', `tweak file '${id}' exists but missing from index`);
  }
} catch (e) {
  error('index.yaml', `failed to validate index: ${e.message}`);
}

// --- Summary ---
console.log(`\nValidated: ${appFiles.length} apps, ${fontFiles.length} fonts, ${tweakFiles.length} tweaks`);
console.log(`Results: ${errors} errors, ${warnings} warnings`);

process.exit(errors > 0 ? 1 : 0);
