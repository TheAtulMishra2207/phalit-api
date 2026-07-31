#!/usr/bin/env node
'use strict';
/**
 * KAR-093 STEP 9 · DRIVER v2
 * Usage: node kar093_step9_driver2.js <playwright|jsdom> [--certify]
 *
 * SHAPED BY THE CERTIFYING ENVIRONMENT, NOT MINE.
 * Every QA run so far has required hand adaptation: page.goto is blocked by
 * container policy, the Node `playwright` package is absent, and jsdom is
 * absent. A gate that needs the verifier to patch it before it runs is not
 * finished, so v2 removes each of those adaptations rather than documenting
 * them.
 *
 *   navigation      setContent is the ONLY path. goto is never called.
 *   package         resolves `playwright` OR `playwright-core`, in that order.
 *   blocked assets  fulfilled with an empty 200, never aborted. Aborting made
 *                   Chromium log "Failed to load resource: net::ERR_FAILED",
 *                   which v1 then counted as a page runtime error and used to
 *                   fail an otherwise clean fixture.
 *   errors          only pageerror and JS console errors count. Network-level
 *                   console noise is recorded separately and never gates.
 *
 * CERTIFICATION FAILS CLOSED. certify() returns true only when conformance has
 * passed IN THIS PROCESS and the observed runtime matches the pins exactly.
 * A CLI flag can no longer assert certification, which is what v1 allowed.
 */

const fs = require('fs');

/**
 * Conformance state lives in a module-private WeakSet. A driver cannot mark
 * ITSELF as conformant, and no caller outside this module can either. v2 had a
 * public markConformancePassed() that nothing ever called, so certify() could
 * never return true; a freely callable public setter would have been the other
 * half of that mistake.
 */
const CONFORMANT = new WeakSet();

// ── Pins, bound to the environment that actually drives the browser ────────
// Not the versions that happen to install in my sandbox. That was the error in
// v1: 1.62.0 was pinned because it installed here, not because it certifies.
const PINS = {
  node: 'v22.16.0',
  playwrightMinor: '1.57',          // matched as a major.minor prefix
  chromiumMajor: '144',             // exact build recorded post-launch
  chromiumPath: '/usr/bin/chromium' // the certifying host's system browser
};

function resolvePlaywright() {
  for (const name of ['playwright', 'playwright-core']) {
    try {
      const mod = require(name);
      const ver = require(name + '/package.json').version;
      return { mod, name, version: ver };
    } catch (e) { /* try the next */ }
  }
  throw new Error('neither "playwright" nor "playwright-core" is installed');
}

// ── PLAYWRIGHT ────────────────────────────────────────────────────────────
class PlaywrightDriver {
  constructor(opts) {
    this.opts = opts || {};
    this._pageErrors = [];      // gating
    this._networkNoise = [];    // recorded, never gating
    this._requests = [];
    this._conformancePassed = false;
  }

  describe() {
    return {
      name: 'playwright-chromium',
      versions: {
        node: process.version,
        playwrightPackage: this._pw ? this._pw.name : '(not resolved)',
        playwright: this._pw ? this._pw.version : '(not resolved)',
        chromium: this._chromium || '(not launched)',
        executablePath: this._execPath || '(not declared)',
        managedBrowserPath: this._managedPath || '(none)'
      }
    };
  }

  /** Certification is earned in-process, never asserted by a flag. */
  certify() {
    const v = this.describe().versions;
    const reasons = [];
    if (!CONFORMANT.has(this)) reasons.push('driver conformance has not passed in this process');
    const caps = this.capabilities();
    Object.keys(caps).forEach(k => { if (!caps[k]) reasons.push(`driver declares no ${k} capability`); });
    if (v.node !== PINS.node) reasons.push(`node ${v.node} != pinned ${PINS.node}`);
    if (!String(v.playwright).startsWith(PINS.playwrightMinor))
      reasons.push(`playwright ${v.playwright} is not ${PINS.playwrightMinor}.x`);
    if (!String(v.chromium).startsWith(PINS.chromiumMajor + '.'))
      reasons.push(`chromium ${v.chromium} is not ${PINS.chromiumMajor}.x`);
    if (!this._execPath)
      reasons.push('no executablePath was declared; a certifying run must name the browser it drives');
    return { certifying: reasons.length === 0, reasons, observed: v };
  }

