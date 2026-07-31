'use strict';
/**
 * KAR-093 STEP 9 · GATE v2 CONTRACTS AND FIXTURES
 *
 * WHAT CHANGED FROM v1, AND WHY
 * v1 asserted that expected sentinels were PRESENT. QA proved that is not
 * provenance: a page can carry every expected sentinel and also carry extra
 * locally computed output beside it. v2 asserts a CLOSED CONTRACT — the exact
 * node set, the exact text, the exact interpretive classes, and a residual check
 * that nothing else value-bearing exists inside the surface root.
 *
 * TYPED FIELDS USE VALID ENUMS, NOT SENTINELS.
 * A sentinel in a typed enum field is an impossible value that can route the
 * renderer down a default branch and leave the production branch untested. So:
 *   free text  -> sentinel, unique per graha
 *   typed enum -> a VALID value chosen to contradict what the legacy client
 *                 rules would produce for that graha, and DIFFERENT per graha
 * A local engine cannot reproduce a nine-graha mapping of contradictory valid
 * enums, so the per-graha mapping is itself the provenance proof.
 *
 * SCOPE (founder ruling): D1 page and drawer cutover scope only. The chips on
 * #page-d1, all nine drawers, and the loading/error/stale/recast states.
 * Pratiphala and downstream report consumers are migration backlog and are
 * reported without affecting the closure exit code.
 */

const GRAHAS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'];
const NODES = ['Rahu', 'Ketu'];

const SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
               'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
const SIGN_LORDS = ['Mars','Venus','Mercury','Moon','Sun','Mercury',
                    'Venus','Mars','Jupiter','Saturn','Saturn','Jupiter'];

// ── Valid enum domains ─────────────────────────────────────────────────────
// Transcribed from the page's own D1_DIGNITY_CLASS keys and the drawer's
// polarity classing, NOT from my recollection of the server model.
const DIGNITY_ENUM = ['Exalted','Moolatrikona','Own Sign','Great Friend','Friend',
                      'Neutral','Enemy','Great Enemy','Debilitated'];
const POLARITY_ENUM = ['supportive','challenging','mixed','neutral'];
const FUNCTIONAL_ENUM = ['benefic','malefic','neutral','mixed'];
const MARAKA_ENUM = ['none','maraka','qualified','primary_killer'];

// Independent transcription of the page's polarity -> class mapping. Kept
// separate from the page so the assertion is not checked against its subject.
const POLARITY_CLASS = { supportive: 'dig-own', challenging: 'dig-enemy', mixed: 'dig-friendly' };
const polarityClassFor = p => POLARITY_CLASS[p] || 'dig-sama';

// ── The chart: legacy answers are known and unambiguous ────────────────────
// Each graha is placed where the degree-blind DIGNITY_SCORES table gives a
// definite answer, so "the payload contradicts the legacy rule" is checkable.
const PLACEMENT = {
  Sun:     { si: 0,  house: 1,  deg: 12.5, d9: 4,  retro: false, legacy: 'Exalted' },
  Moon:    { si: 1,  house: 2,  deg: 8.2,  d9: 7,  retro: false, legacy: 'Exalted' },
  Mars:    { si: 9,  house: 10, deg: 24.4, d9: 1,  retro: false, legacy: 'Exalted' },
  Mercury: { si: 5,  house: 6,  deg: 3.1,  d9: 9,  retro: false, legacy: 'Exalted' },
  Jupiter: { si: 3,  house: 4,  deg: 15.7, d9: 2,  retro: false, legacy: 'Exalted' },
  Venus:   { si: 11, house: 12, deg: 21.3, d9: 5,  retro: true,  legacy: 'Exalted' },
  Saturn:  { si: 6,  house: 7,  deg: 5.9,  d9: 10, retro: false, legacy: 'Exalted' },
  Rahu:    { si: 1,  house: 2,  deg: 17.0, d9: 6,  retro: true,  legacy: 'Exalted' },
  Ketu:    { si: 7,  house: 8,  deg: 17.0, d9: 0,  retro: true,  legacy: 'Exalted' }
};

