#!/usr/bin/env node
'use strict';
/**
 * KAR-093 · GATE v3 ORCHESTRATOR
 * Usage:
 *   node kar093_gate3.js <newphalit_fixed.html> --driver=playwright --executable=/usr/bin/chromium
 *   node kar093_gate3.js <newphalit_fixed.html> --driver=jsdom          # dev only
 *
 * SCOPE (founder ruling): D1 page and drawer cutover scope. The chips on
 * #page-d1, all nine D1 drawers, and the loading, success and error states.
 * NOT Pratiphala, NOT downstream reports. Backlog findings are reported and do
 * NOT affect the exit code.
 *
 * SIX PHASES. Each is declared in REQUIRED_PHASES and must record a real pass:
 *   P1 conformance  the driver proves it can observe what the gate assumes
 *   P2 closure      no unmarked non-empty text leaf in any reviewed root
 *   P3 binding      every marker resolves to its declared source and exact form
 *   P4 corpus       the rendered branch is the one the payload ref selected
 *   P5 adversarial  seven known false-passes are each caught
 *   P6 provenance   the payload under test is regenerated from the accepted
 *                   models DURING this run, not attested by the artifact
 *
 * CERTIFICATION IS EARNED, NEVER ASSERTED. The run is certifying only when the
 * driver's own certify() says so, which requires conformance granted in this
 * process plus exact pin matches plus a declared executable.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const P6 = require('./kar093_p6_bind.js');
const { canonicalSha, runP6Verifier, judgeP6 } = P6;   // ACCEPTED_P6 stays in the bind module; an unused import here is the same defect class as v1's unused D1_SURFACES
const C = require('./kar093_step9_contract.js');
const DRV = require('./kar093_step9_driver2.js');
const BIND = require('./kar093_marker_binding.js');
const ADV = require('./kar093_adversarial.js');

const SCOPE = 'D1 page and drawer cutover scope';

/**
 * REQUIRED PHASES. Certification fails closed until every one is present AND
 * passing. Two are declared and not yet built, so no run can certify today.
 * v1 gated only on driver.certify() and zero findings, which let a run report
 * CERTIFYING: YES while acknowledged prerequisites were still missing.
 */
const REQUIRED_PHASES = [
  { id: 'P1', name: 'driver conformance',        present: true },
  { id: 'P2', name: 'marker closure',            present: true },
  { id: 'P3', name: 'marker binding',            present: true },
  { id: 'P4', name: 'corpus provenance',         present: true },
  { id: 'P5', name: 'adversarial fixture suite', present: true },
  { id: 'P6', name: 'model-generated fixture',   present: true }
];

/**
 * renderChartView() slides the application to the report hub, so #page-d1 sits
 * off-screen. jsdom has no layout and dispatched the clicks regardless; a real
 * browser refuses them. Every cast and recast must be followed by this.
 */
async function gotoD1(driver) {
  await driver.evaluate(() => { slideTo(0); return 1; });
  await driver.wait(500);
}

/**
 * After the first cast the input surface is display:none, so #cast-btn is not
 * clickable. Recast through the page's own function instead of a hidden
 * control, then bring D1 back into view.
 */
async function recast(driver) {
  await driver.evaluate(() => { castChart(); return 1; });
  await driver.wait(2200);
  await gotoD1(driver);
}

// Markers that authorise text. data-d1-state is deliberately NOT among them:
// state records which state the drawer is in, it is not permission for text.
const TEXT_MARKERS = ['data-d1-field', 'data-d1-chart-field', 'data-d1-literal',
                      'data-d1-error-field', 'data-d1-corpus-state'];

// Static legend selectors excluded from closure, printed on every run so the
// exclusion is auditable rather than silent.
const CLOSURE_EXCLUSIONS = [];

