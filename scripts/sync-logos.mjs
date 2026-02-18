import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, basename } from 'node:path';
import yaml from 'js-yaml';

const catalogDir = resolve('catalog');
const logosDir = resolve(catalogDir, 'logos');

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

function extractEntries() {
  const entries = [];

  for (const subdir of ['apps', 'fonts']) {
    const dir = resolve(catalogDir, subdir);
    if (!existsSync(dir)) continue;

    for (const file of collectYamlFiles(dir)) {
      const id = basename(file, '.yaml');
      const content = yaml.load(readFileSync(file, 'utf8'));
      const website = content?.links?.website;
      const github = content?.links?.github;
      entries.push({ id, website, github });
    }
  }

  return entries;
}

function extractDomain(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

function extractGitHubOwner(url) {
  const match = url?.match(/github\.com\/([^/]+)/);
  return match ? match[1] : null;
}

async function downloadImage(url) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok) return null;

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.startsWith('image/')) return null;

  const buffer = Buffer.from(await response.arrayBuffer());
  // Skip tiny images (likely default/placeholder favicons)
  if (buffer.length < 200) return null;

  return buffer;
}

async function main() {
  mkdirSync(logosDir, { recursive: true });

  const entries = extractEntries();
  console.log(`Found ${entries.length} catalog entries.\n`);

  let downloaded = 0;
  let skipped = 0;
  let failed = 0;

  for (const { id, website, github } of entries) {
    const outputPath = resolve(logosDir, `${id}.png`);

    if (existsSync(outputPath)) {
      skipped++;
      continue;
    }

    process.stdout.write(`  ${id}...`);

    // Try Google Favicon API from website domain
    const domain = extractDomain(website);
    if (domain) {
      const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
      const image = await downloadImage(faviconUrl);
      if (image) {
        writeFileSync(outputPath, image);
        console.log(` favicon (${domain})`);
        downloaded++;
        await new Promise(r => setTimeout(r, 50));
        continue;
      }
    }

    // Fallback: GitHub org/user avatar
    const owner = extractGitHubOwner(github);
    if (owner) {
      const avatarUrl = `https://github.com/${owner}.png?size=128`;
      const image = await downloadImage(avatarUrl);
      if (image) {
        writeFileSync(outputPath, image);
        console.log(` github (${owner})`);
        downloaded++;
        await new Promise(r => setTimeout(r, 50));
        continue;
      }
    }

    console.log(' no source');
    failed++;
  }

  console.log(`\nDone: ${downloaded} downloaded, ${skipped} skipped, ${failed} no source.`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
