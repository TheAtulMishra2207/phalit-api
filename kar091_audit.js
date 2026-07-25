// KAR-091 · corpus safety audit v3.
// Every verdict must carry an explicit reviewed disposition. The audit fails on:
//   - extraction failure (fail-closed extractor throws)
//   - HTML-hash mismatch with the reviewed manifest
//   - any entry without a disposition (REVIEW_REQUIRED)
//   - any divergence between the classifier's categories and the stored harmful
//     disposition, in EITHER direction (classifier drift detection)
const fs = require('fs');
const crypto = require('crypto');
const { extractVerdicts } = require('./kar091_extract_verdicts.js');
const { kar091Classify } = require('./kar091_classify.js');

function fullHash(s) { return crypto.createHash('sha256').update(String(s).trim()).digest('hex'); }
// Entry identity includes the normalized source of every dynamic hole, so a
// change INSIDE a ⟨dyn⟩ expression invalidates the disposition even when the
// resolved text is unchanged.
function entityKey(e) { return fullHash(e.identity != null ? e.identity : e.text); }
class AuditError extends Error {}

function auditCorpus(htmlPath, reviewedManifestPath) {
  const manifest = extractVerdicts(htmlPath);
  const reviewed = JSON.parse(fs.readFileSync(reviewedManifestPath, 'utf8'));
  if (!reviewed.source_file_sha256 || reviewed.source_file_sha256 !== manifest.source_file_sha256) {
    throw new AuditError('reviewed manifest bound to sha ' + String(reviewed.source_file_sha256).slice(0, 12) +
      ' but file under audit is ' + manifest.source_file_sha256.slice(0, 12) + '; re-review required');
  }
  const dispositions = reviewed.dispositions || {};
  const harmful = [], reviewedBenign = [], reviewRequired = [], drift = [];
  for (const e of manifest.entries) {
    const cats = kar091Classify(e.text);
    const d = dispositions[entityKey(e)];
    if (!d) { reviewRequired.push({ ...e, cats }); continue; }
    if (d.disposition === 'harmful') {
      if (!cats.length) drift.push({ ...e, stored: d.categories, computed: cats, kindOfDrift: 'classifier no longer flags stored-harmful entry' });
      else if (JSON.stringify(cats) !== JSON.stringify(d.categories)) drift.push({ ...e, stored: d.categories, computed: cats, kindOfDrift: 'category set changed' });
      harmful.push({ ...e, cats });
    } else if (d.disposition === 'benign_reviewed') {
      if (cats.length) drift.push({ ...e, stored: [], computed: cats, kindOfDrift: 'classifier now flags reviewed-benign entry (re-disposition required)' });
      reviewedBenign.push(e);
    } else {
      reviewRequired.push({ ...e, cats });
    }
  }
  return { manifest, harmful, reviewedBenign, reviewRequired, drift };
}

module.exports = { auditCorpus, fullHash, entityKey, AuditError };

if (require.main === module) {
  const htmlPath = process.argv[2] || 'newphalit.html';
  const reviewedPath = process.argv[3] || 'kar091_reviewed_manifest.json';
  let r;
  try { r = auditCorpus(htmlPath, reviewedPath); }
  catch (e) { console.error('AUDIT FAILED (fail-closed): ' + e.message); process.exit(2); }
  console.error(`verdicts ${r.manifest.entries.length} | harmful ${r.harmful.length} | benign_reviewed ${r.reviewedBenign.length} | REVIEW_REQUIRED ${r.reviewRequired.length} | drift ${r.drift.length}`);
  if (r.reviewRequired.length || r.drift.length) {
    r.reviewRequired.slice(0, 10).forEach(e => console.error('  REVIEW: [' + e.fn + '] ' + e.text.slice(0, 75)));
    r.drift.slice(0, 10).forEach(e => console.error('  DRIFT (' + e.kindOfDrift + '): ' + e.text.slice(0, 60)));
    process.exit(1);
  }
  console.error('corpus audit passed: full explicit dispositions, no drift');
}