function probeClosure(markers, exclusions) {
  return function (args) {
    const M = args.markers, EX = args.exclusions;
    const roots = { chips: document.getElementById('planet-list'), drawer: document.getElementById('drawer') };
    const out = {};
    Object.keys(roots).forEach(function (k) {
      const root = roots[k];
      if (!root) { out[k] = { missing: true }; return; }
      const unmarked = [], sheltered = [];
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        const t = (n.textContent || '').trim();
        if (!t) continue;
        let e = n.parentElement, ok = false;
        while (e && e !== root.parentElement) {
          if (EX.some(function (x) { return e.matches && e.matches(x); })) { ok = true; break; }
          for (let i = 0; i < M.length; i++) if (e.hasAttribute(M[i])) { ok = true; break; }
          if (ok) break;
          e = e.parentElement;
        }
        if (!ok) unmarked.push(n.parentElement.tagName + '.' + n.parentElement.className + '::' + t.slice(0, 40));
      }
      // A literal-marked ancestor must not shelter a dynamic descendant.
      Array.prototype.forEach.call(root.querySelectorAll('[data-d1-literal]'), function (el) {
        if (el.querySelector('[data-d1-field],[data-d1-chart-field]'))
          sheltered.push(el.getAttribute('data-d1-literal') + ' :: ' + (el.textContent || '').trim().slice(0, 40));
      });
      out[k] = {
        unmarked: unmarked, sheltered: sheltered,
        composite: root.querySelectorAll('[data-d1-literal="composite"]').length,
        d1Fields: root.querySelectorAll('[data-d1-field]').length,
        chartFields: root.querySelectorAll('[data-d1-chart-field]').length
      };
    });
    return out;
  };
}

function probeCorpus() {
  const root = document.getElementById('drawer-body');
  return Array.prototype.map.call(root.querySelectorAll('[data-d1-corpus-state]'), function (el) {
    return {
      corpus: el.getAttribute('data-d1-corpus'),
      graha: el.getAttribute('data-d1-corpus-graha'),
      key: el.getAttribute('data-d1-corpus-key'),
      state: el.getAttribute('data-d1-corpus-state'),
      text: (el.textContent || '')
    };
  });
}

/**
 * Corpus provenance. The prose lives in the page and cannot carry a sentinel,
 * so the proof is comparative: the rendered text must equal the branch the
 * payload ref names, AND must differ from the branch the legacy client score
 * would have chosen. The legacy branch is computed with the page's own scoring
 * function on purpose — it is the engine being proved not to be in charge.
 */
function corpusOracle() {
  return function (args) {
    const refs = args.refs;
    return refs.map(function (r) {
      let declared = '';
      try {
        if (r.corpus === 'RASHI_CORPUS') declared = (D1_RASHI_CORPUS[r.graha] || {})[r.key] || '';
        else if (r.corpus === 'HOUSE_CORPUS') declared = (HOUSE_CORPUS[r.graha] || {})[r.key] || '';
        else if (r.corpus === 'BHAVAT_DESC') declared = BHAVAT_DESC[r.key] || '';
        else if (r.corpus === 'BHAVA_KARAKA') declared = (BHAVA_KARAKA[r.key] || {}).text || '';
      } catch (e) { declared = '(oracle error) ' + e.message; }
      let legacy = '';
      try {
        if (r.corpus === 'RASHI_CORPUS' && r.graha && chartData && chartData.planets[r.graha]) {
          const sc = getScore(r.graha, chartData.planets[r.graha].sign_index);
          const tier = String(sc);
          legacy = (RASHI_CORPUS[r.graha] || {})[tier] || '';
        }
      } catch (e) { legacy = ''; }
      return { declared: declared, legacy: legacy };
    });
  };
}

