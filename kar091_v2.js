// KAR-091 v2 · classification + neutral framing + explicit source model.
// Fixes the three P1 failures QA identified in v1:
//   1. classifier missed real corpus harm (sterility, epilepsy, dumbness, murder, cancer...)
//   2. wording wrapped the raw accusation in a disclaimer instead of replacing it
//   3. "Classical yoga corpus" was a fake source; unsourced severe claims were introduced anyway
const C = require('./kar091_classify.js');
const kar091Classify = C.kar091Classify;
const KAR091_HIGH_RISK = C.KAR091_HIGH_RISK;

// QA's neutral, category-level summaries. These become the PRINCIPAL consumer
// result for a harmful verdict; the raw classical wording moves to a collapsed
// audit element, it is not the headline.
const KAR091_SAFE_SUMMARY = {
  infidelity:          'possible relationship-boundary conflict or instability around fidelity',
  deception:           'a risk of evasive, inconsistent or manipulative conduct',
  childlessness:       'possible delay, difficulty or uncertainty around progeny',
  child_sex_prediction:'a sex-specific progeny prediction that this platform does not present as a personal forecast',
  reproductive_health: 'a traditional reproductive-health caution, not a fertility diagnosis',
  medical:             'a traditional health-vulnerability indication, not a medical diagnosis',
  mental_health:       'a traditional emotional or mental-wellbeing caution, not a psychiatric diagnosis',
  disability:          'a traditional physical, sensory or speech-vulnerability indication',
  addiction:           'a risk of compulsive or dependency-related patterns',
  mortality:           'a traditional longevity caution, not a lifespan prediction',
  self_harm:           'a traditional severe-distress caution requiring non-astrological support if relevant',
  violence_or_crime:   'a traditional warning about severe aggression or antisocial conduct',
  sexual_taboo_claim:  'an archaic sexual-taboo claim that this platform does not present as a personal inference',
  progeny_prediction:  'a specific traditional progeny or family-structure prediction not presented as a personal forecast',
  bodily_mark_prediction: 'a traditional bodily-mark prediction not presented as a personal forecast',
  confinement_or_legal_risk: 'a traditional warning involving confinement or legal jeopardy, not a prediction of criminal proceedings',
  identity_or_gendered_claim:'an archaic gendered or identity-related claim that this platform does not present as a personal inference',
  stigmatizing_status_claim: 'a historically stigmatizing character or social-status claim that is not presented as a personal fact',
};

// Categories severe enough that an UNSOURCED claim is withheld entirely.
const KAR091_WITHHOLD_IF_UNSOURCED = new Set([
  'reproductive_health','medical','mental_health','disability','mortality','self_harm',
  'violence_or_crime','child_sex_prediction','confinement_or_legal_risk','sexual_taboo_claim','progeny_prediction',
  'identity_or_gendered_claim','stigmatizing_status_claim',
]);

// Known classical source texts. A trailing bracket naming one of these is a
// citation even without chapter/verse numerals (e.g. "[Sambu Hora Prakasha]").
const KAR091_KNOWN_SOURCES = /\b(BPHS|Brihat Parashara|Bhava Kutuhalam|Bhavartha Ratnakara|Hora Ratnam|Jataka Desha Marga|Jataka Parijata|Phala\s?Deepika|Sambu Hora Prakasha|Saravali|Sarvartha Chintamani|Uttara Kalamrita|Brihat Jataka|Phaladeepika)\b/i;

// A real citation is a text name followed by chapter/verse numerals, OR a bare
// naming of a known classical source. A trailing bracket that is prose
// ("Classical — ...", "Also see ...", "not verified") is a NOTE, not a source.
function kar091ParseSource(originalResult) {
  const text = String(originalResult || '');
  const m = text.match(/\[([^\]]+)\]\s*$/);
  if (!m) return { source_status: 'unspecified', source: null, stripped: text.trim() };
  const inside = m[1].trim();
  const stripped = text.slice(0, m.index).trim();
  const isNote = /^(also see|see\b|not verified|note\b|cf\b|classical\s*[\u2014-]|modern:|thursday)/i.test(inside);
  const isKnownName = KAR091_KNOWN_SOURCES.test(inside);
  // A citation must NAME a recognised text. An orphan verse number like "[7/48]"
  // is not a source identifier on its own (QA P2). Numerals qualify only when a
  // known text name is also present in the bracket.
  if (!isNote && isKnownName) return { source_status: 'cited', source: inside, stripped };
  // a note-style bracket, or numerals with no named text: strip from the body,
  // but do NOT treat as a source.
  return { source_status: 'unspecified', source: null, stripped };
}

function kar091FrameV2(y) {
  const resultField = y.result ||
    (y.severity && y.severity !== 'caution' && y.severity !== 'warning' ? y.severity : '') || '';
  // Some collector entries carry the claim in DESC (3-argument add calls). The
  // renderer previously printed desc raw, so a harmful desc bypassed framing
  // entirely (QA P1). Classify desc independently; when the claim lives there,
  // frame desc as the verdict and suppress its raw rendering.
  const descCats = kar091Classify(y.desc || '');
  const desc_harmful = descCats.length > 0;
  const verdict_in = resultField ? 'result' : (desc_harmful ? 'desc' : 'result');
  const original = verdict_in === 'desc' ? (y.desc || '') : resultField;
  const harmCats = verdict_in === 'desc' ? descCats : kar091Classify(original);

  // Benign results must be preserved byte-for-byte: return the ORIGINAL, before
  // any source parsing. Calling kar091ParseSource here would strip trailing
  // citations and editorial notes from harmless verdicts (QA regression).
  if (harmCats.length === 0 && !desc_harmful) {
    return { harmful:false, harm_categories:[], source_status:'not_applicable', source:null,
             trigger:y.desc || '', confidence:null, principal:original, audit:null, withheld:false,
             desc_harmful:false, verdict_in, original };
  }

  // Source parsing and stripping apply ONLY to the safety-framed harmful branch.
  const src = kar091ParseSource(original);
  // A desc that itself classifies harmful must not be echoed as the trigger.
  const trigger = desc_harmful ? '' : (y.desc || '');

  // Principal consumer text = neutral category summaries, never the raw verdict.
  const summaries = harmCats.map(c => KAR091_SAFE_SUMMARY[c]).filter(Boolean);
  const principalCore = summaries.length ? summaries.join('; ') : 'a traditional caution';

  // Withhold an unsourced severe claim: show nothing but the neutral note and the trigger.
  const severe = harmCats.some(c => KAR091_WITHHOLD_IF_UNSOURCED.has(c));
  const withheld = severe && src.source_status === 'unspecified';

  const confidence = 'single classical indication';
  const principal = withheld
    ? `This classical combination carries ${principalCore}. The specific traditional wording is withheld here because it is a high-severity indication with no cited source in the current corpus.`
    : `This classical combination indicates ${principalCore}. It is a traditional indication, not a prediction; its expression depends on planetary dignity, cancellation yogas, dasha timing and the chart as a whole.`;

  // Raw classical wording is retained ONLY as a labelled, collapsed audit string,
  // and never for a withheld severe claim.
  const audit = withheld ? null : src.stripped;

  return { harmful:true, harm_categories:harmCats, source_status:src.source_status, source:src.source,
           trigger, confidence, principal, audit, withheld, desc_harmful, verdict_in, original };
}

module.exports = { kar091Classify, KAR091_HIGH_RISK, KAR091_SAFE_SUMMARY, kar091ParseSource, kar091FrameV2 };