  /**
   * Declared capabilities. A driver that cannot observe a condition must SAY SO
   * rather than let the corresponding assertion pass by default. jsdom has no
   * layout, so it cannot see an obstructed target: under jsdom the real gate's
   * overlay bug was invisible, and under Chromium it was fatal. That asymmetry
   * is now a declared property instead of a surprise.
   */
  capabilities() { return { layout: true, obstruction: true, viewport: true }; }

  async open(htmlSource, { routes }) {
    this._pageErrors = []; this._networkNoise = []; this._requests = [];
    this._pw = resolvePlaywright();
    const { chromium } = this._pw.mod;
    const launchOpts = { headless: true };
    // No silent fallback to a bundled or cached browser. A certifying run must
    // name the executable it drives.
    if (this.opts.executablePath) {
      if (!fs.existsSync(this.opts.executablePath))
        throw new Error(`executablePath does not exist: ${this.opts.executablePath}`);
      launchOpts.executablePath = this.opts.executablePath;
    }
    this.browser = await chromium.launch(launchOpts);
    this._chromium = this.browser.version();
    // The SUPPLIED path is authoritative. Preferring chromium.executablePath()
    // would report a bundled binary while a system one was actually launched.
    this._execPath = this.opts.executablePath || null;
    let managed = null;
    try { managed = chromium.executablePath && chromium.executablePath(); } catch (e) { managed = null; }
    this._managedPath = managed;
    this.context = await this.browser.newContext();
    this.page = await this.context.newPage();

    this.page.on('pageerror', e =>
      this._pageErrors.push({ kind: 'pageerror', message: String(e && e.message || e).slice(0, 300) }));
    this.page.on('console', m => {
      if (m.type() !== 'error') return;
      const t = m.text();
      // Network-level failures are not JS defects. v1 conflated them and used
      // an aborted font request to fail a clean page.
      if (/Failed to load resource|net::ERR_/.test(t)) { this._networkNoise.push(t.slice(0, 200)); return; }
      this._pageErrors.push({ kind: 'console', message: t.slice(0, 300) });
    });

    await this.context.route('**/*', async route => {
      const req = route.request();
      const url = req.url();
      this._requests.push({ url, method: req.method(), headers: req.headers() });
      for (const r of routes) {
        if (r.match(url)) {
          const body = await r.body();
          return route.fulfill({
            status: (typeof r.status === 'number' ? r.status : 200),
            contentType: 'application/json',
            body: JSON.stringify(body)
          });
        }
      }
      // Unrouted third-party assets get an empty 200 rather than an abort, so
      // no console error is generated and a certified run never touches the net.
      return route.fulfill({ status: 200, contentType: 'text/plain', body: '' });
    });

    // setContent ONLY. goto is blocked by the certifying host's policy.
    await this.page.setContent(htmlSource, { waitUntil: 'load' });
  }

  async evaluate(fn, ...args) { return this.page.evaluate(fn, args.length === 1 ? args[0] : args); }
  async click(selector, index) {
    const loc = this.page.locator(selector).nth(index || 0);
    await loc.scrollIntoViewIfNeeded({ timeout: 5000 });
    await loc.click({ timeout: 5000 });
  }
  async isVisible(selector) { return this.page.locator(selector).first().isVisible(); }
  async wait(ms) { await this.page.waitForTimeout(ms); }
  async errors() { return this._pageErrors.slice(); }
  async networkNoise() { return this._networkNoise.slice(); }
  async requests() { return this._requests.slice(); }
  async close() { if (this.browser) await this.browser.close(); }
}

