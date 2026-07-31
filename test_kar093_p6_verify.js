#!/usr/bin/env node
'use strict';
/**
 * KAR-093 · GATE v3 · P6 ADVERSARIAL SUITE
 *
 * Every case here is a way the REJECTED P6 would have returned a pass. The old
 * phase read `_evidence` out of the fixture, so a hand-written artifact with a
 * plausible manifest satisfied all six of its checks. These mutants exist to
 * prove the replacement does not have that property, and to prove it still
 * passes on the clean bundle.
 *
 * TWO TIERS, DELIBERATELY:
 *   E · execution   real files are mutated on disk and the verifier subprocess
 *                   actually runs against them. Slow, and the only tier that
 *                   proves the Python side.
 *   J · judgement   the oracle in kar093_p6_bind.js is fed an observed record
 *                   with one fact altered. Covers states that are awkward to
 *                   produce physically, such as an aspect edge swapped for a
 *                   different valid one.
 *
 * RULES CARRIED FROM P5, WHICH QA IMPOSED AND I AGREE WITH:
 *   - The clean bundle must produce ZERO problems before any mutant is
 *     trusted. A detector that fires on the unmodified subject makes every
 *     "caught" meaningless.
 *   - A mutant counts as caught ONLY when the returned evidence matches what it
 *     declared it would cause. Any failure for any reason is not a pass.
 *   - E7 is the inverse case and matters most: a forged `_evidence` block must
 *     NOT change the verdict. If lying in the artifact still moves P6, nothing
 *     here has been fixed.
 *
 * Usage: node test_kar093_p6_verify.js [--python=/tmp/prod/bin/python]
 *                                      [--pydantic2=/tmp/pyd2/bin/python]
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { runP6Verifier, judgeP6, ACCEPTED_P6, canonicalSha } = require('./kar093_p6_bind.js');

const argOf = n => (process.argv.find(a => a.startsWith('--' + n + '=')) || '').split('=')[1];
const PY = argOf('python') || process.env.KAR093_PYTHON || 'python3';
const PY2 = argOf('pydantic2');
const SRC_DIR = argOf('bundle') || path.join(__dirname, 'd1');
const PRODUCT = argOf('product') || path.join(__dirname, 'newphalit_fixed.html');

const BUNDLE_FILES = ['d1_contract.py', 'd1_engine.py', 'd1_functional_roles.py',
                      'd1_synthesis.py', 'd1_chart_adapter.py', 'd1_routes.py',
                      'kar093_p6_generate_fixture.py',
                      'kar093_p6_verify.py'];

let pass = 0, fail = 0;
const failures = [];
function check(name, ok, detail) {
  if (ok) { pass++; console.log('  \u2713 ' + name); }
  else { fail++; failures.push(name + (detail ? ' — ' + detail : '')); console.log('  \u2717 ' + name + (detail ? ' — ' + detail : '')); }
}

/** A disposable copy of the bundle, so mutants never touch the real files. */
function makeBundle(tag) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kar093_p6_' + tag + '_'));
  BUNDLE_FILES.forEach(f => fs.copyFileSync(path.join(SRC_DIR, f), path.join(dir, f)));
  const html = path.join(dir, 'newphalit_fixed.html');
  fs.copyFileSync(PRODUCT, html);
  return { dir, html };
}

function runOn(b, opts) {
  opts = opts || {};
  return runP6Verifier({
    htmlPath: opts.html || b.html,
    python: opts.python || PY,
    p6Dir: b.dir,
    p6Out: path.join(b.dir, 'generated.json')
  });
}

/** What the contract module would hand the browser. Clean case: the artifact
 *  the verifier just wrote. Mutants override it. */
function servedFrom(run, mutate) {
  const obj = JSON.parse(JSON.stringify(run.generated));
  if (mutate) mutate(obj);
  return obj;
}

function problemsOf(verdict) { return (verdict.problems || []).join(' || '); }

function expectCaught(name, verdict, expected) {
  if (verdict.pass) return check(name, false, 'NOT CAUGHT: the mutant passed P6');
  const hay = problemsOf(verdict);
  check(name, hay.includes(expected),
        hay.includes(expected) ? '' : 'caught, but for the wrong reason: ' + hay.slice(0, 240));
}

console.log('KAR-093 · P6 ADVERSARIAL SUITE');
console.log('bundle  : ' + SRC_DIR);
console.log('product : ' + PRODUCT);
console.log('python  : ' + PY);
console.log('');

