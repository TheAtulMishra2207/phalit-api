'use strict';
/**
 * KAR-093 · GATE v3 · P6 BINDING  (answers QA blocker P6-001)
 *
 * Split out of kar093_gate3.js so the P6 oracle can be reviewed and exercised
 * on its own, without a browser driver or a page. test_kar093_p6_verify.js
 * drives exactly this module.
 *
 * DIVISION OF LABOUR:
 *   kar093_p6_verify.py   mechanism. Executes the accepted generator and
 *                         reports what it observed. Judges nothing.
 *   this file             oracle. Holds the accepted constants and does all
 *                         the comparing.
 *   kar093_p6_fixture.json  a build product. Nothing in it is trusted; the
 *                         payload is regenerated every run and the artifact is
 *                         only ever compared against that regeneration.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

/**
 * ── P6 · THE ORACLE ────────────────────────────────────────────────────────
 *
 * QA blocker P6-001: the previous P6 read `_evidence` out of the fixture and
 * set phaseResults.P6 from it, so the artifact was both subject and witness.
 * A hand-written fixture carrying a forged `_evidence` block passed.
 *
 * The accepted values now live HERE, in the gate, and the facts they are
 * compared against are derived by executing kar093_p6_verify.py during the
 * run. The verifier reports what it observed and renders no verdict; this file
 * does the judging. Editing the fixture cannot move either side.
 *
 * ASPECT_EDGES is transcribed from the doctrine, NOT copied from the engine's
 * output: every classical graha casts the 7th; Mars adds 4 and 8; Jupiter adds
 * 5 and 9; Saturn adds 3 and 10; Rahu and Ketu cast none (founder ruling
 * 2026-07-25, node_aspect_policy=no_independent_drishti). An oracle copied from
 * the thing it checks is the circularity QA caught in the 84-cell matrix.
 */
const P6_DOCTRINE_DRISHTI = {
  Sun:     ['7th'],
  Moon:    ['7th'],
  Mars:    ['7th', '4th', '8th'],
  Mercury: ['7th'],
  Jupiter: ['7th', '5th', '9th'],
  Venus:   ['7th'],
  Saturn:  ['7th', '3rd', '10th']
  // Rahu and Ketu are absent by ruling, not by omission.
};

const ACCEPTED_P6 = {
  pydantic: '1.10.13',
  modules: {
    'd1_contract.py':         '36b3d131713959b23362407b2ee928eba4cf8b547c630fa02812a777f890b51f',
    'd1_engine.py':           '59da497a697e31f6fdc3fd8d7ad2facc09ec8bde1d2ef5cd61793c0415c451d8',
    // UNCHANGED by the D9 port. Left at its original value deliberately: it is
    // the record that the port never touched functional roles.
    'd1_functional_roles.py': '7689984fcb9fe01ad36c4926f284a506ce4daa9eb51135505e2b94cf5aff3cc3',
    'd1_synthesis.py':        '8bb49c9a9cea356e05fd870976ca0f9e5364381da6049a12afff4a89682c4757',
    // D9 port. A NEW KEY, permitted by the amended re-pin constraint 1 where a
    // module joins the set. It is hashed AND imported AND identity-checked by
    // the verifier, so the pin carries the same weight as its four neighbours.
    'd1_chart_adapter.py':    'be088670c891791cf57d949f1b7fc8e181175e911edcf602ca02b7f7cda07760',
    // KAR-093-B04. The route is the one join gate v3 structurally cannot reach:
    // it stubs the network boundary, so a varga dropped in the request model is
    // invisible to every phase. Pinned with the same import-and-identity
    // treatment as the adapter.
    'd1_routes.py':           'bd2f8109cc85c2c32a3d60016564659836824839c7599019d495d40200480ca3'
  },
  productSha256: '7e026b371a64e43602b93c4804c28181cf6e837d285d40e3f2b174368cc649d3',
  // Whole-file hash of the regenerated artifact. Deterministic on any host:
  // the generator records the product BASENAME, never an absolute path.
  // RECORDED PROVENANCE ONLY (KAR-093-B03). Not compared, not re-pinned: the
  // artifact embeds the generating interpreter's version, so this value is
  // host-specific by construction. payloadCanonicalSha256 governs.
  fixtureSha256: '7b2bc75e665ce88ce1d2fd3a5983b3e962a95a90497648368a4b97439385e4a8',
  // Canonical digest of the BROWSER-FACING subtrees only (policy, drawers,
  // _chart, _variants). This is the value that matters: `_evidence` is
  // diagnostic and must not be able to move the verdict in either
  // direction, including by breaking a whole-file hash comparison.
  payloadCanonicalSha256: 'fa06cb962b7cb1ad86f4bc0d66d0ddb10384abfb0ec6fe75114d707a109ceb72',
  payloadKeys: ['policy', 'drawers', '_chart', '_variants'],
  drawers: 9,
  grahas: 9,
  houses: 12,
  enginePolicy: {
    engine_version: 'd1-engine-0.1.0',
    aspect_policy_version: 'parashari-d1-1.0',
    node_aspect_policy: 'no_independent_drishti'
  },
  aspectEdges: Object.keys(P6_DOCTRINE_DRISHTI)
    .reduce((acc, g) => acc.concat(P6_DOCTRINE_DRISHTI[g].map(k => g + ' ' + k)), [])
    .sort(),
  revalidatedThrough: 'd1_synthesis.D1DrawerPayload.parse_obj',
  doctrine: { orthogonal_roles_publishable: true, legacy_flat_roles_publishable: false }
};