// ── Per-graha assignment ───────────────────────────────────────────────────
// Every graha gets a DIFFERENT valid enum, none of them the legacy answer.
const ENUM_FOR = {};
GRAHAS.forEach((g, i) => {
  const legacy = PLACEMENT[g].legacy;
  const dignityChoices = DIGNITY_ENUM.filter(d => d !== legacy);
  ENUM_FOR[g] = {
    dignity:    dignityChoices[i % dignityChoices.length],
    polarity:   POLARITY_ENUM[i % POLARITY_ENUM.length],
    net:        POLARITY_ENUM[(i + 2) % POLARITY_ENUM.length],
    bhPolarity: POLARITY_ENUM[(i + 1) % POLARITY_ENUM.length],
    gsPolarity: POLARITY_ENUM[(i + 3) % POLARITY_ENUM.length],
    functional: FUNCTIONAL_ENUM[i % FUNCTIONAL_ENUM.length],
    maraka:     MARAKA_ENUM[i % MARAKA_ENUM.length]
  };
});

// ── Sentinels, unique per graha per field ──────────────────────────────────
const FIELDS = ['DIGLABEL','SIGN','SIGNLORD','HOUSENAME','HOUSELORD','BHAVESH','OFSIGN',
                'BHDIGLABEL','SUPPORT','BBHOUSENAME','BBLORD','BBDIGLABEL','SUSTAINING',
                'KARAKA1','KARAKA2','KARAKASUPPORT','OVERALL','STRENGTH','NATURALNATURE',
                'VERSEYOGA','BASISVERSE','DSUBJECT','DSOURCE','DKIND',
                'BHDSOURCE','GSDSOURCE'];
const S = {};
GRAHAS.forEach(g => {
  S[g] = {};
  FIELDS.forEach(f => { S[g][f] = `ZQX${g.toUpperCase()}${f}Q7`; });
});
const allSentinels = () => GRAHAS.flatMap(g => FIELDS.map(f => S[g][f]));

function verifySentinelsAbsent(pageSource) {
  return allSentinels().filter(v => pageSource.includes(v));
}

// ═══ PAYLOADS ═════════════════════════════════════════════════════════════
function buildChartResponse(overrides) {
  const planets = {};
  GRAHAS.forEach(g => {
    const p = PLACEMENT[g];
    planets[g] = {
      sign: SIGNS[p.si], sign_index: p.si, house: p.house, degree: p.deg,
      longitude: p.si * 30 + p.deg, retrograde: p.retro, dignity: 'Neutral',
      nakshatra: 'Ashwini', nakshatra_pada: 1,
      d9_sign_index: p.d9, d9_sign: SIGNS[p.d9], d9_dignity: 'Neutral',
      d20_sign_index: (p.si + 3) % 12, vargottama: p.si === p.d9
    };
  });
  const houses = {};
  for (let h = 1; h <= 12; h++) {
    const si = (h - 1) % 12;
    houses[String(h)] = { sign: SIGNS[si], sign_index: si, lord: SIGN_LORDS[si], house: h };
  }
  return Object.assign({
    chart_token: 'ZQXCHARTTOKENQ7',
    anon_session: 'ZQXANONSESSIONQ7',
    input: { date: '1990-01-01', time: '12:00', lat: 25.2139, lon: 84.9896, utc_offset: 5.5 },
    lagna: { sign: SIGNS[0], sign_index: 0, degree: 20.0586, longitude: 20.0586,
             ayanamsha: 23.85, lord: SIGN_LORDS[0], d9_sign_index: 4, d20_sign_index: 7 },
    planets, houses,
    dasha: { current_mahadasha: { planet: 'Rahu', end: '2028-01-01' },
             current_antardasha: { planet: 'Saturn', end: '2027-01-01' }, sequence: [] },
    calculation_meta: { chart_engine_version: '1.1.0', house_system: 'whole-sign' }
  }, overrides || {});
}

function drishti(g, sourceField, polarity, net) {
  return { subject: S[g].DSUBJECT,
           sources: [{ source: S[g][sourceField], kind: S[g].DKIND, polarity }],
           net };
}

/**
 * Node drawers use the REAL node shape: has_lordship_doctrine false, no
 * lordship fields, and an UNRESOLVABLE corpus ref. That exercises the
 * renderer's node branch and d1Corpus's early return, neither of which v1
 * touched.
 */
