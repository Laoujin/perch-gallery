import { readdirSync, readFileSync } from 'node:fs';
import { resolve, join, basename, dirname, relative } from 'node:path';
import yaml from 'js-yaml';

export interface CatalogEntry {
  id: string;
  name: string;
  category: string;
  tags: string[];
  path: string;
  type: string;
}

interface ParentTile {
  name: string;
  sort: number;
  pattern?: string;
}

const catalogDir = resolve('catalog');

function isParentTile(file: string): boolean {
  return basename(file, '.yaml') === basename(dirname(file));
}

function walkYaml(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkYaml(full));
    else if (entry.name.endsWith('.yaml')) out.push(full);
  }
  return out;
}

function readYaml<T = any>(file: string): T {
  return yaml.load(readFileSync(file, 'utf8')) as T;
}

// Build a map: absolute folder path -> display name (from <folder>/<folder>.yaml)
function buildFolderNameMap(root: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const file of walkYaml(root)) {
    if (!isParentTile(file)) continue;
    const content = readYaml<any>(file);
    if (content?.name) map.set(dirname(file), content.name);
  }
  return map;
}

// Walk up the folder chain from an entry to its root, collecting display names
function categoryFromPath(file: string, folderNames: Map<string, string>, root: string): string {
  const parts: string[] = [];
  let dir = dirname(file);
  while (dir !== root && dir.length > root.length) {
    const name = folderNames.get(dir);
    parts.unshift(name ?? basename(dir));
    dir = dirname(dir);
  }
  return parts.join('/');
}

function loadSection(subdir: string): CatalogEntry[] {
  const root = resolve(catalogDir, subdir);
  const folderNames = buildFolderNameMap(root);
  const entries: CatalogEntry[] = [];
  for (const file of walkYaml(root)) {
    const content = readYaml<any>(file);
    if (content?.type === 'category' && isParentTile(file)) continue; // pure parent tile
    if (!content?.name) continue;
    entries.push({
      id: basename(file, '.yaml'),
      name: content.name,
      category: categoryFromPath(file, folderNames, root),
      tags: content.tags ?? [],
      path: relative(catalogDir, file).replace(/\\/g, '/'),
      type: content.type ?? 'app',
    });
  }
  return entries.sort((a, b) => a.name.localeCompare(b.name));
}

export function loadCatalog() {
  return {
    apps: loadSection('apps'),
    fonts: loadSection('fonts'),
    tweaks: loadSection('tweaks'),
  };
}