/** Stable digest of a JSON value with object keys sorted, so key order cannot
 *  make two identical payloads look different or two different ones look
 *  identical. */
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object')
    return '{' + Object.keys(value).sort()
      .map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value === undefined ? null : value);
}
function canonicalSha(value) {
  return crypto.createHash('sha256').update(canonical(value)).digest('hex');
}

/**
 * Run the verifier as a subprocess. It executes the accepted generator against
 * the accepted modules and writes a result file of OBSERVED facts.
 *
 * Fails closed. No Python, a missing verifier, a non-zero exit or an
 * unparseable result all leave P6 unproven; none of them is a pass, and none
 * silently falls back to a fixture on disk.
 */
function runP6Verifier(opts) {
  const dir = opts.p6Dir || __dirname;
  const verifier = path.join(dir, 'kar093_p6_verify.py');
  const outPath = opts.p6Out || path.join(os.tmpdir(), 'kar093_p6_fixture.generated.json');
  const resPath = path.join(os.tmpdir(), 'kar093_p6_result.json');
  const py = opts.python || process.env.KAR093_PYTHON || 'python3';
  if (!fs.existsSync(verifier))
    return { ran: false, error: 'verifier not found at ' + verifier };
  let stdout = '';
  try {
    stdout = execFileSync(py, [
      verifier,
      '--product=' + path.resolve(opts.htmlPath),
      '--modules=' + dir,
      '--out=' + outPath,
      '--result=' + resPath,
      '--shipped=' + path.join(dir, 'kar093_p6_fixture.json')
    ], { encoding: 'utf8', maxBuffer: 1 << 26 });
  } catch (e) {
    stdout = (e.stdout || '') + (e.stderr || '');
    if (!fs.existsSync(resPath))
      return { ran: false, error: 'verifier failed and wrote no result: ' + String(e.message).slice(0, 300), stdout };
  }
  let observed;
  try {
    observed = JSON.parse(fs.readFileSync(resPath, 'utf8'));
  } catch (e) {
    return { ran: false, error: 'verifier result is not parseable JSON: ' + e.message, stdout };
  }
  let generated = null;
  try {
    generated = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  } catch (e) {
    // Surface what the verifier actually said. A gate that fails closed with an
    // unhelpful reason gets routed around, which is its own kind of failure.
    const why = (observed && Array.isArray(observed.errors) && observed.errors.length)
      ? observed.errors.join('; ') : e.message;
    return { ran: false, error: 'the verifier produced no payload: ' + why, observed, stdout };
  }
  return { ran: true, observed, generated, outPath, resPath, stdout };
}

/**
 * Compare the verifier's observed facts with ACCEPTED_P6, and prove that the
 * payload the browser phases are about to consume is the one just generated.
 *
 * `loaded` is whatever the contract module will feed the routes. Comparing it
 * by canonical digest against the freshly generated object closes the gap
 * between "a model-generated fixture exists" and "the gate tested with it",
 * without either side needing to know where the other put the file.
 */
