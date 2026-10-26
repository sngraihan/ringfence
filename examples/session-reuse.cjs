#!/usr/bin/env node
/**
 * qa-session — satu sesi login yang dipakai ulang untuk verifikasi produksi.
 *
 * Masalah yang diselesaikan (insiden 27/10): setiap percobaan verifikasi login
 * ulang, sesi lama tidak ditutup, akun uji menembus batas server:
 * 409 AUTH_SESSION_LIMIT lalu 429 AUTH_SESSION_ISSUANCE_LIMIT (50 sesi aktif).
 *
 * Cara pakai:
 *   node qa-session.cjs ensure --base https://host --user U --pass P --state qa-state.json
 *   node qa-session.cjs check  --state qa-state.json
 *
 * `ensure` memakai state yang ada bila masih valid (tidak login). Hanya bila
 * tidak valid ia login SEKALI lalu menyimpan state. `check` tidak pernah login.
 *
 * Status keluar: 0 = sesi siap, 2 = perlu login manual/akun terkunci, 3 = galat.
 */
const fs = require('fs');
const path = require('path');

function arg(name, fallback = '') {
  const i = process.argv.indexOf('--' + name);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function loadPlaywright() {
  const candidates = [
    process.env.QA_PLAYWRIGHT,
    'playwright',
    '/home/ubuntu/workspaces/bisnis/routerreceh/deva/node_modules/playwright',
    '/usr/lib/node_modules/playwright',
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      return require(c);
    } catch (err) {
      /* coba kandidat berikutnya */
    }
  }
  throw new Error('playwright tidak ditemukan; set QA_PLAYWRIGHT=/path/to/playwright');
}

async function withBrowser(fn) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  try {
    return await fn(browser);
  } finally {
    await browser.close();
  }
}

async function stateValid(browser, statePath, base) {
  if (!fs.existsSync(statePath)) return { valid: false, why: 'state belum ada' };
  let ctx;
  try {
    ctx = await browser.newContext({ storageState: statePath });
    const page = await ctx.newPage();
    const resp = await page.request.get(base.replace(/\/$/, '') + '/api/user/self', { timeout: 20000 });
    const status = resp.status();
    return { valid: status === 200, why: 'GET /api/user/self ' + status };
  } catch (err) {
    return { valid: false, why: String(err).slice(0, 200) };
  } finally {
    if (ctx) await ctx.close();
  }
}

async function main() {
  const mode = process.argv[2] || 'ensure';
  const base = (arg('base', process.env.QA_BASE || '')).replace(/\/$/, '');
  const statePath = path.resolve(arg('state', 'qa-state.json'));
  const user = arg('user', process.env.QA_USER || '');
  const pass = arg('pass', process.env.QA_PASS || '');

  if (!base && mode !== 'check') {
    out({ ok: false, code: 3, why: '--base wajib' });
    return 3;
  }

  return withBrowser(async (browser) => {
    const before = await stateValid(browser, statePath, base || 'http://127.0.0.1:1');
    if (before.valid) {
      out({ ok: true, code: 0, mode: 'reused', why: before.why, state: statePath });
      return 0;
    }
    if (mode === 'check') {
      out({ ok: false, code: 2, mode: 'check', why: before.why, state: statePath });
      return 2;
    }
    if (!user || !pass) {
      out({ ok: false, code: 3, why: 'sesi tidak valid dan kredensial tidak diberikan', reason: before.why });
      return 3;
    }

    // Login SEKALI. Tidak ada percobaan ulang otomatis: 409/429 berarti harus
    // berhenti dan melapor, bukan menambah sesi baru.
    const ctx = await browser.newContext();
    try {
      const page = await ctx.newPage();
      await page.goto(base + '/signin/', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.fill('input[name=username], input[type=text]', user);
      await page.fill('input[type=password]', pass);
      const wait = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/user/login', { timeout: 60000 });
      await page.keyboard.press('Enter');
      const resp = await wait;
      const status = resp.status();
      if (status !== 200) {
        const body = await resp.text().catch(() => '');
        out({ ok: false, code: 2, mode: 'login', status, why: body.slice(0, 200), hint: 'jangan ulangi login; tutup sesi lain lebih dulu' });
        return 2;
      }
      fs.mkdirSync(path.dirname(statePath), { recursive: true });
      await ctx.storageState({ path: statePath });
      out({ ok: true, code: 0, mode: 'logged_in', state: statePath });
      return 0;
    } finally {
      await ctx.close();
    }
  });
}

main().then((code) => process.exit(code)).catch((err) => {
  out({ ok: false, code: 3, why: String(err).slice(0, 300) });
  process.exit(3);
});