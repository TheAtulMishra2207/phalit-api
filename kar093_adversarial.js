'use strict';
/**
 * KAR-093 · GATE v3 · PHASE 5 · ADVERSARIAL FIXTURE SUITE
 *
 * Every mutant here is a false-pass that actually happened on this ticket. The
 * suite asserts the gate CATCHES each one. A gate that only ever sees a correct
 * subject proves nothing, and each of these was found by QA rather than by me,
 * which is precisely why they are now permanent.
 *
 * P5 passes only when every mutant is caught. Its result feeds certification
 * directly; the phase is never marked present by a flag.
 *
 * Each mutation is EXACT-ONCE and throws otherwise, so a mutant cannot silently
 * stop mutating and turn into a second copy of the clean subject.
 */

const C = require('./kar093_step9_contract.js');
const BIND = require('./kar093_marker_binding.js');

function mutate(src, from, to, label, scope) {
  // `scope`, when given, narrows the search to the region between the previous
  // and next occurrences of a marker unique to the intended surface. The D9
  // cutover introduced legitimate duplicates of several D1 anchors, and a
  // mutant that could match either surface might mutate the wrong one.
  if (scope) {
    const at = src.search(scope);
    if (at < 0) throw new Error(`mutant "${label}": scope marker ${scope} not found`);
    const start = src.lastIndexOf('parts.push(', at);
    const region = src.slice(start, at);
    const n = region.split(from).length - 1;
    if (n !== 1) throw new Error(`mutant "${label}": anchor matched ${n} times in scope, expected exactly 1`);
    return src.slice(0, start) + region.replace(from, to) + src.slice(at);
  }
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error(`mutant "${label}": anchor matched ${n} times, expected exactly 1`);
  return src.replace(from, to);
}

/**
 * Each entry: a source transform, and the check that must fire.
 * `check` is one of: closure | binding | corpus.
 */
const MUTANTS = [
  {
    id: 'M1', check: 'closure',
    name: 'extra locally computed node inside a chip',
    why: 'QA v2 probe: an unaccounted value-bearing node beside correct markers',
    apply: s => mutate(s,
      '<div class="chip-sub"><span data-d1-chart-field="planet.sign">',
      '<div class="chip-extra-local">WAXING_LOCAL</div><div class="chip-sub"><span data-d1-chart-field="planet.sign">',
      'M1')
  },
  {
    id: 'M2', check: 'closure',
    name: 'local interpretive class on the chip root',
    why: 'QA v2 probe: dig-* moved onto an element the badge check does not cover',
    apply: s => mutate(s,
      // D1-unique: the D9 chip follows this line with data-d1-varga, the D1 one
      // with style.setProperty. Anchoring on the pair keeps the mutant on D1.
      "    chip.setAttribute('data-d1-graha', pn);\n    chip.style.setProperty('--chip-color', color);",
      "    chip.setAttribute('data-d1-graha', pn);\n    if (pn === 'Sun') chip.classList.add('dig-exalted');\n    chip.style.setProperty('--chip-color', color);",
      'M2')
  },
  {
    id: 'M3', check: 'binding',
    name: 'text grafted INSIDE an authorised marker',
    why: 'QA v3 probe: no new node, no new class, text added within the marked leaf',
    // v1 inserted a SIBLING before the marked span, which is a different defect
    // (an unmarked leaf) and not the one M3 claims. The text now lands inside
    // the element carrying data-d1-chart-field="planet.degree", where closure
    // cannot see it and only binding can.
    expect: /planet\.degree/,
    apply: s => mutate(s,
      'data-d1-chart-field="planet.degree">${p.degree.toFixed(1)}\u00b0</span>',
      'data-d1-chart-field="planet.degree">${p.degree.toFixed(1)}\u00b0 WAXING_LOCAL</span>',
      'M3')
  },
  {
    id: 'M4', check: 'binding',
    name: 'marker repointed at a neighbouring field',
    why: 'a path typo or a mirrored value that closure cannot see',
    apply: s => mutate(s,
      // The Strength row is textually identical in both renderers. ${roleRows}
      // exists ONLY in the D1 Graha Sara section, so anchoring through to it
      // pins the mutant to D1. The D9 section has no lordship rows by ruling.
      'data-d1-field="graha_saar.strength_verdict"',
      'data-d1-field="graha_saar.overall_verdict"',
      'M4', /\$\{roleRows\}/)
  },
  {
    id: 'M5', check: 'binding',
    name: 'conditional note rendered while its source is false',
    why: 'QA v3 finding: the positive note emitted regardless of the boolean',
    apply: s => mutate(s,
      "${bh.retrograde_note ? '<p class=\"dim\" data-d1-field=\"bhavesh.retrograde_note\">",
      "${true ? '<p class=\"dim\" data-d1-field=\"bhavesh.retrograde_note\">",
      'M5')
  },
  {
    id: 'M6', check: 'corpus',
    name: 'corpus branch chosen by the local score',
    why: 'the KAR-093 defect itself, restored in the one place closure cannot reach',
    apply: s => mutate(s,
      "  if (ref.corpus === 'RASHI_CORPUS')       text = (D1_RASHI_CORPUS[ref.graha] || {})[ref.key] || '';",
      "  if (ref.corpus === 'RASHI_CORPUS')       text = (RASHI_CORPUS[ref.graha] || {})[String(getScore(ref.graha, (chartData&&chartData.planets[ref.graha]||{}).sign_index))] || '';",
      'M6')
  },
  {
    id: 'M7', check: 'corpus',
    name: 'unresolvable reference renders prose anyway',
    why: 'the node branch must render nothing, not a locally chosen fallback',
    // v1 only disabled the outer guard, so d1Corpus's own guard still returned
    // '' and the mutant never produced the fallback text it claimed to model.
    // The unresolvable branch now emits prose directly while keeping its
    // state="unresolvable", which is exactly the contract violation.
    expect: /unresolvable/,
    // The primary model-generated fixture has no unresolvable ref, because the
    // nodes carry a certified dignity. The declared variant (nodes without
    // dignity) is the model state where that branch exists, so M7 runs there.
    variant: 'node_without_dignity',
    apply: s => mutate(s,
      "data-d1-corpus-state=\"unresolvable\"></p>';",
      "data-d1-corpus-state=\"unresolvable\">' + d1Esc((D1_RASHI_CORPUS[ref.graha] || {})[ref.key] || 'LOCAL_FALLBACK_PROSE') + '</p>';",
      'M7')
  }
];