function judgeP6(run, loaded) {
  const problems = [];
  if (!run.ran) {
    problems.push(run.error || 'the P6 verifier did not run');
    // Even on a hard failure, report a wrong runtime explicitly if the verifier
    // got far enough to record one. "no payload" alone hides the actual cause.
    const rt = (run.observed || {}).runtime || {};
    if (rt.pydantic && rt.pydantic !== ACCEPTED_P6.pydantic)
      problems.push(`pydantic ${rt.pydantic} is not the pinned ${ACCEPTED_P6.pydantic}`);
    return { pass: false, problems };
  }
  const o = run.observed || {};
  const g = (o.generated || {});

  if (!o.ok) (o.errors || ['verifier reported failure']).forEach(e => problems.push('verifier: ' + e));
  if (((o.runtime || {}).pydantic) !== ACCEPTED_P6.pydantic)
    problems.push(`pydantic ${(o.runtime || {}).pydantic} is not the pinned ${ACCEPTED_P6.pydantic}`);

  // Exact names AND exact hashes. The old check counted entries.
  const seen = Object.keys(o.modules || {}).sort();
  const want = Object.keys(ACCEPTED_P6.modules).sort();
  if (seen.join(',') !== want.join(','))
    problems.push(`module set is [${seen.join(', ')}], accepted set is [${want.join(', ')}]`);
  want.forEach(m => {
    const e = (o.modules || {})[m];
    if (!e) return;
    if (e.sha256 !== ACCEPTED_P6.modules[m])
      problems.push(`${m} sha256 ${String(e.sha256).slice(0, 16)} is not the accepted ${ACCEPTED_P6.modules[m].slice(0, 16)}`);
    if (e.path_matches_import !== true)
      problems.push(`${m} was hashed at ${e.path} but imported from ${e.imported_from}`);
  });

  if (!(o.import_chain || {}).closed)
    problems.push('import chain not closed: ' + JSON.stringify(o.import_chain || {}));

  // The exact edge SET, not the count.
  const edges = (g.aspect_edges || []).slice().sort();
  if (edges.join(' | ') !== ACCEPTED_P6.aspectEdges.join(' | '))
    problems.push(`aspect manifest is [${edges.join(', ')}], doctrine requires [${ACCEPTED_P6.aspectEdges.join(', ')}]`);

  ['engine_version', 'aspect_policy_version', 'node_aspect_policy'].forEach(k => {
    if (g[k] !== ACCEPTED_P6.enginePolicy[k])
      problems.push(`policy.${k} is ${g[k]}, accepted is ${ACCEPTED_P6.enginePolicy[k]}`);
  });
  if (g.drawer_count !== ACCEPTED_P6.drawers) problems.push(`${g.drawer_count} drawers, accepted ${ACCEPTED_P6.drawers}`);
  if (g.graha_count !== ACCEPTED_P6.grahas) problems.push(`${g.graha_count} grahas, accepted ${ACCEPTED_P6.grahas}`);
  if (g.house_count !== ACCEPTED_P6.houses) problems.push(`${g.house_count} houses, accepted ${ACCEPTED_P6.houses}`);
  if (g.revalidated !== true || g.revalidated_through !== ACCEPTED_P6.revalidatedThrough)
    problems.push('the generated payload was not re-parsed through the accepted payload model');
  if ((g.doctrine || {}).orthogonal_roles_publishable !== ACCEPTED_P6.doctrine.orthogonal_roles_publishable)
    problems.push('orthogonal roles are not publishable');
  if ((g.doctrine || {}).legacy_flat_roles_publishable !== ACCEPTED_P6.doctrine.legacy_flat_roles_publishable)
    problems.push('legacy flat roles are marked publishable');
  // KAR-093-B03. The whole-file hash NO LONGER GATES. `_evidence.runtime.python`
  // is part of the artifact, so regenerating on a different interpreter moves
  // the file hash while the browser-facing payload is byte-identical. Comparing
  // it produced an in-scope finding for a difference that carries no meaning.
  // ACCEPTED_P6.fixtureSha256 is retained as RECORDED PROVENANCE and is printed
  // in the run notes; it is deliberately not re-pinned, because any new pin
  // would be host-specific in exactly the same way and would fail on the next
  // Python. The canonical digest below is what governs.
  // The digest that actually governs: the payload the browser will see.
  const facing = {};
  ACCEPTED_P6.payloadKeys.forEach(k => { facing[k] = (run.generated || {})[k]; });
  const facingSha = canonicalSha(facing);
  if (facingSha !== ACCEPTED_P6.payloadCanonicalSha256)
    problems.push(`regenerated payload digest ${facingSha.slice(0, 16)} is not the accepted ${ACCEPTED_P6.payloadCanonicalSha256.slice(0, 16)}`);

  // The product subject, hashed from the bytes the gate itself loaded.
  const p = o.product || {};
  if (p.sha256 !== ACCEPTED_P6.productSha256)
    problems.push(`product subject sha256 ${String(p.sha256).slice(0, 16)} is not accepted product v5 ${ACCEPTED_P6.productSha256.slice(0, 16)}`);
  if (!Array.isArray(p.sentinel_collisions) || p.sentinel_collisions.length)
    problems.push('sentinel collisions with the product subject: ' + JSON.stringify(p.sentinel_collisions));

  // What the browser will actually be served must BE the generated payload.
  if (!loaded) problems.push('the contract module served no payload to compare against');
  else {
    ['policy', 'drawers', '_chart', '_variants'].forEach(k => {
      const a = canonicalSha(run.generated[k]);
      const b = canonicalSha(loaded[k]);
      if (a !== b) problems.push(`the payload served to the browser differs from the generated one at "${k}" (${a.slice(0, 12)} vs ${b.slice(0, 12)})`);
    });
  }
  return { pass: problems.length === 0, problems };
}

module.exports = { P6_DOCTRINE_DRISHTI, ACCEPTED_P6, canonical, canonicalSha,
                   runP6Verifier, judgeP6 };
