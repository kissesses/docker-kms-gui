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
  { file: 'keys.png', path: '/keys', theme: 'dark', label: 'GVLK keys', fullPage: true },
  { file: 'protocol.png', path: '/protocol', theme: 'dark', label: 'Protocol', fullPage: true },
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

    await page.goto(`${baseUrl}${shot.path}`, { waitUntil: 'networkidle', timeout: 60000 });
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

  await page.screenshot({ path: path.join(outDir, 'setup.png') });
  console.log('Captured Initial setup → setup.png');

  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/setup'), { timeout: 30000 });
  await page.waitForTimeout(800);

  const loginCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const loginPage = await loginCtx.newPage();
  await loginPage.addInitScript(() => {
    localStorage.setItem('pykms-theme', 'dark');
  });
  await loginPage.goto(`${baseUrl}/login`, { waitUntil: 'networkidle', timeout: 60000 });
  await loginPage.waitForSelector('#open-keys-picker', { timeout: 15000 });
  await loginPage.click('#open-keys-picker');
  await loginPage.waitForSelector('#keys-picker-modal:not([hidden])', { timeout: 10000 });
  await loginPage.waitForTimeout(500);
  const guide = loginPage.locator('#keys-picker-guide');
  if (await guide.count()) {
    await guide.evaluate((el) => { el.open = true; });
    await loginPage.waitForTimeout(400);
  }
  await loginPage.screenshot({ path: path.join(outDir, 'login-keys.png'), fullPage: true });
  console.log('Captured Login GVLK picker → login-keys.png');
  await loginCtx.close();

  await page.goto(`${baseUrl}/admin/activations`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForSelector('.admin-tabs', { timeout: 15000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(outDir, 'admin-activations.png'), fullPage: true });
  console.log('Captured KMS activation policy → admin-activations.png');

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