/** Drives one mutant and returns whether the expected check caught it. */
async function runMutant(driver, m, source, chart, payload, routes, gotoD1) {
  // A mutant may declare a payload variant. Routes close over the payload the
  // caller passed, so the variant is swapped in place for this run only.
  // Swapped IN PLACE: the route closures hold a reference to this object, so
  // rebinding the local would have left the routes serving the primary payload.
  let restore = null;
  if (m.variant && payload && payload.__variants && payload.__variants[m.variant]) {
    const v = payload.__variants[m.variant];
    restore = { policy: payload.policy, drawers: payload.drawers };
    payload.policy = v.policy;
    payload.drawers = v.drawers;
  }
  const finish = (r) => { if (restore) { payload.policy = restore.policy; payload.drawers = restore.drawers; } return r; };
  await driver.close().catch(() => {});
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
  await gotoD1(driver);

  if (m.check === 'binding') {
    const r = await BIND.validateWithDriver(driver, chart, payload);
    return finish({ caught: r.findings.length > 0, evidence: r.findings.slice(0, 2) });
  }

  if (m.check === 'closure') {
    const probe = await driver.evaluate(function (args) {
      const M = args.markers;
      // Scoped to the chips. The drawer root carries an unmarked placeholder
      // ("\u2014" in #dr-planet-name) before any drawer is opened, so including
      // it made this detector return findings on the CLEAN subject and every
      // closure mutant reported "caught" without its own mutation being seen.
      const roots = [document.getElementById('planet-list')];
      const out = [];
      roots.forEach(function (root) {
        if (!root) return;
        const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let n;
        while ((n = w.nextNode())) {
          const t = (n.textContent || '').trim();
          if (!t) continue;
          let e = n.parentElement, ok = false;
          while (e && e !== root.parentElement) {
            for (let i = 0; i < M.length; i++) if (e.hasAttribute(M[i])) { ok = true; break; }
            if (ok) break;
            e = e.parentElement;
          }
          if (!ok) out.push(n.parentElement.tagName + '.' + n.parentElement.className + '::' + t.slice(0, 30));
        }
        Array.prototype.forEach.call(root.querySelectorAll('.planet-chip'), function (c) {
          if ((c.getAttribute('class') || '').trim() !== 'planet-chip')
            out.push('chip root class is "' + c.getAttribute('class') + '"');
        });
      });
      return out;
    }, { markers: ['data-d1-field', 'data-d1-chart-field', 'data-d1-literal', 'data-d1-error-field', 'data-d1-corpus-state'] });
    return finish({ caught: probe.length > 0, evidence: probe.slice(0, 2) });
  }

  // corpus. Sun carries resolvable refs, Rahu carries unresolvable ones; a
  // mutant may corrupt either branch, so both drawers are inspected.
  const bad = [];
  for (const idx of [0, 7]) {
  await driver.evaluate(() => { closeDrawer(); return 1; });
  await driver.wait(120);
  await driver.click('#page-d1 .planet-chip', idx);
  await driver.wait(500);
  const refs = await driver.evaluate(function () {
    const root = document.getElementById('drawer-body');
    return Array.prototype.map.call(root.querySelectorAll('[data-d1-corpus-state]'), function (el) {
      return { corpus: el.getAttribute('data-d1-corpus'), graha: el.getAttribute('data-d1-corpus-graha'),
               key: el.getAttribute('data-d1-corpus-key'), state: el.getAttribute('data-d1-corpus-state'),
               text: (el.textContent || '') };
    });
  });
  const declared = await driver.evaluate(function (args) {
    return args.refs.map(function (r) {
      try {
        if (r.corpus === 'RASHI_CORPUS') return (D1_RASHI_CORPUS[r.graha] || {})[r.key] || '';
        if (r.corpus === 'HOUSE_CORPUS') return (HOUSE_CORPUS[r.graha] || {})[r.key] || '';
        if (r.corpus === 'BHAVAT_DESC') return BHAVAT_DESC[r.key] || '';
        if (r.corpus === 'BHAVA_KARAKA') return (BHAVA_KARAKA[r.key] || {}).text || '';
      } catch (e) { /* fall through */ }
      return '';
    });
  }, { refs });
  refs.forEach(function (r, i) {
    if (r.state === 'unresolvable') {
      if (r.text.trim() !== '') bad.push(`${r.corpus}/${r.key} unresolvable but rendered prose`);
      return;
    }
    const g = C.GRAHAS[idx];
    const want = String(declared[i] || '').replace(/\{sign\}/g, C.S[g] ? C.S[g].SIGN : '');
    if (r.text.trim() !== want.trim()) bad.push(`${g}: ${r.corpus}/${r.key} text is not the declared branch`);
  });
  }
  return finish({ caught: bad.length > 0, evidence: bad.slice(0, 2) });
}