// ── JSDOM (development only) ──────────────────────────────────────────────
class JsdomDriver {
  constructor() { this._pageErrors = []; this._networkNoise = []; this._requests = []; }
  describe() {
    let jsdomVersion = '(not installed)';
    try { jsdomVersion = require('jsdom/package.json').version; } catch (e) { /* optional */ }
    return { name: 'jsdom (DEVELOPMENT ONLY)',
             versions: { node: process.version, jsdom: jsdomVersion,
                         playwright: '(n/a)', chromium: '(n/a)', executablePath: '(n/a)' } };
  }
  certify() { return { certifying: false, reasons: ['jsdom cannot certify Step 9 closure'], observed: this.describe().versions }; }
  // No layout engine: obstruction and viewport conditions are unobservable.
  capabilities() { return { layout: false, obstruction: false, viewport: false }; }

  async open(htmlSource, { routes }) {
    // Reset on every open. The orchestrator must reuse the conformance-granted
    // instance, so a stale error from the conformance page would otherwise be
    // reported as a defect in the subject.
    this._pageErrors = []; this._networkNoise = []; this._requests = [];
    const { JSDOM, VirtualConsole } = require('jsdom');
    const vc = new VirtualConsole();
    vc.on('jsdomError', e => {
      const m = String(e && e.message || e);
      if (/Not implemented:/.test(m)) { this._networkNoise.push(m); return; }
      this._pageErrors.push({ kind: 'error', message: m.slice(0, 300) });
    });
    this.dom = new JSDOM(htmlSource, { runScripts: 'dangerously', pretendToBeVisual: true,
                                       virtualConsole: vc, url: 'https://kar093.local/subject' });
    const w = this.dom.window;
    this.w = w;
    w.fetch = async (url, opts) => {
      const u = String(url);
      this._requests.push({ url: u, method: (opts && opts.method) || 'GET', headers: (opts && opts.headers) || {} });
      for (const r of routes) {
        if (r.match(u)) {
          const body = await r.body();
          const status = (typeof r.status === 'number' ? r.status : 200);
          return { ok: r.ok !== false && status < 400, status,
                   json: async () => body, text: async () => JSON.stringify(body) };
        }
      }
      return { ok: true, status: 200, json: async () => ({}), text: async () => '' };
    };
    await new Promise(r => setTimeout(r, 2200));
  }
  async evaluate(fn, ...args) {
    const payload = args.length === 1 ? args[0] : args;
    return this.w.eval('(' + fn.toString() + ')(' + JSON.stringify(payload === undefined ? null : payload) + ')');
  }
  async click(selector, index) {
    const el = this.w.document.querySelectorAll(selector)[index || 0];
    if (!el) throw new Error(`click: no element at ${selector}[${index || 0}]`);
    el.dispatchEvent(new this.w.MouseEvent('click', { bubbles: true }));
  }
  async isVisible(selector) {
    const el = this.w.document.querySelector(selector);
    if (!el) return false;
    // jsdom has no layout; approximate with the class the stylesheet keys on.
    return !(el.classList.contains('open') === false && /drawer|overlay/.test(el.id || ''));
  }
  async wait(ms) { await new Promise(r => setTimeout(r, ms)); }
  async errors() { return this._pageErrors.slice(); }
  async networkNoise() { return this._networkNoise.slice(); }
  async requests() { return this._requests.slice(); }
  async close() { if (this.dom) this.dom.window.close(); }
}

// ── CONFORMANCE ───────────────────────────────────────────────────────────
// v1's page tested an unobstructed button, so it never exercised the state that
// broke the real gate: an open overlay covering the next target. That case is
// now first-class.
const CONFORMANCE_PAGE = `<!doctype html><html><head><style>
  #veil{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;z-index:10;}
  #veil.on{display:block;}
  #target{position:relative;z-index:1;}
  #far{margin-top:4000px;}
</style></head><body>
<div id="root"><span class="tag">alpha</span><span class="tag">beta</span></div>
<button id="btn">go</button>
<button id="target">target</button>
<button id="far">far</button>
<div id="veil"></div>
<div id="out">idle</div>
<script>
  window.__clicks = 0; window.__target = 0; window.__far = 0;
  document.getElementById('btn').addEventListener('click', function () {
    window.__clicks++; document.getElementById('out').textContent = 'clicked:' + window.__clicks;
  });
  document.getElementById('target').addEventListener('click', function () { window.__target++; });
  document.getElementById('far').addEventListener('click', function () { window.__far++; });
  window.__veil = function (on) { document.getElementById('veil').classList.toggle('on', !!on); };
  window.__fetched = null;
  window.__doFetch = function () {
    return fetch('https://example.invalid/probe', { method: 'POST', headers: { 'X-Probe': '1' } })
      .then(function (r) { return r.json(); })
      .then(function (j) { window.__fetched = j.marker; })
      .catch(function (e) { window.__fetched = 'ERR:' + e.message; });
  };
  window.__unrouted = function () {
    return fetch('https://fonts.example/x.css').then(function(){ return 'ok'; }).catch(function(e){ return 'ERR'; });
  };
  setTimeout(function () { document.getElementById('out').setAttribute('data-late', 'yes'); }, 300);
  window.__throwLater = function () { setTimeout(function () { throw new Error('CONFORMANCE_PAGE_ERROR'); }, 10); };
</script></body></html>`;