async function runGate3(htmlPath, opts) {
  opts = opts || {};
  const source = opts.source != null ? opts.source : fs.readFileSync(htmlPath, 'utf8');
  const DriverClass = DRV.selectDriver(opts.driver || 'jsdom');
  const findings = [];
  const notes = [];
  // Phase outcomes, recorded from real results. Certification reads THESE, not
  // the `present` flags: a declared phase that runs and fails must still block.
  const phaseResults = {};
  const add = (id, sev, scope, title, detail, ev) =>
    findings.push({ id, severity: sev, scope, title, detail, evidence: ev || [] });

  // ── PHASE 1 · driver conformance, in this process ────────────────────────
  const conf = await DRV.runDriverConformance(DriverClass, () => {}, { executablePath: opts.executablePath });
  phaseResults.P1 = conf.failed === 0 && conf.conformanceGranted;
  notes.push(`P1 conformance: ${conf.passed} passed, ${conf.failed} failed, ${conf.skipped} skipped; granted=${conf.conformanceGranted}`);
  if (conf.failed) {
    add('P1', 'BLOCKER', 'in', 'Driver conformance failed',
        'The gate will not report on a driver that cannot observe what it assumes.',
        conf.results.filter(r => !r.skipped && !r.ok).map(r => r.name + (r.detail ? ' — ' + r.detail : '')));
    return { findings, notes, aborted: true, certifying: false, scope: SCOPE };
  }

  // ── PHASE 6 · the payload IS model-generated, demonstrated in this run ───
  // Runs BEFORE the payload is bound, because its result decides whether there
  // is a trustworthy payload to test with at all. The old P6 ran last and read
  // `_evidence` out of the artifact it was certifying (QA blocker P6-001).
  const useP6 = process.env.KAR093_P6 !== '0';
  let p6run = { ran: false, error: 'running the hand-authored fixture (KAR093_P6=0)' };
  if (useP6) {
    p6run = runP6Verifier({ htmlPath, python: opts.python, p6Dir: opts.p6Dir, p6Out: opts.p6Out });
    if (!p6run.ran) {
      // Fail closed. No generated payload means nothing to compare against, so
      // the browser phases would be exercising an unverified artifact.
      phaseResults.P6 = false;
      add('P6', 'BLOCKER', 'in', 'The P6 verifier did not run',
          'P6 is derived by executing the accepted generator during the gate run. ' +
          'It never falls back to a fixture on disk.', [p6run.error]);
      notes.push('P6 verifier: DID NOT RUN — ' + p6run.error);
      return { findings, notes, aborted: true, certifying: false, scope: SCOPE, phaseResults };
    }
  }

  const chart = useP6 ? C.buildChartResponseP6() : C.buildChartResponse();
  const payload = useP6 ? C.buildD1PayloadP6() : C.buildD1Payload();

  const p6verdict = judgeP6(p6run, (useP6 && C.loadP6) ? C.loadP6() : null);
  phaseResults.P6 = p6verdict.pass;
  {
    const o = p6run.observed || {}, g = o.generated || {};
    notes.push('P6 fixture: ' + (p6verdict.pass ? 'model-generated, DEMONSTRATED by execution' : 'REJECTED') +
      (p6run.ran ? ` (python ${(o.runtime || {}).python} pydantic ${(o.runtime || {}).pydantic}, ` +
        `${g.edge_count} edges, ${Object.keys(o.modules || {}).length} modules, ` +
        `fixture ${String(g.fixture_sha256 || '').slice(0, 12)}, ` +
        `product ${String((o.product || {}).sha256 || '').slice(0, 12)})` : ''));
    // Recorded for QA: the digest of the object actually served on /d1/prepare.
    notes.push('P6 served payload digest: ' + canonicalSha(payload).slice(0, 16) +
               '  (generated drawers ' + canonicalSha(p6run.generated ? p6run.generated.drawers : null).slice(0, 16) + ')');
  }
  if (!p6verdict.pass)
    add('P6', 'BLOCKER', 'in', 'The payload under test is not a verified model-generated artifact',
        'Accepted values are held by the gate and compared against facts derived by executing the generator.',
        p6verdict.problems);
  let d1Fail = false;
  let hold = null;   // when set, /d1/prepare awaits it before responding
  const routes = [
    { match: u => u.includes('nominatim'),
      body: async () => [{ lat: '25.2139', lon: '84.9896', display_name: 'Jehanabad' }] },
    { match: u => u.includes('/d1/prepare'),
      get ok() { return !d1Fail; }, get status() { return d1Fail ? 502 : 200; },
      body: async () => { if (hold) await hold; return d1Fail ? { detail: 'Reference: ZQXERRQ7' } : payload; } },
    { match: u => u.includes('/chart'), body: async () => chart }
  ];

  // THE CONFORMANCE-GRANTED INSTANCE, reused. v1 created a fresh driver here and
  // called certify() on it before launch, so the WeakSet membership earned in P1
  // was discarded and the run could never certify. Same defect class as the
  // driver's own missing grant, one layer up: the mechanism was correct and the
  // construction defeated it.
  const driver = conf.driver;
  let cert;
  try {
    try { await driver.close(); } catch (e) { /* conformance browser */ }
    await driver.open(source, { routes });
    cert = driver.certify();   // AFTER launch, so runtime metadata is real
    await driver.evaluate(() => {
      document.getElementById('inp-date').value = '1990-01-01';
      document.getElementById('inp-time').value = '12:00';
      document.getElementById('inp-utc').value = '5.5';
      searchPlace('Jehanabad'); return 1;
    });
    await driver.wait(1000);
    await driver.click('#place-results .place-result', 0);
    await driver.wait(150);
    await driver.click('#cast-btn', 0);   // visible only for the FIRST cast
    await driver.wait(2200);
    await gotoD1(driver);

    // ── PHASE 2 · closure, chips seeded ───────────────────────────────────
    const closeArgs = { markers: TEXT_MARKERS, exclusions: CLOSURE_EXCLUSIONS };
    const c1 = await driver.evaluate(probeClosure(), closeArgs);
    ['chips'].forEach(k => {
      if (c1[k].unmarked.length) add('P2', 'BLOCKER', 'in', `Unmarked text in ${k}`,
        'Every non-empty text leaf must be payload-bound or an approved literal.', c1[k].unmarked);
      if (c1[k].sheltered.length) add('P2B', 'BLOCKER', 'in', `Literal ancestor shelters dynamic content in ${k}`,
        'A literal marker must not sit above a payload-bound descendant.', c1[k].sheltered);
      if (c1[k].composite) add('P2C', 'BLOCKER', 'in', `Composite ancestor waiver present in ${k}`,
        'data-d1-literal="composite" was removed in product fix v5.', [String(c1[k].composite)]);
    });
    notes.push(`P2 chips: ${c1.chips.d1Fields} field, ${c1.chips.chartFields} chart-field, ${c1.chips.unmarked.length} unmarked`);
    phaseResults.P2 = true;   // revoked below by any P2* finding

    // ── PHASE 3 · marker binding, on THIS driver ──────────────────────────
    // v1 delegated to BIND.run(), which opened its own browser through the
    // SUPERSEDED driver (goto + force clicks). One certification decision was
    // being assembled from two driver implementations, and P1 gated neither.
    await gotoD1(driver);
    const bindRes = await BIND.validateWithDriver(driver, chart, payload);
    notes.push(`P3 binding: ${bindRes.stats.d1} field, ${bindRes.stats.chartF} chart-field, ` +
               `${bindRes.stats.undeclared} undeclared, ${bindRes.stats.mismatch} mismatch`);
    bindRes.findings.forEach(f => add('P3', 'BLOCKER', 'in', 'Marker binding failure', '', [f]));
    phaseResults.P3 = bindRes.findings.length === 0;

    // ── PHASE 4 · per drawer: closure, corpus provenance ──────────────────
    let corpusChecked = 0, unresolvableChecked = 0;
    await gotoD1(driver);
    for (let i = 0; i < C.GRAHAS.length; i++) {
      const g = C.GRAHAS[i];
      await driver.click('#page-d1 .planet-chip', i);
      await driver.wait(450);
      const cd = await driver.evaluate(probeClosure(), closeArgs);
      if (cd.drawer.unmarked.length)
        add('P2', 'BLOCKER', 'in', `Unmarked text in the ${g} drawer`, 'Closure is not satisfied.', cd.drawer.unmarked);
      if (cd.drawer.sheltered.length)
        add('P2B', 'BLOCKER', 'in', `Literal ancestor shelters dynamic content in the ${g} drawer`, '', cd.drawer.sheltered);

      const refs = await driver.evaluate(probeCorpus);
      const oracle = await driver.evaluate(corpusOracle(), { refs });
      refs.forEach((r, k) => {
        const o = oracle[k];
        if (r.state === 'unresolvable') {
          unresolvableChecked++;
          if (r.text.trim() !== '')
            add('P4', 'BLOCKER', 'in', `${g}: unresolvable corpus ref rendered prose`,
                'An unresolvable reference must render nothing, not a locally chosen branch.',
                [`${r.corpus}/${r.graha}/${r.key} rendered ${JSON.stringify(r.text.slice(0, 60))}`]);
          return;
        }
        corpusChecked++;
        const want = String(o.declared || '').replace(/\{sign\}/g, C.S[g] ? C.S[g].SIGN : '');
        if (r.text.trim() !== want.trim())
          add('P4', 'BLOCKER', 'in', `${g}: corpus text is not the branch the payload selected`,
              'The rendered prose must be the branch corpus_ref names.',
              [`${r.corpus}/${r.graha}/${r.key}`,
               `rendered: ${JSON.stringify(r.text.slice(0, 70))}`,
               `declared branch: ${JSON.stringify(want.slice(0, 70))}`]);
        else if (o.legacy && o.legacy.trim() === r.text.trim())
          add('P4B', 'BLOCKER', 'in', `${g}: corpus branch is indistinguishable from the legacy score branch`,
              'The payload ref must select a branch the client score would not have chosen, or provenance is unproven.',
              [`${r.corpus}/${r.graha}/${r.key}`]);
      });
      await driver.evaluate(() => { closeDrawer(); return 1; });
      await driver.wait(120);
    }
    phaseResults.P4 = !findings.some(f => f.id === 'P4' || f.id === 'P4B');
    notes.push(`P4 corpus: ${corpusChecked} resolved branch(es) matched, ${unresolvableChecked} unresolvable ref(s) rendered empty`);

    // ── PHASE 2 · LOADING state, genuinely pending ────────────────────────
    // Scope claims loading, success and error. v1 checked seeded chips, success
    // drawers and the error drawer, and never held a request open. This holds
    // one cache-miss response unresolved and inspects the drawer while it is
    // actually loading.
    let release = null;
    hold = new Promise(res => { release = res; });
    await recast(driver);                     // clears the payload cache
    await driver.click('#page-d1 .planet-chip', 0);
    await driver.wait(450);
    const cl = await driver.evaluate(probeClosure(), closeArgs);
    const loadState = await driver.evaluate(() =>
      document.getElementById('drawer-body').getAttribute('data-d1-state'));
    if (loadState !== 'loading')
      add('P2L', 'BLOCKER', 'in', 'Loading probe did not observe the loading state',
          'The probe must inspect the drawer while the request is genuinely pending.',
          [`observed data-d1-state=${JSON.stringify(loadState)}`]);
    if (cl.drawer.unmarked.length)
      add('P2L', 'BLOCKER', 'in', 'Unmarked text in the loading state', '', cl.drawer.unmarked);
    if (cl.drawer.d1Fields)
      add('P2L', 'BLOCKER', 'in', 'Loading state carries data-d1-field elements',
          'Loading text is not payload-bound.', [String(cl.drawer.d1Fields)]);
    notes.push(`P2 loading state (request held): state=${loadState}, ` +
               `${cl.drawer.d1Fields} field, ${cl.drawer.chartFields} chart-field, ${cl.drawer.unmarked.length} unmarked`);
    release(); hold = null;
    await driver.wait(700);

    // ── error state closure ───────────────────────────────────────────────
    d1Fail = true;
    await recast(driver);
    await driver.click('#page-d1 .planet-chip', 0);
    await driver.wait(700);
    const ce = await driver.evaluate(probeClosure(), closeArgs);
    if (ce.drawer.unmarked.length)
      add('P2', 'BLOCKER', 'in', 'Unmarked text in the error state', '', ce.drawer.unmarked);
    if (ce.drawer.d1Fields)
      add('P2D', 'BLOCKER', 'in', 'Error state carries data-d1-field elements',
          'The authorised contract requires none.', [String(ce.drawer.d1Fields)]);
    notes.push(`P2 error state: ${ce.drawer.d1Fields} field, ${ce.drawer.chartFields} chart-field, ${ce.drawer.unmarked.length} unmarked`);

    // ── PHASE 5 · adversarial fixture suite ───────────────────────────────
    // Reset the route state first. The error probe leaves d1Fail set, and P5
    // was running every mutant against a 502, so the corpus mutants had no
    // drawer to corrupt and silently reported "not caught".
    d1Fail = false; hold = null;
    // Runs last because each mutant reopens the page. Its result is recorded
    // and fed to certification; the phase flag alone never satisfies P5.
    // P6 already ran, before the payload was bound. See runP6Verifier/judgeP6.

    const adv = await ADV.runAdversarialSuite(driver, source, chart, payload, routes, gotoD1);
    phaseResults.P5 = adv.passed;
    notes.push(`P5 adversarial: ${adv.caught}/${adv.total} mutants caught`);
    if (!adv.passed)
      add('P5', 'BLOCKER', 'in', 'The gate failed to catch a known false-pass',
          'Every mutant here is a defect that reached QA on this ticket.',
          adv.results.filter(r => !r.caught).map(r => `${r.id} [${r.check || 'n/a'}] ${r.name}: ${(r.evidence || []).join('; ')}`));

    const errs = await driver.errors();
    if (errs.length) add('P5', 'HIGH', 'in', 'Page runtime errors during the run', 'Recorded, not swallowed.',
                         errs.slice(0, 6).map(e => e.message));

    cert = driver.certify();   // recomputed at the end of the run
  } finally {
    try { await driver.close(); } catch (e) { /* best effort */ }
  }

  if (findings.some(f => String(f.id).startsWith('P2'))) phaseResults.P2 = false;
  const inScope = findings.filter(f => f.scope === 'in');
  const reasons = (cert.reasons || []).slice();
  const missing = REQUIRED_PHASES.filter(p => !p.present);
  missing.forEach(p => reasons.push(`required phase ${p.id} (${p.name}) is not implemented`));
  // A phase that is present but recorded no PASS is treated as not satisfied.
  const unproven = REQUIRED_PHASES.filter(p => p.present && phaseResults[p.id] !== true);
  unproven.forEach(p => reasons.push(`required phase ${p.id} (${p.name}) did not record a pass`));
  if (inScope.length) reasons.push(`${inScope.length} in-scope finding(s)`);
  return { findings, notes, aborted: false, scope: SCOPE, phaseResults,
           certifying: cert.certifying && inScope.length === 0 && missing.length === 0 && unproven.length === 0,
           certReasons: reasons, requiredPhases: REQUIRED_PHASES,
           driver: driver.describe ? driver.describe() : {} };
}

