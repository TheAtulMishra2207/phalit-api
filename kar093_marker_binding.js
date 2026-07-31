#!/usr/bin/env node
'use strict';
/**
 * KAR-093 GATE v3 · MARKER BINDING VALIDATOR
 * Usage: node kar093_marker_binding.js <newphalit_fixed.html> [--driver=jsdom]
 *
 * Closure proves no UNMARKED text exists. It does not prove a MARKED element
 * shows what its marker claims. A path typo, a mirrored value, or a field
 * quietly rendering its neighbour all survive closure. This binds each marker
 * to its declared source and asserts the exact rendered form.
 *
 *   data-d1-field       -> resolved against the /d1/prepare drawer for the graha
 *   data-d1-chart-field -> resolved against the /chart planet or lagna
 *
 * A path with no declared renderer is a FINDING, not a default. Defaulting to
 * identity would let an unreviewed field pass by omission, which is the same
 * shape of hole as an unaudited exclusion list.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const C = require('./kar093_step9_contract.js');
const { selectDriver } = require('./kar093_step9_driver2.js');

const EM = '\u2014';
const RENDER = {
  'position.dignity_label':                    v => String(v),
  'rashi.sign':                                v => String(v),
  'rashi.dignity_label':                       v => v == null ? EM : String(v),
  'rashi.sign_lord.graha':                     v => String(v),
  'rashi.sign_lord.house':                     v => 'H' + v,
  'rashi.sign_lord.sign':                      v => String(v),
  'house.house':                               v => 'H' + v,
  'house.house_name':                          v => String(v),
  'house.house_lord':                          v => String(v),
  'bhavesh.bhavesh':                           v => String(v),
  'bhavesh.of_sign':                           v => String(v),
  'bhavesh.position.house':                    v => 'H' + v,
  'bhavesh.position.sign':                     v => String(v),
  'bhavesh.position.dignity_label':            v => v == null ? EM : String(v),
  'bhavesh.support':                           v => String(v),
  // CONDITIONAL. The note is only correct when the source boolean is true, so
  // the renderer declares a precondition. v1 emitted the positive sentence for
  // a false source, which meant a wrongly displayed note agreed with the gate.
  'bhavesh.retrograde_note':                   { requires: v => v === true,
                                                 render: () => 'Retrograde \u2014 inward review, delay then intensification.' },
  'bhavat_bhavam.from_house':                  v => 'H' + v,
  'bhavat_bhavam.bb_house':                    v => 'H' + v,
  'bhavat_bhavam.bb_house_name':               v => String(v),
  'bhavat_bhavam.bb_lord':                     v => String(v),
  'bhavat_bhavam.bb_lord_position.house':      v => 'H' + v,
  'bhavat_bhavam.bb_lord_position.dignity_label': v => v == null ? EM : String(v),
  'bhavat_bhavam.sustaining':                  v => String(v),
  'bhava_karaka.karakas':                      v => (v || []).join(' / ') || EM,
  'bhava_karaka.karaka_support':               v => String(v),
  'graha_saar.overall_verdict':                v => String(v),
  'graha_saar.strength_verdict':               v => String(v),
  'graha_saar.natural_nature':                 v => String(v),
  'graha_saar.functional_nature':              v => String(v),
  'graha_saar.verse_yoga_status':              v => String(v),
  'graha_saar.ownership_yogakaraka':           v => (v ? 'yes' : 'no'),
  'graha_saar.maraka_status':                  v => String(v),
  'graha_saar.functional_basis_verse':         v => v == null ? EM : String(v),
  'shadbala.at_digbala_peak_house':            { requires: v => v === true,
                                                 render: () => 'This is the house of Digbala \u2014 maximum directional strength.' }
};
// Dṛṣṭi paths are indexed, so they are matched by shape rather than listed.
const DRISHTI_RE = /^(house\.drishti|bhavesh\.drishti|graha_saar\.house_drishti)\.(net|subject|sources\.(\d+)\.(source|kind|polarity))$/;

// Declared static lookups for the drawer header. Transcribed from the page's
// own tables, so a shared transcription error would pass; that limit is stated
// rather than hidden. Everything else in the summary is chart-sourced.
const SIGN_SA = ['\u092e\u0947\u0937','\u0935\u0943\u0937','\u092e\u093f\u0925\u0941\u0928','\u0915\u0930\u094d\u0915','\u0938\u093f\u0902\u0939','\u0915\u0928\u094d\u092f\u093e','\u0924\u0941\u0932\u093e','\u0935\u0943\u0936\u094d\u091a\u093f\u0915','\u0927\u0928\u0941','\u092e\u0915\u0930','\u0915\u0941\u0902\u092d','\u092e\u0940\u0928'];
const HOUSE_NAMES = ['','Lagna','Dhana','Parakrama','Sukha','Putra','Ripu','Kalatra','Randhra','Bhagya','Karma','Labha','Vyaya'];

const CHART_RENDER = {
  'planet.sign':       (p) => String(p.sign),
  'planet.house':      (p) => 'H' + p.house,
  'planet.degree':     (p) => p.degree.toFixed(1) + '\u00b0',
  'planet.retrograde': (p) => (p.retrograde ? ' \u00b7 \u211e' : ''),
  'planet.summary':    (p) => `${p.sign} \u00b7 ${SIGN_SA[p.sign_index]} \u00b7 H${p.house} \u00b7 ${HOUSE_NAMES[p.house]} \u00b7 ${p.degree.toFixed(2)}\u00b0${p.retrograde ? ' \u00b7 \u211e Vakri' : ''}`
};

const dig = (obj, p) => p.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);

/**
 * MIRROR ROLES. The same payload path is legitimately rendered twice in one
 * drawer with different surrounding text: house.house appears as the kv-row
 * value "H1" and inside the section heading "Bhāva · H1". Rather than reopen
 * the accepted HTML to add a role attribute, the role is derived from DOM
 * position and given its own declared renderer. An undeclared role is a
 * finding, exactly like an undeclared path.
 */