async function runDriverConformance(DriverClass, log, opts) {
  log = log || console.log;
  const results = [];
  const t = (name, ok, detail) => { results.push({ name, ok, detail });
    log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}${!ok && detail ? ' — ' + detail : ''}`); };
  const skip = (name, why) => { results.push({ name, skipped: true, detail: why });
    log(`  SKIP ${name} — driver declares no ${why}`); };

  const d = new DriverClass(opts);
  try {
    await d.open(CONFORMANCE_PAGE, {
      routes: [{ match: u => u.includes('example.invalid'), body: async () => ({ marker: 'ROUTED_OK' }) }]
    });

    const tags = await d.evaluate(() => Array.from(document.querySelectorAll('.tag')).map(e => e.textContent));
    t('evaluate returns serialisable DOM data', JSON.stringify(tags) === '["alpha","beta"]', JSON.stringify(tags));
    t('evaluate passes arguments into the page realm', (await d.evaluate(x => x.a + 1, { a: 41 })) === 42);

    await d.click('#btn'); await d.wait(50);
    t('click dispatches a real listener', (await d.evaluate(() => window.__clicks)) === 1);
    await d.click('#btn'); await d.wait(50);
    t('click is repeatable', (await d.evaluate(() => window.__clicks)) === 2);

    // THE CASE THAT BROKE THE REAL GATE. An element far down the page must be
    // reachable; v1 used force:true and still failed with "outside of viewport".
    await d.click('#far'); await d.wait(50);
    t('click scrolls an out-of-viewport target into reach', (await d.evaluate(() => window.__far)) === 1);

    // And an obstructed target must FAIL rather than silently succeed, so the
    // gate learns to close the drawer instead of forcing through the overlay.
    const caps = d.capabilities();
    if (!caps.obstruction) {
      skip('an obstructed target is not silently clicked through', 'obstruction capability');
      skip('the same target is clickable once unobstructed', 'obstruction capability');
    } else {
      await d.evaluate(() => window.__veil(true));
      let obstructedThrew = false, thrown = '(none)';
      try { await d.click('#target'); }
      catch (e) { obstructedThrew = true; thrown = (e && e.name ? e.name + ': ' : '') + String(e && e.message || e).split('\n')[0].slice(0, 120); }
      const targetHits = await d.evaluate(() => window.__target);
      await d.evaluate(() => window.__veil(false));
      // BOTH conditions. An OR passes when the click lands on the covered
      // element and the call then throws, which is the exact behaviour this
      // case exists to reject.
      t('an obstructed target is not silently clicked through',
        obstructedThrew === true && targetHits === 0,
        `threw=${obstructedThrew} hits=${targetHits} error=${thrown}`);
      log(`       obstruction evidence: threw=${obstructedThrew} hits=${targetHits} error=${thrown}`);
      await d.click('#target'); await d.wait(50);
      t('the same target is clickable once unobstructed', (await d.evaluate(() => window.__target)) === targetHits + 1);
    }

    await d.wait(400);
    t('wait allows page timers to run',
      (await d.evaluate(() => document.getElementById('out').getAttribute('data-late'))) === 'yes');

    await d.evaluate(() => window.__doFetch()); await d.wait(300);
    t('network route is intercepted and fulfilled', (await d.evaluate(() => window.__fetched)) === 'ROUTED_OK');

    const probe = (await d.requests()).find(r => r.url.includes('example.invalid'));
    t('request method and headers are observable',
      !!probe && probe.method === 'POST' && Object.keys(probe.headers).some(k => k.toLowerCase() === 'x-probe'));

    // An unrouted asset must not manufacture a page error.
    const before = (await d.errors()).length;
    await d.evaluate(() => window.__unrouted()); await d.wait(300);
    t('an unrouted asset does not become a page error', (await d.errors()).length === before);

    await d.evaluate(() => window.__throwLater()); await d.wait(250);
    t('page runtime errors are captured',
      (await d.errors()).some(e => /CONFORMANCE_PAGE_ERROR/.test(e.message)));

    const desc = d.describe();
    t('describe reports name and versions after launch',
      !!(desc && desc.name && desc.versions && desc.versions.node));
    if (DriverClass === PlaywrightDriver)
      t('chromium version is recorded post-launch, not a placeholder',
        !/not launched/.test(String(desc.versions.chromium)), String(desc.versions.chromium));
  } finally {
    try { await d.close(); } catch (e) { /* best effort */ }
  }
  const failed = results.filter(r => !r.skipped && !r.ok);
  const skipped = results.filter(r => r.skipped);
  const caps = d.capabilities();
  const allCaps = Object.keys(caps).every(k => caps[k]);
  // Granted here and nowhere else. Zero failures, zero skips, every capability
  // present, and the Playwright driver specifically.
  if (failed.length === 0 && skipped.length === 0 && allCaps && DriverClass === PlaywrightDriver)
    CONFORMANT.add(d);
  return { results, passed: results.length - failed.length - skipped.length,
           failed: failed.length, skipped: skipped.length, driver: d,
           conformanceGranted: CONFORMANT.has(d) };
}

function selectDriver(name) {
  if (name === 'playwright') return PlaywrightDriver;
  if (name === 'jsdom') return JsdomDriver;
  throw new Error(`unknown driver "${name}" (expected playwright or jsdom)`);
}

if (require.main === module) {
  const argv = process.argv.slice(2);
  const which = argv.find(a => !a.startsWith('--')) || 'jsdom';
  const execArg = (argv.find(a => a.startsWith('--executable=')) || '').split('=')[1];
  const D = selectDriver(which);
  // A certifying run must name the browser. Defaulting to a Playwright-managed
  // download would certify a browser nobody declared.
  const execPath = execArg || (which === 'playwright' ? PINS.chromiumPath : undefined);
  if (which === 'playwright' && !execPath) {
    console.error('refusing to run: --executable=/path/to/chromium is required for a certifying driver');
    process.exit(2);
  }
  console.log(`KAR-093 STEP 9 · DRIVER v2 CONFORMANCE · ${which}`);
  console.log(`pins: node ${PINS.node}, playwright ${PINS.playwrightMinor}.x, chromium ${PINS.chromiumMajor}.x`);
  if (execPath) console.log(`executable: ${execPath}${execArg ? '' : '  (default; override with --executable=)'}`);
  console.log('');
  runDriverConformance(D, null, { executablePath: execPath }).then(r => {
    console.log('');
    const cert = r.driver.certify();
    console.log(`${r.passed} passed, ${r.failed} failed, ${r.skipped} skipped`);
    console.log('conformance granted: ' + (r.conformanceGranted ? 'YES' : 'NO'));
    if (r.skipped) console.log('  skipped cases are DECLARED INCAPACITIES, not passes; a driver missing a capability cannot certify');
    console.log('certifying: ' + (cert.certifying ? 'YES' : 'NO'));
    cert.reasons.forEach(x => console.log('  - ' + x));
    process.exit(r.failed ? 1 : 0);
  }).catch(e => { console.error('CONFORMANCE ERROR: ' + (e && e.stack || e)); process.exit(2); });
}

module.exports = { PlaywrightDriver, JsdomDriver, selectDriver, runDriverConformance, PINS, CONFORMANCE_PAGE };
