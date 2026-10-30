import { cpSync, existsSync, readdirSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const dist = join(root, 'dist');
const docs = join(root, 'docs');
const pages = ['index.html', 'zh/index.html'];
const published = new Set(['index.html', '404.html', '.nojekyll', '_astro', 'brand', 'figures', 'fonts', 'images', 'media', 'zh']);

for (const page of [...pages, '404.html', '.nojekyll']) {
  if (!existsSync(join(dist, page))) throw new Error(`Build the complete static site first: ${page} is missing.`);
}
for (const name of readdirSync(dist)) {
  if (!published.has(name)) throw new Error(`Unexpected build output: ${name}`);
}

// GitHub Pages publishes main's docs/ only; the sources and plain media stay unpublished.
rmSync(docs, { recursive: true, force: true });
cpSync(dist, docs, { recursive: true });
console.log('Prepared the site in docs/ for GitHub Pages.');
