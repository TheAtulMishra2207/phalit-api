// KAR-091 corpus safety test v7.
//
// New in v6 (QA v5 corrections):
//  - ONE CANONICAL CLASSIFIER: the page must embed kar091_classify.js verbatim
//    between KAR091-CLASSIFIER-CANONICAL markers (source identity), and the
//    embedded classifier must produce identical categories to the Node module
//    over the ENTIRE corpus (behavioral parity).
//  - All-or-nothing extraction: extractAddCalls throws on any unresolved
//    argument, so the DOM test runs only on fully reconstructed objects.
//  - Permanent negatives for: template-hole harm, function-returned container
//    value, and HTML/Node classifier drift.
const fs = require('fs');
const crypto = require('crypto');
const { extractVerdicts, extractAddCalls, ExtractionError } = require('./kar091_extract_verdicts.js');
const { auditCorpus, fullHash, entityKey, AuditError } = require('./kar091_audit.js');
const { kar091Classify } = require('./kar091_classify.js');

const HTML_PATH = process.argv[2] || 'newphalit.html';
const REVIEWED = process.argv[3] || 'kar091_reviewed_manifest.json';
const js = fs.readFileSync(HTML_PATH, 'utf8');
const htmlSha = crypto.createHash('sha256').update(js).digest('hex');

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log('  FAIL: ' + m)); };

// ── canonical classifier: source identity + behavioral parity ────────────────
const MARK_A = '// KAR091-CLASSIFIER-CANONICAL-BEGIN';
const MARK_B = '// KAR091-CLASSIFIER-CANONICAL-END';
function embeddedClassifierSource(html) {
  const a = html.indexOf(MARK_A), b = html.indexOf(MARK_B);
  if (a < 0 || b < 0) return null;
  return html.slice(a + MARK_A.length, b).trim();
}
function moduleClassifierSource() {
  const src = fs.readFileSync(require.resolve('./kar091_classify.js'), 'utf8');
  return src.slice(src.indexOf('const KAR091_HARM_PATTERNS'), src.indexOf('module.exports')).trim();
}
function classifierParity(html) {
  const emb = embeddedClassifierSource(html);
  if (emb == null) return { sourceIdentical: false, behavioralIdentical: false };
  const mod = moduleClassifierSource();
  const sourceIdentical = emb === mod;
  let behavioralIdentical = true;
  try {
    const htmlClassify = new Function(emb + '\nreturn kar091Classify;')();
    const m = extractVerdicts(HTML_PATH);
    for (const e of m.entries) {
      if (JSON.stringify(htmlClassify(e.text)) !== JSON.stringify(kar091Classify(e.text))) { behavioralIdentical = false; break; }
    }
  } catch { behavioralIdentical = false; }
  return { sourceIdentical, behavioralIdentical };
}

console.log(`=== extraction + audit integrity (HTML sha ${htmlSha.slice(0, 12)}) ===`);
const manifest = extractVerdicts(HTML_PATH);
ok(manifest.source_file_sha256 === htmlSha, 'manifest hash matches HTML under test');
ok(manifest.entries.every(e => e.fn === 'collectMaleficYogas' || e.fn === 'collectBeneficYogas'), 'all provenance is a collector');
const audit = auditCorpus(HTML_PATH, REVIEWED);
ok(audit.reviewRequired.length === 0, `no REVIEW_REQUIRED (found ${audit.reviewRequired.length})`);
ok(audit.drift.length === 0, `no classifier/manifest drift (found ${audit.drift.length})`);
console.log(`  ${manifest.entries.length} verdicts | harmful ${audit.harmful.length} | benign_reviewed ${audit.reviewedBenign.length}`);

console.log('\n=== canonical classifier parity ===');
{
  const p = classifierParity(js);
  ok(p.sourceIdentical, 'embedded classifier is byte-identical to kar091_classify.js');
  ok(p.behavioralIdentical, 'embedded and Node classifiers agree on every corpus entry');
}

console.log('\n=== wrapper reconstruction coverage ===');
{
  const m = extractVerdicts(HTML_PATH);
  const rySuffixed = m.entries.filter(e => e.kind === 'wrapper:ry' && /\[(Bhavartha|Phala|Sarvartha)[^\]]*\]$/.test(e.text.trim()));
  ok(rySuffixed.length >= 13, `ry res+[citation] variants reconstructed (found ${rySuffixed.length}, need >=13)`);
  const bare = m.entries.some(e => e.kind === 'wrapper:ry' && /^\s*(Bhavartha|Phala|Sarvartha)[^\[]*\d+\/\d+\s*$/.test(e.text));
  ok(!bare, 'no bare citation string audited AS a verdict (the v6 paramIndex bug)');
  const calls = extractAddCalls(HTML_PATH);
  const ryInDom = calls.some(c => c.args.some(a => /Brings forth a king\. Jupiter in its exaltation/.test(String(a))));
  ok(ryInDom, 'wrapper res text present among DOM-reconstructed objects');
}