// ── E0 · the clean bundle, which every other case depends on ───────────────
console.log('E · execution');
const clean = makeBundle('clean');
const cleanRun = runOn(clean);
check('E0a verifier ran on the clean bundle', cleanRun.ran, cleanRun.error);
let cleanVerdict = { pass: false, problems: ['verifier did not run'] };
if (cleanRun.ran) {
  cleanVerdict = judgeP6(cleanRun, servedFrom(cleanRun));
  check('E0b clean bundle produces ZERO problems', cleanVerdict.pass, problemsOf(cleanVerdict));
  // E0c was "regeneration is byte-deterministic (accepted fixture sha256)".
  // Retargeted under B03: whole-file determinism is host-specific because the
  // artifact embeds the generating interpreter's version. What must be
  // deterministic is the payload the browser sees.
  {
    const f = {};
    ACCEPTED_P6.payloadKeys.forEach(k => { f[k] = cleanRun.generated[k]; });
    check('E0c regeneration is deterministic in the digest that governs',
          canonicalSha(f) === ACCEPTED_P6.payloadCanonicalSha256, canonicalSha(f));
  }
  const facing = {};
  ACCEPTED_P6.payloadKeys.forEach(k => { facing[k] = cleanRun.generated[k]; });
  check('E0e browser-facing payload matches the accepted canonical digest',
        canonicalSha(facing) === ACCEPTED_P6.payloadCanonicalSha256, canonicalSha(facing));
  check('E0d the 13-edge doctrine set is what the engine produced',
        (cleanRun.observed.generated.aspect_edges || []).slice().sort().join('|') ===
        ACCEPTED_P6.aspectEdges.join('|'));
}
if (!cleanVerdict.pass) {
  console.log('\nABORT: the clean bundle does not pass. No mutant result can be trusted.');
  console.log(problemsOf(cleanVerdict));
  process.exit(2);
}

// ── E1 · a module byte changes ─────────────────────────────────────────────
{
  const b = makeBundle('mod');
  fs.appendFileSync(path.join(b.dir, 'd1_engine.py'), '\n# one byte of drift\n');
  const r = runOn(b);
  expectCaught('E1 module byte changed -> hash mismatch',
               r.ran ? judgeP6(r, servedFrom(r)) : { pass: false, problems: [r.error] },
               'd1_engine.py sha256');
}

// ── E1b · the FIFTH module, same shape as E1 ───────────────────────────────
// d1_chart_adapter.py is not in the fixture's construction path, so without
// this case its pin would be asserted and never exercised. That is the
// declared-but-unchecked pattern this ticket exists to stop.
{
  const b = makeBundle('adapter');
  fs.appendFileSync(path.join(b.dir, 'd1_chart_adapter.py'), '\n# one byte of drift\n');
  const r = runOn(b);
  expectCaught('E1b adapter byte changed -> hash mismatch',
               r.ran ? judgeP6(r, servedFrom(r)) : { pass: false, problems: [r.error] },
               'd1_chart_adapter.py sha256');
}

// ── E1c · the ROUTE module, same shape as E1 and E1b ───────────────────────
// The route is the layer gate v3 cannot see at all. Without this case its pin
// would be asserted and never exercised, which is the pattern B04 came from.
{
  const b = makeBundle('routes');
  fs.appendFileSync(path.join(b.dir, 'd1_routes.py'), '\n# one byte of drift\n');
  const r = runOn(b);
  expectCaught('E1c route byte changed -> hash mismatch',
               r.ran ? judgeP6(r, servedFrom(r)) : { pass: false, problems: [r.error] },
               'd1_routes.py sha256');
}

// ── E2 · the product subject is not product v5 ─────────────────────────────
{
  const b = makeBundle('html');
  fs.appendFileSync(b.html, '<!-- one byte of drift -->\n');
  const r = runOn(b);
  expectCaught('E2 product HTML byte changed -> subject mismatch',
               r.ran ? judgeP6(r, servedFrom(r)) : { pass: false, problems: [r.error] },
               'product subject sha256');
}

// ── E3 · a sentinel already occurs in the page ─────────────────────────────
// If a sentinel exists in the product source, its appearance in the DOM proves
// nothing about provenance, which is the whole basis of P2 and P4.
{
  const b = makeBundle('collide');
  const html = fs.readFileSync(b.html, 'utf8');
  fs.writeFileSync(b.html, html.replace('</body>', '<!-- ZQXSUNSIGNQ7 --></body>'));
  const r = runOn(b);
  const v = r.ran ? judgeP6(r, servedFrom(r)) : { pass: false, problems: [r.error] };
  expectCaught('E3 sentinel planted in the page -> collision reported', v, 'sentinel collisions');
}

// ── E4 · an accepted module is absent ──────────────────────────────────────
{
  const b = makeBundle('missing');
  fs.unlinkSync(path.join(b.dir, 'd1_functional_roles.py'));
  const r = runOn(b);
  expectCaught('E4 missing accepted module -> fails closed with the reason',
               judgeP6(r, null), 'accepted module missing');
}

// ── E5 · the wrong pydantic ────────────────────────────────────────────────
if (PY2) {
  const b = makeBundle('pyd2');
  const r = runOn(b, { python: PY2 });
  expectCaught('E5 pydantic 2 interpreter -> P6 refuses on the pin',
               judgeP6(r, r.ran ? servedFrom(r) : null),
               'is not the pinned ' + ACCEPTED_P6.pydantic);
} else {
  console.log('  \u25CB E5 skipped: no --pydantic2 interpreter supplied');
}