if (require.main === module) {
  const argv = process.argv.slice(2);
  const file = argv.find(a => !a.startsWith('--'));
  const driver = (argv.find(a => a.startsWith('--driver=')) || '--driver=jsdom').split('=')[1];
  const execPath = (argv.find(a => a.startsWith('--executable=')) || '').split('=')[1];
  // P6 runs a Python subprocess. --python lets QA point at the pinned venv
  // without editing anything; the gate still refuses any pydantic but 1.10.13.
  const python = (argv.find(a => a.startsWith('--python=')) || '').split('=')[1];
  const p6Dir = (argv.find(a => a.startsWith('--p6dir=')) || '').split('=')[1];
  if (!file) { console.error('usage: node kar093_gate3.js <html> --driver=playwright --executable=/usr/bin/chromium [--python=/path/to/python] [--p6dir=<dir with d1_*.py>]'); process.exit(2); }

  runGate3(file, { driver, executablePath: execPath, python, p6Dir }).then(r => {
    const buf = fs.readFileSync(file);
    let nl = 0; for (const b of buf) if (b === 10) nl++;
    console.log('KAR-093 · GATE v3');
    console.log('scope     : ' + SCOPE);
    console.log('subject   : ' + path.resolve(file));
    console.log('sha256    : ' + crypto.createHash('sha256').update(buf).digest('hex'));
    console.log('newlines  : ' + nl);
    console.log('driver    : ' + driver + (execPath ? '  executable=' + execPath : ''));
    console.log('exclusions: ' + (CLOSURE_EXCLUSIONS.length ? CLOSURE_EXCLUSIONS.join(', ') : '(none)'));
    console.log('phases    : ' + REQUIRED_PHASES.map(p =>
      p.id + (!p.present ? '\u2717(absent)' : (r.phaseResults && r.phaseResults[p.id] === true ? '\u2713' : '\u2717'))).join(' '));
    console.log('');
    r.notes.forEach(n => console.log('  ' + n));
    console.log('');
    console.log('CERTIFYING: ' + (r.certifying ? 'YES' : 'NO'));
    (r.certReasons || []).forEach(x => console.log('  - ' + x));
    const inScope = r.findings.filter(f => f.scope === 'in');
    console.log('');
    if (r.aborted) console.log('RESULT: ABORTED.');
    else if (!inScope.length) console.log(`RESULT: in-scope gate passes (${SCOPE}).`);
    else console.log(`RESULT: ${inScope.length} in-scope finding(s).`);
    inScope.slice(0, 12).forEach(f => {
      console.log('');
      console.log(`  [${f.id}] ${f.severity} · ${f.title}`);
      f.evidence.slice(0, 6).forEach(e => console.log('        - ' + e));
    });
    process.exit(inScope.length ? 1 : 0);
  }).catch(e => { console.error('GATE ERROR: ' + (e && e.stack || e)); process.exit(2); });
}

module.exports = { runGate3, SCOPE, TEXT_MARKERS, P6 };