// ── shipped renderer ─────────────────────────────────────────────────────────
const block = js.slice(js.indexOf(MARK_A), js.indexOf('function renderYogaVichar'));
const bcStart = js.indexOf('function buildCard(y, cls)');
const bcEnd = js.indexOf('\n  }\n', bcStart) + 4;
const api = new Function(block + '\n' + js.slice(bcStart, bcEnd) + `
  return { kar091Classify, kar091FrameV2, kar091ParseSource, buildCard };
`)();
const { kar091FrameV2, kar091ParseSource, buildCard } = api;
const escapeHtml = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const stripAudit = h => h.replace(/<details class="yoga-audit">[\s\S]*?<\/details>/g, '');

console.log('\n=== DOM invariants over REAL collector objects (all-or-nothing) ===');
{
  const calls = extractAddCalls(HTML_PATH);   // throws on ANY unresolved argument
  ok(calls.every(c => c.args.every(a => a != null && a !== '')), 'every argument of every call resolved (no nulls, no empties in non-verdict slots)' );
  let checked = 0, leaks = 0, missingSource = 0, descLeaks = 0, benignChanged = 0;
  for (const c of calls) {
    const [a0, a1, a2, a3] = c.args;
    const y = c.fn === 'collectMaleficYogas'
      ? { cat: a0, name: a1, desc: a2, severity: a3 == null ? 'caution' : a3 }
      : { cat: a0, name: a1, desc: a2, result: a3 || '' };
    const f = kar091FrameV2(y);
    const html = buildCard(y, c.fn === 'collectMaleficYogas' ? 'yoga-malefic' : 'yoga-benefic');
    const visible = stripAudit(html);
    checked++;
    if (f.harmful) {
      const raw = kar091ParseSource(f.original).stripped.replace(/\.$/, '');
      if (raw.length >= 20 && visible.includes(escapeHtml(raw.slice(0, 20)))) leaks++;
      if (!/Source · |Source not specified/.test(html)) missingSource++;
    } else if (y.result || (y.severity && y.severity !== 'caution' && y.severity !== 'warning')) {
      const orig = y.result || y.severity;
      if (f.principal !== orig) benignChanged++;
    }
    if (y.desc && api.kar091Classify(y.desc).length && visible.includes(escapeHtml(y.desc.slice(0, 25)))) descLeaks++;
  }
  ok(leaks === 0, `no raw harmful verdict outside audit across ${checked} real calls (leaks ${leaks})`);
  ok(missingSource === 0, `every harmful card carries a source line (missing ${missingSource})`);
  ok(descLeaks === 0, `no harmful desc echoed raw (leaks ${descLeaks})`);
  ok(benignChanged === 0, `benign verdicts byte-for-byte unchanged (${benignChanged} changed)`);
  console.log(`  checked ${checked} fully-resolved real add() calls through the shipped renderer`);
}

console.log('\n=== framing spot checks ===');
{
  const y = { name: 'X', desc: 'Moon, Venus, Saturn, Mars conjunct H7.', result: 'Both native and spouse commit adultery. [Saravali 12/8]' };
  const html = buildCard(y, 'yoga-malefic');
  ok(html.includes(`<div class="yoga-desc">${escapeHtml(y.desc)}</div>`), 'clean trigger rendered exactly');
  ok(html.includes('Source · '), 'cited source shown');
  const s = kar091ParseSource('Harmful claim about disease. [7/48]');
  ok(s.source_status === 'unspecified', 'orphan verse number is not a source');
}