const ROLE_RENDER = {
  'section-title|house.house': v => 'Bh\u0101va \u00b7 H' + v
};
const roleOf = el => (el.inSectionHead ? 'section-title' : 'primary');

function resolveD1(drawer, fieldPath, role) {
  if (role && role !== 'primary') {
    const key = role + '|' + fieldPath;
    if (!Object.prototype.hasOwnProperty.call(ROLE_RENDER, key)) return { undeclared: true, role };
    return { text: ROLE_RENDER[key](dig(drawer, fieldPath)) };
  }
  const m = DRISHTI_RE.exec(fieldPath);
  if (!m) {
    if (!Object.prototype.hasOwnProperty.call(RENDER, fieldPath)) return { undeclared: true };
    const decl = RENDER[fieldPath];
    const value = dig(drawer, fieldPath);
    if (typeof decl === 'function') return { text: decl(value) };
    if (!decl.requires(value))
      return { precondition: `source ${JSON.stringify(value)} does not satisfy the declared precondition` };
    return { text: decl.render(value) };
  }
  const blockPath = m[1] === 'graha_saar.house_drishti' ? 'graha_saar.house_drishti' : m[1];
  const block = dig(drawer, blockPath);
  if (!block) return { text: null, missing: true };
  if (m[2] === 'net') return { text: String(block.net) };
  if (m[2] === 'subject') {
    // Rendered only when the block genuinely has no sources. Matching on the
    // subject alone would accept the sentence beside a populated block.
    if ((block.sources || []).length !== 0)
      return { precondition: `subject sentence rendered while ${block.sources.length} drishti source(s) exist` };
    return { text: String(block.subject) + ' receives no external drishti.' };
  }
  const src = (block.sources || [])[Number(m[3])];
  if (!src) return { text: null, missing: true };
  return { text: String(src[m[4]]) };
}

/**
 * INTEGRATION POINT. Validates against a driver the caller already opened and
 * drove to the chart view. The orchestrator needs this so one certification
 * decision is assembled from ONE driver instance: run() below opens its own,
 * which is correct standalone and wrong inside a gate.
 * The renderer and binding tables are untouched.
 */