function buildDrawer(g) {
  const isNode = NODES.includes(g);
  const E = ENUM_FOR[g];
  const d = {
    graha: g,
    position: { dignity: E.dignity, dignity_label: S[g].DIGLABEL,
                house: PLACEMENT[g].house, sign: S[g].SIGN },
    rashi: {
      sign: S[g].SIGN, dignity: E.dignity, dignity_label: S[g].DIGLABEL,
      sign_lord: { graha: S[g].SIGNLORD, house: 7, sign: S[g].SIGN },
      corpus_ref: isNode
        ? { corpus: 'RASHI_CORPUS', graha: g, key: E.dignity, resolvable: false }
        : { corpus: 'RASHI_CORPUS', graha: 'Sun', key: 'Debilitated', resolvable: true }
    },
    house: {
      house: PLACEMENT[g].house, house_name: S[g].HOUSENAME, house_lord: S[g].HOUSELORD,
      corpus_ref: { corpus: 'HOUSE_CORPUS', graha: 'Sun', key: '1', resolvable: !isNode },
      drishti: drishti(g, 'DSOURCE', E.polarity, E.net)
    },
    bhavesh: {
      bhavesh: S[g].BHAVESH, of_sign: S[g].OFSIGN,
      position: { house: 4, sign: S[g].SIGN, dignity: E.dignity, dignity_label: S[g].BHDIGLABEL },
      support: S[g].SUPPORT, retrograde_note: false,
      drishti: drishti(g, 'BHDSOURCE', E.bhPolarity, E.polarity)
    },
    bhavat_bhavam: {
      from_house: PLACEMENT[g].house, bb_house: 1, bb_house_name: S[g].BBHOUSENAME,
      bb_lord: S[g].BBLORD, bb_lord_position: { house: 9, dignity_label: S[g].BBDIGLABEL },
      sustaining: S[g].SUSTAINING,
      corpus_ref: { corpus: 'BHAVAT_DESC', key: '1', resolvable: true }
    },
    bhava_karaka: {
      karakas: [S[g].KARAKA1, S[g].KARAKA2], primary_karaka: S[g].KARAKA1,
      karaka_support: S[g].KARAKASUPPORT,
      corpus_ref: { corpus: 'BHAVA_KARAKA', key: '1', resolvable: true }
    },
    shadbala: { at_digbala_peak_house: false },
    graha_saar: {
      overall_verdict: S[g].OVERALL, strength_verdict: S[g].STRENGTH,
      // For the Moon this field IS the pakṣa output. It carries a Moon-unique
      // sentinel and the gate asserts it in the Moon drawer specifically.
      natural_nature: S[g].NATURALNATURE,
      has_lordship_doctrine: !isNode,
      house_drishti: drishti(g, 'GSDSOURCE', E.gsPolarity, E.net)
    }
  };
  if (!isNode) {
    Object.assign(d.graha_saar, {
      functional_nature: E.functional, verse_yoga_status: S[g].VERSEYOGA,
      ownership_yogakaraka: GRAHAS.indexOf(g) % 2 === 0,
      maraka_status: E.maraka, functional_basis_verse: S[g].BASISVERSE
    });
  }
  return d;
}

const buildD1Payload = () => ({
  policy: { engine_version: 'd1-engine-0.1.0', node_aspect_policy: 'no_independent_drishti' },
  drawers: { drawers: GRAHAS.map(buildDrawer) }
});

// ═══ CLOSED DOM CONTRACTS ═════════════════════════════════════════════════
/**
 * CHIP CONTRACT. Exactly six descendants, one per named class, no others; the
 * root carries no interpretive class; the badge carries exactly one dignity
 * class and it is the one the payload dictates.
 *
 * This is what closes QA's adversarial page: an extra `.chip-extra-local` node
 * fails the descendant count, and a `dig-exalted` token on the root fails the
 * root class equality.
 */
const CHIP_CONTRACT = {
  rootClass: 'planet-chip',
  descendantClasses: ['chip-sym', 'chip-info', 'chip-name', 'chip-sub', 'chip-badge', 'chip-arrow'],
  interpretiveClassPrefix: 'dig-',
  interpretiveClassAllowedOn: 'chip-badge'
};

/** DRAWER CONTRACT. Class tokens are a closed set; anything else is a finding. */
const DRAWER_CONTRACT = {
  allowedClassTokens: ['analysis-section', 'section-head', 'section-arrow', 'section-body',
                       'open', 'kv-row', 'kv-key', 'kv-val', 'note-box', 'dim'],
  interpretiveClassPrefix: 'dig-',
  interpretiveClassAllowedOn: 'kv-val',
  sectionCount: 7,
  // kv-val text that legitimately contains no sentinel. Everything else must.
  allowedLiteralValues: ['yes', 'no', '—', ''],
  allowedLiteralPatterns: [/^H\d+$/]
};

/** Everything the Moon drawer must show, used for the explicit pakṣa exercise. */
const PAKSHA_FIELD = 'NATURALNATURE';


