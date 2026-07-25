// KAR-091 · reviewed-manifest regeneration tool v3.
//
// NEVER auto-approves. Dispositions (harmful AND benign) carry forward by full
// content hash. Any NEW or CHANGED verdict stays undispositioned, so the audit
// fails with REVIEW_REQUIRED until a human adds a ruling. Carried harmful
// entries whose classifier categories changed are reported as drift and the
// tool exits non-zero: the stored category decision must be re-confirmed.
const fs = require('fs');
const { extractVerdicts } = require('./kar091_extract_verdicts.js');
const { kar091Classify } = require('./kar091_classify.js');
const { fullHash, entityKey } = require('./kar091_audit.js');

const htmlPath = process.argv[2] || 'newphalit.html';
const oldPath = process.argv[3] || 'kar091_reviewed_manifest.json';
const outPath = process.argv[4] || oldPath;

const m = extractVerdicts(htmlPath);
let old = { dispositions: {} };
try { old = JSON.parse(fs.readFileSync(oldPath, 'utf8')); } catch {}

const dispositions = {};
const newEntries = [];
const drift = [];
for (const e of m.entries) {
  const h = entityKey(e);
  const prev = old.dispositions && old.dispositions[h];
  if (!prev) { newEntries.push({ ...e, cats: kar091Classify(e.text) }); continue; }
  const cats = kar091Classify(e.text);
  if (prev.disposition === 'harmful' && JSON.stringify(cats) !== JSON.stringify(prev.categories)) {
    drift.push({ text: e.text, stored: prev.categories, computed: cats });
  }
  if (prev.disposition === 'benign_reviewed' && cats.length) {
    // classifier now flags it: promote is NOT automatic — surface for re-ruling
    drift.push({ text: e.text, stored: [], computed: cats });
  }
  dispositions[h] = prev;
}

fs.writeFileSync(outPath, JSON.stringify({
  manifest_version: '3.0.0',
  reviewed_at: old.reviewed_at || null,
  regenerated_at: new Date().toISOString().slice(0, 10),
  review_note: old.review_note || '',
  source_file_sha256: m.source_file_sha256,
  dispositions,
}, null, 1));

console.error(`bound to ${m.source_file_sha256.slice(0, 12)} | carried ${Object.keys(dispositions).length} | NEW UNDISPOSITIONED ${newEntries.length} | drift ${drift.length}`);
newEntries.slice(0, 20).forEach(e => console.error(`  NEW [${e.fn}]${e.cats.length ? ' <classifier: ' + e.cats.join(',') + '>' : ''} ${e.text.slice(0, 75)}`));
drift.slice(0, 20).forEach(d => console.error(`  DRIFT stored=[${d.stored}] computed=[${d.computed}] ${d.text.slice(0, 60)}`));
if (newEntries.length || drift.length) process.exit(1);