async function collectAndCheck(driver, chart, payload, findings, stats) {
  // Chip markers, per graha.
  const chips = await driver.evaluate(() => Array.from(document.querySelectorAll('#page-d1 .planet-chip')).map(c => ({
    graha: c.getAttribute('data-d1-graha'),
    fields: Array.from(c.querySelectorAll('[data-d1-field]')).map(e => ({ p: e.getAttribute('data-d1-field'), t: e.textContent })),
    chartFields: Array.from(c.querySelectorAll('[data-d1-chart-field]')).map(e => ({ p: e.getAttribute('data-d1-chart-field'), t: e.textContent }))
  })));
  chips.forEach(chip => {
    const drawer = payload.drawers.drawers.find(d => d.graha === chip.graha);
    chip.fields.forEach(f => {
      stats.d1++;
      const r = resolveD1(drawer, f.p);
      if (r.undeclared) { stats.undeclared++; findings.push(`chip ${chip.graha}: no declared renderer for "${f.p}"`); return; }
      if (r.precondition) { stats.mismatch++; findings.push(`chip ${chip.graha} "${f.p}": ${r.precondition}`); return; }
      if (f.t !== r.text) { stats.mismatch++; findings.push(`chip ${chip.graha} "${f.p}": rendered ${JSON.stringify(f.t)}, source gives ${JSON.stringify(r.text)}`); }
    });
    chip.chartFields.forEach(f => {
      stats.chartF++;
      const p = chart.planets[chip.graha];
      if (!CHART_RENDER[f.p]) { stats.undeclared++; findings.push(`chip ${chip.graha}: no declared chart renderer for "${f.p}"`); return; }
      const want = CHART_RENDER[f.p](p, {});
      if (f.t !== want) { stats.mismatch++; findings.push(`chip ${chip.graha} chart "${f.p}": rendered ${JSON.stringify(f.t)}, chart gives ${JSON.stringify(want)}`); }
    });
  });

  // Drawer markers, all nine.
  for (let i = 0; i < C.GRAHAS.length; i++) {
    const g = C.GRAHAS[i];
    await driver.click('#page-d1 .planet-chip', i);
    await driver.wait(450);
    const obs = await driver.evaluate(() => {
      const root = document.getElementById('drawer');
      return {
        graha: document.getElementById('drawer-body').getAttribute('data-d1-graha'),
        fields: Array.from(root.querySelectorAll('[data-d1-field]')).map(e => ({
          p: e.getAttribute('data-d1-field'), t: e.textContent,
          inSectionHead: !!e.closest('.section-head') })),
        chartFields: Array.from(root.querySelectorAll('[data-d1-chart-field]')).map(e => ({
          p: e.getAttribute('data-d1-chart-field'), t: e.textContent }))
      };
    });
    if (obs.graha !== g) { findings.push(`drawer ${i}: identity is ${obs.graha}, expected ${g}`); continue; }
    const drawer = payload.drawers.drawers.find(d => d.graha === g);
    obs.fields.forEach(f => {
      stats.d1++;
      const r = resolveD1(drawer, f.p, roleOf(f));
      if (r.undeclared) { stats.undeclared++; findings.push(`${g} drawer: no declared renderer for "${f.p}" in role "${r.role || 'primary'}"`); return; }
      if (r.missing) { stats.mismatch++; findings.push(`${g} drawer "${f.p}": marked but absent from payload`); return; }
      if (r.precondition) { stats.mismatch++; findings.push(`${g} drawer "${f.p}": ${r.precondition}`); return; }
      if (f.t !== r.text) { stats.mismatch++; findings.push(`${g} drawer "${f.p}" [${roleOf(f)}]: rendered ${JSON.stringify(f.t)}, source gives ${JSON.stringify(r.text)}`); }
    });
    obs.chartFields.forEach(f => {
      stats.chartF++;
      if (!CHART_RENDER[f.p]) { stats.undeclared++; findings.push(`${g} drawer: no declared chart renderer for "${f.p}"`); return; }
      const want = CHART_RENDER[f.p](chart.planets[g]);
      if (f.t !== want) { stats.mismatch++; findings.push(`${g} drawer chart "${f.p}": rendered ${JSON.stringify(f.t)}, chart gives ${JSON.stringify(want)}`); }
    });
    await driver.evaluate(() => { closeDrawer(); return 1; });
    await driver.wait(120);
  }

}

async function validateWithDriver(driver, chart, payload) {
  const findings = [];
  const stats = { d1: 0, chartF: 0, undeclared: 0, mismatch: 0 };
  await collectAndCheck(driver, chart, payload, findings, stats);
  return { findings, stats };
}