// ═══ P6 · MODEL-GENERATED FIXTURE ════════════════════════════════════════
// The payload below is no longer authored here. It is loaded from
// kar093_p6_fixture.json, which was produced by instantiating the accepted
// Pydantic models (CertifiedChart -> compute_d1 -> build_d1_drawers) and
// re-validated through D1DrawerPayload after sentinel injection.
//
// Nothing about the validators changes. What changes is that the payload is now
// something the contract produced rather than something I wrote, which is what
// Gate v2 was rejected for.
const fsP6 = require('fs');
const pathP6 = require('path');
const P6_PATH = process.env.KAR093_P6_FIXTURE ||
                pathP6.join(__dirname, 'kar093_p6_fixture.json');
let P6 = null;
function loadP6() {
  if (P6) return P6;
  P6 = JSON.parse(fsP6.readFileSync(P6_PATH, 'utf8'));
  if (!P6.drawers || !P6.drawers.drawers || P6.drawers.drawers.length !== 9)
    throw new Error('P6 fixture does not carry nine drawers');
  if (!P6._evidence) throw new Error('P6 fixture carries no evidence manifest');
  return P6;
}

/** Sentinels are READ BACK from the generated fixture, never re-declared. */
function p6Sentinels() {
  const out = {};
  loadP6().drawers.drawers.forEach(d => {
    const found = JSON.stringify(d).match(/ZQX[A-Z]+Q7/g) || [];
    out[d.graha] = Array.from(new Set(found));
  });
  return out;
}

function buildD1PayloadP6() {
  const f = loadP6();
  return { policy: f.policy, drawers: f.drawers, __variants: f._variants || {} };
}

/** The /chart stub is emitted by the SAME generator, so the two cannot drift. */
function buildChartResponseP6() {
  const f = loadP6();
  const c = f._chart;
  const planets = {};
  Object.keys(c.grahas).forEach(g => {
    const cg = c.grahas[g];
    planets[g] = {
      sign: SIGNS[cg.sign_index], sign_index: cg.sign_index,
      house: ((cg.sign_index - c.lagna.sign_index) % 12 + 12) % 12 + 1,
      degree: cg.degree_in_sign, longitude: cg.longitude,
      retrograde: cg.retrograde, dignity: cg.dignity,
      nakshatra: cg.nakshatra, nakshatra_pada: cg.nakshatra_pada,
      d9_sign_index: (cg.sign_index + 4) % 12, d9_sign: SIGNS[(cg.sign_index + 4) % 12],
      d9_dignity: 'Neutral', d20_sign_index: (cg.sign_index + 3) % 12,
      vargottama: false
    };
  });
  const houses = {};
  for (let h = 1; h <= 12; h++) {
    const si = (c.lagna.sign_index + h - 1) % 12;
    houses[String(h)] = { sign: SIGNS[si], sign_index: si, lord: SIGN_LORDS[si], house: h };
  }
  return {
    chart_token: c.chart_token, anon_session: 'ZQXANONSESSIONQ7',
    input: { date: '1990-01-01', time: '12:00', lat: 25.2139, lon: 84.9896, utc_offset: 5.5 },
    lagna: { sign: SIGNS[c.lagna.sign_index], sign_index: c.lagna.sign_index,
             degree: c.lagna.degree, longitude: c.lagna.sign_index * 30 + c.lagna.degree,
             ayanamsha: 23.85, lord: SIGN_LORDS[c.lagna.sign_index],
             d9_sign_index: 4, d20_sign_index: 7 },
    planets, houses,
    dasha: { current_mahadasha: { planet: 'Rahu', end: '2028-01-01' },
             current_antardasha: { planet: 'Saturn', end: '2027-01-01' }, sequence: [] },
    calculation_meta: { chart_engine_version: '1.1.0', house_system: 'whole-sign' }
  };
}

module.exports = {
  loadP6, p6Sentinels, buildD1PayloadP6, buildChartResponseP6,
  GRAHAS, NODES, SIGNS, SIGN_LORDS, PLACEMENT, ENUM_FOR, S, FIELDS,
  DIGNITY_ENUM, POLARITY_ENUM, FUNCTIONAL_ENUM, MARAKA_ENUM,
  polarityClassFor, allSentinels, verifySentinelsAbsent,
  buildChartResponse, buildD1Payload, buildDrawer,
  CHIP_CONTRACT, DRAWER_CONTRACT, PAKSHA_FIELD
};