console.log('\n=== permanent negative tests ===');
function mutate(mut) {
  const p = '/tmp/kar091_m_' + Math.random().toString(36).slice(2) + '.html';
  fs.writeFileSync(p, mut(fs.readFileSync(HTML_PATH, 'utf8')));
  return p;
}
function gjkBounds(s) {
  const i = s.indexOf('const GJK_HOUSE_RESULTS = {');
  if (i < 0) throw new Error('GJK_HOUSE_RESULTS definition not found');
  const q = s.indexOf("'", i);
  const q2 = s.indexOf("'", q + 1);
  return { i, q, q2 };
}
// (a) emptied collector -> ExtractionError
{
  const p = mutate(s => {
    const start = s.indexOf('function collectMaleficYogas(lagna, planets, houses) {');
    let end = s.indexOf('{', start), depth = 0;
    for (; end < s.length; end++) { if (s[end] === '{') depth++; else if (s[end] === '}') { depth--; if (depth === 0) break; } }
    return s.slice(0, start) + 'function collectMaleficYogas(lagna, planets, houses) {\n  const found = [];\n  function add(){}\n  return found;\n}' + s.slice(end + 1);
  });
  try { extractVerdicts(p); ok(false, 'emptied collector should throw'); }
  catch (e) { ok(e instanceof ExtractionError, 'emptied collector -> ExtractionError'); }
  fs.unlinkSync(p);
}
// (b) syntax error -> ExtractionError
{
  const p = mutate(s => { const i = s.indexOf('function collectMaleficYogas'); return s.slice(0, i) + 'const B = {{{ ;\n' + s.slice(i); });
  try { extractVerdicts(p); ok(false, 'syntax error should throw'); }
  catch (e) { ok(e instanceof ExtractionError, 'syntax error -> ExtractionError'); }
  fs.unlinkSync(p);
}
// (c) novel literal harm -> AuditError on old manifest, REVIEW_REQUIRED after sha rebind
{
  const marker = 'function collectMaleficYogas(lagna, planets, houses) {';
  const p = mutate(s => { const i = s.indexOf(marker) + marker.length;
    return s.slice(0, i) + "\n    add('Positional','Novel','trig','The native becomes a rapist and kidnaps children.');" + s.slice(i); });
  try { auditCorpus(p, REVIEWED); ok(false, 'changed HTML should fail hash binding'); }
  catch (e) { ok(e instanceof AuditError, 'changed HTML -> AuditError (manifest bound to old sha)'); }
  const m2 = extractVerdicts(p);
  const old = JSON.parse(fs.readFileSync(REVIEWED, 'utf8'));
  const rp = '/tmp/kar091_regen.json';
  fs.writeFileSync(rp, JSON.stringify({ ...old, source_file_sha256: m2.source_file_sha256 }));
  const a2 = auditCorpus(p, rp);
  ok(a2.reviewRequired.some(e => /rapist/.test(e.text)), 'novel literal harm -> REVIEW_REQUIRED after regeneration');
  fs.unlinkSync(p); fs.unlinkSync(rp);
}
// (d) GJK container: function-returned value -> ExtractionError; plain novel literal -> REVIEW_REQUIRED
{
  const pFn = mutate(s => { const { i, q, q2 } = gjkBounds(s);
    return s.slice(0, i) + "const novelHarm = () => 'The native becomes a rapist and kidnaps children.';\n    "
      + s.slice(i, q) + 'novelHarm()' + s.slice(q2 + 1); });
  try { extractVerdicts(pFn); ok(false, 'function-returned container value should throw'); }
  catch (e) { ok(e instanceof ExtractionError, 'function-returned container value -> ExtractionError'); }
  fs.unlinkSync(pFn);

  const pLit = mutate(s => { const { q, q2 } = gjkBounds(s);
    return s.slice(0, q + 1) + 'The native becomes a rapist and kidnaps children.' + s.slice(q2); });
  const m3 = extractVerdicts(pLit);
  ok(m3.entries.some(e => /rapist/.test(e.text)), 'container-lookup literal harm IS extracted (GJK shape)');
  const old = JSON.parse(fs.readFileSync(REVIEWED, 'utf8'));
  const rp = '/tmp/kar091_regen2.json';
  fs.writeFileSync(rp, JSON.stringify({ ...old, source_file_sha256: m3.source_file_sha256 }));
  const a3 = auditCorpus(pLit, rp);
  ok(a3.reviewRequired.some(e => /rapist/.test(e.text)), 'container-lookup literal harm -> REVIEW_REQUIRED');
  fs.unlinkSync(pLit); fs.unlinkSync(rp);
}
// (e) manifest hash tampered -> AuditError
{
  const old = JSON.parse(fs.readFileSync(REVIEWED, 'utf8'));
  const rp = '/tmp/kar091_zero.json';
  fs.writeFileSync(rp, JSON.stringify({ ...old, source_file_sha256: '0'.repeat(64) }));
  try { auditCorpus(HTML_PATH, rp); ok(false, 'zeroed manifest hash should throw'); }
  catch (e) { ok(e instanceof AuditError, 'zeroed manifest hash -> AuditError'); }
  fs.unlinkSync(rp);
}
// (f) template-hole harm -> ExtractionError
{
  const p = mutate(s => { const { i, q, q2 } = gjkBounds(s);
    return s.slice(0, i) + "const novelHarm = () => 'The native becomes a rapist and kidnaps children.';\n    "
      + s.slice(i, q) + '`Existing reviewed text. ${novelHarm()}`' + s.slice(q2 + 1); });
  try { extractVerdicts(p); ok(false, 'template-hole harm should throw'); }
  catch (e) { ok(e instanceof ExtractionError, 'template-hole harm -> ExtractionError'); }
  fs.unlinkSync(p);
}
// (g) HTML/Node classifier drift -> parity assertions fail
{
  const p = mutate(s => s.replace('epilep\\w*|', ''));   // weaken HTML classifier copy only
  const mutated = fs.readFileSync(p, 'utf8');
  ok(mutated !== fs.readFileSync(HTML_PATH, 'utf8'), 'drift mutation applied');
  const par = (function () {
    const emb = embeddedClassifierSource(mutated);
    if (emb == null) return { sourceIdentical: false, behavioralIdentical: false };
    const mod = moduleClassifierSource();
    let behavioral = true;
    try {
      const htmlClassify = new Function(emb + '\nreturn kar091Classify;')();
      behavioral = JSON.stringify(htmlClassify('Vulnerable to epilepsy.')) ===
                   JSON.stringify(kar091Classify('Vulnerable to epilepsy.'));
    } catch { behavioral = false; }
    return { sourceIdentical: emb === mod, behavioralIdentical: behavioral };
  })();
  ok(!par.sourceIdentical, 'classifier drift -> source parity FAILS');
  ok(!par.behavioralIdentical, 'classifier drift -> behavioral parity FAILS');
  fs.unlinkSync(p);
}