async function run(htmlPath, driverName, opts) {
  opts = opts || {};
  const source = fs.readFileSync(htmlPath, 'utf8');
  const useP6 = process.env.KAR093_P6 !== '0';
  const chart = useP6 ? C.buildChartResponseP6() : C.buildChartResponse();
  let payload = useP6 ? C.buildD1PayloadP6() : C.buildD1Payload();
  if (typeof opts.mutatePayload === 'function') payload = opts.mutatePayload(payload) || payload;
  const routes = [
    { match: u => u.includes('nominatim'),
      body: async () => [{ lat: '25.2139', lon: '84.9896', display_name: 'Jehanabad' }] },
    { match: u => u.includes('/d1/prepare'), body: async () => payload },
    { match: u => u.includes('/chart'), body: async () => chart }
  ];
  const D = selectDriver(driverName || 'jsdom');
  const driver = new D();
  const findings = [];
  const stats = { d1: 0, chartF: 0, undeclared: 0, mismatch: 0 };

  await driver.open(source, { routes });
  await driver.evaluate(() => {
    document.getElementById('inp-date').value = '1990-01-01';
    document.getElementById('inp-time').value = '12:00';
    document.getElementById('inp-utc').value = '5.5';
    searchPlace('Jehanabad'); return 1;
  });
  await driver.wait(1000);
  await driver.click('#place-results .place-result', 0);
  await driver.wait(150);
  await driver.click('#cast-btn', 0);
  await driver.wait(2200);
  // renderChartView() slides to the report hub, leaving #page-d1 off-screen.
  // jsdom has no layout so the clicks landed anyway; a real browser refuses
  // them. Navigate D1 into view before any chip interaction.
  await driver.evaluate(() => { slideTo(0); return 1; });
  await driver.wait(500);

  await collectAndCheck(driver, chart, payload, findings, stats);
  await driver.close();
  return { findings, stats };
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const file = args.find(a => !a.startsWith('--'));
  const drv = (args.find(a => a.startsWith('--driver=')) || '--driver=jsdom').split('=')[1];
  if (!file) { console.error('usage: node kar093_marker_binding.js <html> [--driver=...]'); process.exit(2); }

  // BRANCH COVERAGE. The base fixture leaves every conditional false, so the
  // retrograde note, the Digbala note and the no-drishti sentence are never
  // rendered. Each variant activates one branch. A validator that only ever
  // sees the false side proves nothing about the true side.
  const VARIANTS = [
    { name: 'base (all conditionals false)', mutate: null },
    { name: 'retrograde note active',
      mutate: p => { p.drawers.drawers.forEach(d => { d.bhavesh.retrograde_note = true; }); return p; } },
    { name: 'digbala note active',
      mutate: p => { p.drawers.drawers.forEach(d => { d.shadbala.at_digbala_peak_house = true; }); return p; } },
    { name: 'no external drishti',
      mutate: p => { p.drawers.drawers.forEach(d => {
        [d.house.drishti, d.bhavesh.drishti, d.graha_saar.house_drishti].forEach(b => { b.sources = []; }); }); return p; } }
  ];

  (async () => {
    const buf = fs.readFileSync(file);
    let nl = 0; for (const b of buf) if (b === 10) nl++;
    console.log('KAR-093 GATE v3 · MARKER BINDING VALIDATOR');
    console.log('subject : ' + path.resolve(file));
    console.log('sha256  : ' + crypto.createHash('sha256').update(buf).digest('hex'));
    console.log('newlines: ' + nl);
    console.log('driver  : ' + drv + (drv === 'jsdom' ? '  (DEVELOPMENT ONLY, CANNOT CERTIFY)' : ''));
    console.log('');
    let total = 0;
    for (const v of VARIANTS) {
      const r = await run(file, drv, { mutatePayload: v.mutate });
      total += r.findings.length;
      console.log(`[${r.findings.length ? 'FAIL' : ' ok '}] ${v.name.padEnd(32)} ` +
                  `bound ${String(r.stats.d1).padStart(4)} field / ${String(r.stats.chartF).padStart(3)} chart-field · ` +
                  `undeclared ${r.stats.undeclared} · mismatch ${r.stats.mismatch}`);
      r.findings.slice(0, 8).forEach(f => console.log('        - ' + f));
      if (r.findings.length > 8) console.log(`        … ${r.findings.length - 8} more`);
    }
    console.log('');
    console.log(total ? `RESULT: ${total} finding(s) across ${VARIANTS.length} branch variants.`
                      : `RESULT: every marker resolves to its declared source, across ${VARIANTS.length} branch variants.`);
    process.exit(total ? 1 : 0);
  })().catch(e => { console.error('VALIDATOR ERROR: ' + (e && e.stack || e)); process.exit(2); });
}

module.exports = { run, validateWithDriver, collectAndCheck, RENDER, CHART_RENDER, DRISHTI_RE };
