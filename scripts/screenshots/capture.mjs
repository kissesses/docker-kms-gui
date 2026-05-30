#!/usr/bin/env node
/**
 * Capture KMS-GUI screenshots for GitHub Releases.
 * Usage: node capture.mjs <base-url> <output-dir>
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const baseUrl = (process.argv[2] || 'http://127.0.0.1:18080').replace(/\/$/, '');
const outDir = process.argv[3] || 'screenshots';

const shots = [
  { file: 'dashboard.png', path: '/', theme: 'dark', label: 'Dashboard' },
  { file: 'dashboard-light.png', path: '/', theme: 'light', label: 'Dashboard (light)' },
  { file: 'clients.png', path: '/clients', theme: 'dark', label: 'Clients' },
  { file: 'products.png', path: '/products', theme: 'dark', label: 'Products' },
];

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

for (const shot of shots) {
  const page = await context.newPage();
  await page.addInitScript((theme) => {
    localStorage.setItem('pykms-theme', theme);
  }, shot.theme);

  const url = `${baseUrl}${shot.path}`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  const outPath = path.join(outDir, shot.file);
  await page.screenshot({ path: outPath, fullPage: shot.path === '/products' });
  console.log(`Captured ${shot.label} → ${outPath}`);
  await page.close();
}

await browser.close();
console.log('Done.');