/**
 * Runs every mutant. Returns { passed, results } where passed is true only when
 * all mutants were caught. Certification consumes this result, never a flag.
 */
async function runAdversarialSuite(driver, cleanSource, chart, payload, routes, gotoD1, log) {
  log = log || (() => {});
  const results = [];

  // BASELINE. Each detector must return ZERO findings on the clean subject
  // before any mutant is trusted. Without this a detector firing for unrelated
  // reasons makes every mutant of that kind report "caught" while its own
  // mutation goes unseen.
  const baseline = {};
  for (const kind of ['closure', 'binding', 'corpus']) {
    const probe = { id: 'BASE-' + kind, check: kind, name: 'clean-subject baseline' };
    let r;
    try { r = await runMutant(driver, probe, cleanSource, chart, payload, routes, gotoD1); }
    catch (e) { r = { caught: true, evidence: ['baseline runtime: ' + String(e.message).slice(0, 120)] }; }
    baseline[kind] = r;
    if (r.caught) {
      results.push({ id: 'BASE-' + kind, name: `${kind} detector is not clean on the unmodified subject`,
                     check: kind, built: true, caught: false, evidence: r.evidence });
      log(`  FAIL BASE-${kind} — detector returns findings on the CLEAN subject: ${(r.evidence || []).join('; ')}`);
    } else {
      log(`  ok   BASE-${kind} — detector returns zero findings on the clean subject`);
    }
  }
  for (const m of MUTANTS) {
    let source, built = true, err = null;
    try { source = m.apply(cleanSource); }
    catch (e) { built = false; err = e.message; }
    if (!built) {
      results.push({ id: m.id, name: m.name, caught: false, built: false, evidence: [err] });
      log(`  FAIL ${m.id} ${m.name} — mutation did not apply: ${err}`);
      continue;
    }
    // A mutant is only trusted when its detector was clean on the baseline.
    if (baseline[m.check] && baseline[m.check].caught) {
      results.push({ id: m.id, name: m.name, check: m.check, built: true, caught: false,
                     evidence: [`${m.check} detector was not clean on the baseline; result not trustworthy`] });
      log(`  FAIL ${m.id} [${m.check}] ${m.name} — baseline not clean`);
      continue;
    }
    let r;
    try { r = await runMutant(driver, m, source, chart, payload, routes, gotoD1); }
    catch (e) { r = { caught: false, evidence: ['runtime: ' + String(e.message).slice(0, 120)] }; }
    // MUTATION-SPECIFIC EVIDENCE. Where the mutant declares an `expect`, the
    // finding text must match it, so a mutant caught for an unrelated reason
    // does not count as caught.
    let specific = true, why = '';
    if (r.caught && m.expect) {
      specific = (r.evidence || []).some(e => m.expect.test(String(e)));
      if (!specific) why = ` — caught, but no evidence matching ${m.expect}`;
    }
    const caught = r.caught && specific;
    results.push({ id: m.id, name: m.name, check: m.check, built: true, caught,
                   evidence: r.evidence });
    log(`  ${caught ? 'ok  ' : 'FAIL'} ${m.id} [${m.check}] ${m.name}` +
        (caught ? '' : (r.caught ? why : ' — NOT CAUGHT')));
  }
  return { passed: results.every(r => r.caught), results, total: MUTANTS.length,
           caught: results.filter(r => r.caught).length };
}

module.exports = { MUTANTS, runAdversarialSuite, runMutant };
