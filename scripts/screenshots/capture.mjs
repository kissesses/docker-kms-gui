#!/usr/bin/env node
/**
 * Capture KMS-GUI screenshots for GitHub Releases.
 * Usage: node capture.mjs <base-url> <output-dir> [public|auth|all]
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const baseUrl = (process.argv[2] || 'http://127.0.0.1:18080').replace(/\/$/, '');
const outDir = process.argv[3] || 'screenshots';
const mode = process.argv[4] || 'all';

const publicShots = [
  { file: 'dashboard.png', path: '/', theme: 'dark', label: 'Dashboard' },
  { file: 'dashboard-light.png', path: '/', theme: 'light', label: 'Dashboard (light)' },
  { file: 'clients.png', path: '/clients', theme: 'dark', label: 'Clients' },
  { file: 'products.png', path: '/products', theme: 'dark', label: 'Products', fullPage: true },
];

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });

async function capturePublic() {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });

  for (const shot of publicShots) {
    const page = await context.newPage();
    await page.addInitScript((theme) => {
      localStorage.setItem('pykms-theme', theme);
    }, shot.theme);

    const url = `${baseUrl}${shot.path}`;
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1500);

    const outPath = path.join(outDir, shot.file);
    await page.screenshot({ path: outPath, fullPage: !!shot.fullPage });
    console.log(`Captured ${shot.label} → ${outPath}`);
    await page.close();
  }

  await context.close();
}

async function captureAuth() {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  await page.addInitScript(() => {
    localStorage.setItem('pykms-theme', 'dark');
  });

  await page.goto(`${baseUrl}/setup`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForSelector('#username');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'demopassword1234');
  await page.fill('#confirm', 'demopassword1234');

  const setupPath = path.join(outDir, 'setup.png');
  await page.screenshot({ path: setupPath, fullPage: false });
  console.log(`Captured Initial setup → ${setupPath}`);

  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/setup'), { timeout: 30000 });
  await page.waitForTimeout(1000);

  await page.goto(`${baseUrl}/admin/activations`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForSelector('.admin-tabs');
  await page.waitForTimeout(1500);

  const policyPath = path.join(outDir, 'admin-activations.png');
  await page.screenshot({ path: policyPath, fullPage: true });
  console.log(`Captured KMS activation policy → ${policyPath}`);

  await page.close();
  await context.close();
}

if (mode === 'public' || mode === 'all') {
  await capturePublic();
}

if (mode === 'auth' || mode === 'all') {
  await captureAuth();
}

await browser.close();
console.log('Done.');