// (h) authored [harm].join('') replacing a verdict chart-token hole -> ExtractionError
{
  const p = mutate(s => {
    const yv = s.indexOf('` Age ${age}');
    if (yv < 0) throw new Error('Yogarishta hole not found');
    return s.slice(0, yv) + '` Age ${[' + JSON.stringify('The native becomes a rapist and kidnaps children.') + "].join('')}" + s.slice(yv + 12);
  });
  try { extractVerdicts(p); ok(false, 'authored join in verdict hole should throw'); }
  catch (e) { ok(e instanceof ExtractionError, 'authored [harm].join() in chart-token hole -> ExtractionError'); }
  fs.unlinkSync(p);
}
// (i) harmful alternate desc branch -> new identity -> REVIEW_REQUIRED after rebind
{
  const p = mutate(s => {
    const t = s.indexOf("'Rahu and Mars in the Ascendant with Sun");
    const q2 = s.indexOf("'", t + 1);
    const orig = s.slice(t, q2 + 1);
    return s.replace(orig, '(houses[1].length ? ' + orig + ' : ' + JSON.stringify('The native becomes a rapist and kidnaps children.') + ')');
  });
  const mX = extractVerdicts(p);
  const old = JSON.parse(fs.readFileSync(REVIEWED, 'utf8'));
  const rp = '/tmp/kar091_descalt.json';
  fs.writeFileSync(rp, JSON.stringify({ ...old, source_file_sha256: mX.source_file_sha256 }));
  const aX = auditCorpus(p, rp);
  ok(aX.reviewRequired.some(e => /rapist/.test(e.text)), 'harmful alternate desc -> REVIEW_REQUIRED (both branches audited)');
  fs.unlinkSync(p); fs.unlinkSync(rp);
}
// (j) wrapper res changed, citation arg unchanged -> REVIEW_REQUIRED after rebind
{
  const RES = 'Brings forth a king. Jupiter in its exaltation sign Cancer area — placed at the zenith in Pisces Lagna gives supreme public authority.';
  const p = mutate(s => {
    if (!s.includes(RES)) throw new Error('ry res text not found');
    return s.replace(RES, 'The native becomes a rapist and kidnaps children.');
  });
  const mY = extractVerdicts(p);
  const old = JSON.parse(fs.readFileSync(REVIEWED, 'utf8'));
  const rp = '/tmp/kar091_ryres.json';
  fs.writeFileSync(rp, JSON.stringify({ ...old, source_file_sha256: mY.source_file_sha256 }));
  const aY = auditCorpus(p, rp);
  ok(aY.reviewRequired.some(e => /rapist/.test(e.text)), 'changed ry res with unchanged src -> REVIEW_REQUIRED');
  fs.unlinkSync(p); fs.unlinkSync(rp);
}

console.log(`\n${pass}/${pass + fail} assertions passed`);
process.exit(fail ? 1 : 0);