// ── E6 · the verifier itself is absent ─────────────────────────────────────
{
  const b = makeBundle('noverifier');
  fs.unlinkSync(path.join(b.dir, 'kar093_p6_verify.py'));
  const r = runOn(b);
  expectCaught('E6 verifier absent -> fails closed', judgeP6(r, null), 'verifier not found');
}

// ── E7 · THE INVERSE CASE. A forged _evidence block must change nothing ────
// This is the defect QA found, stated as a test. The artifact claims pydantic
// 9.9.9, ninety-nine edges and a different product hash; every real fact is
// unchanged. P6 must still PASS, because it no longer reads any of that.
{
  const served = servedFrom(cleanRun, o => {
    o._evidence.runtime.pydantic = '9.9.9';
    o._evidence.aspect_manifest.edge_count = 99;
    o._evidence.aspect_manifest.edges = ['Rahu 7th'];
    o._evidence.modules = { 'made_up.py': 'deadbeef' };
    o._evidence.doctrine.legacy_flat_roles_publishable = true;
    o._evidence.revalidated_through = 'nothing at all';
    o._evidence.product_subject.sentinel_collisions = ['ZQXSUNSIGNQ7'];
    o._evidence.import_chain_closed = false;
  });
  const v = judgeP6(cleanRun, served);
  check('E7 forged _evidence has NO effect on the verdict (P6-001 is gone)',
        v.pass, problemsOf(v));
}

// ── E8 · the payload served to the browser is not the generated one ────────
{
  const served = servedFrom(cleanRun, o => {
    o.drawers.drawers[0].rashi.dignity_label = 'Swakshetra';
  });
  expectCaught('E8 tampered payload served to the browser -> divergence',
               judgeP6(cleanRun, served),
               'differs from the generated one at "drawers"');
}

// ── J · judgement tier ─────────────────────────────────────────────────────
console.log('');
console.log('J · judgement');
const baseRun = () => JSON.parse(JSON.stringify(cleanRun));
function judgeWith(mutate) {
  const r = baseRun();
  mutate(r.observed);
  return judgeP6(r, servedFrom(cleanRun));
}

expectCaught('J1 one edge swapped for another, count still 13',
  judgeWith(o => {
    const e = o.generated.aspect_edges;
    e[e.indexOf('Saturn 3rd')] = 'Venus 4th';
  }), 'aspect manifest is');

expectCaught('J2 module hashed at one path, imported from another',
  judgeWith(o => { o.modules['d1_synthesis.py'].path_matches_import = false;
                   o.modules['d1_synthesis.py'].imported_from = '/elsewhere/d1_synthesis.py'; }),
  'was hashed at');

expectCaught('J3 import chain not closed',
  judgeWith(o => { o.import_chain.closed = false; o.import_chain.synthesis_shares_contract_graha = false; }),
  'import chain not closed');

expectCaught('J4 payload never re-parsed through the accepted model',
  judgeWith(o => { o.generated.revalidated = false; }), 're-parsed through the accepted payload model');

expectCaught('J5 legacy flat roles marked publishable',
  judgeWith(o => { o.generated.doctrine.legacy_flat_roles_publishable = true; }),
  'legacy flat roles');

// J6 was "regenerated fixture does not match the accepted hash" and expected a
// catch. Under B03 that comparison is gone, so the case is INVERTED BY DESIGN:
// it now proves the removed check is actually removed. This is B03 stated as a
// regression test, the same shape as E7 for P6-001. J6b below still proves that
// a real payload change moves the canonical digest and IS caught, so the pair
// covers both directions and neither can pass vacuously.
{
  const v = judgeWith(o => { o.generated.fixture_sha256 = 'f'.repeat(64); });
  check('J6 a differing whole-file fixture hash is NOT a finding (B03)',
        v.pass, problemsOf(v));
}

// J6b is the one that survives a cosmetic change to the evidence block: the
// browser-facing digest is computed by the gate from the generated payload, so
// altering a real value moves it even when every reported fact still lines up.
{
  const r = baseRun();
  r.generated = JSON.parse(JSON.stringify(cleanRun.generated));
  r.generated.drawers.drawers[0].position.dignity = 'Debilitated';
  expectCaught('J6b generated payload altered -> canonical digest moves',
               judgeP6(r, servedFrom({ generated: r.generated })),
               'regenerated payload digest');
}

expectCaught('J7 an accepted module is not in the observed set',
  judgeWith(o => { delete o.modules['d1_contract.py']; }), 'module set is');

expectCaught('J8 drawer count is not nine',
  judgeWith(o => { o.generated.drawer_count = 8; }), 'drawers, accepted 9');

expectCaught('J9 node aspect policy silently changed',
  judgeWith(o => { o.generated.node_aspect_policy = 'five_seven_nine'; }),
  'node_aspect_policy is five_seven_nine');

expectCaught('J10 verifier reported its own errors',
  judgeWith(o => { o.ok = false; o.errors = ['generation raised: boom']; }), 'verifier: generation raised');

console.log('');
console.log(`RESULT: ${pass} passed, ${fail} failed`);
failures.forEach(f => console.log('  - ' + f));
process.exit(fail ? 1 : 0);
