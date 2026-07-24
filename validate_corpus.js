#!/usr/bin/env node
/*
 * validate_corpus.js — build-time guard for newphalit.html trait corpora.
 *
 * KAR-088. A malformed corpus value must fail the build, not render as garbage
 * like the "Ip" artifact. The lesson that shaped this validator: Array.isArray
 * is insufficient, because a single ['text','p'] pair is itself an array. So a
 * house slot that is a BARE PAIR instead of a LIST of pairs is the exact defect
 * class, and the validator must reject it. Regex-scanning individual pairs (the
 * first version) could not see that structural error. This version parses the
 * real GBN / GRN / GP_TRAITS objects out of the file and validates their shape
 * with the same schema the browser's isTraitList uses.
 *
 * Run:  node validate_corpus.js newphalit.html
 * Exit non-zero on any violation; intended as a CI / pre-deploy gate.
 */
"use strict";
const fs = require("fs");

const path = process.argv[2] || "newphalit.html";
const js = fs.readFileSync(path, "utf8");
const problems = [];

function extractObject(name) {
  const m = js.search(new RegExp("const\\s+" + name + "\\s*=\\s*\\{"));
  if (m < 0) return null;
  let i = js.indexOf("{", m), depth = 0;
  for (let j = i; j < js.length; j++) {
    if (js[j] === "{") depth++;
    else if (js[j] === "}") { depth--; if (depth === 0) return js.slice(i, j + 1); }
  }
  return null;
}

function loadObject(name) {
  const blob = extractObject(name);
  if (blob == null) { problems.push(`${name}: corpus object not found`); return null; }
  try { return eval("(" + blob + ")"); }
  catch (e) { problems.push(`${name}: could not parse (${e.message})`); return null; }
}

const TRAIT_TYPES = new Set(["p", "c", "n"]);

// KAR-088-CI. The exact GP_TRAITS slots that are empty by design in the accepted
// corpus (nodes own no signs and this corpus leaves their friend/enemy slots
// empty). Derived from the accepted corpus and pinned here, so any OTHER slot
// going empty — including Rahu/Ketu under Exalted or Debilitated, which DO carry
// content — fails CI as content loss.
const ALLOWED_EMPTY_GP_TRAITS = new Set([
  "Moolatrikona.Ketu",
  "Own Sign (Swa).Ketu",
  "Friendly Sign (Mitra).Rahu",
  "Friendly Sign (Mitra).Ketu",
  "Enemy Sign (Shatru).Rahu",
  "Enemy Sign (Shatru).Ketu",
]);
function isTraitPair(v) {
  return Array.isArray(v) && v.length === 2 &&
         typeof v[0] === "string" && v[0].trim().length > 0 &&
         TRAIT_TYPES.has(v[1]);
}
function assertTraitList(v, path, allowEmpty) {
  if (allowEmpty && Array.isArray(v) && v.length === 0) return;  // legitimately empty (e.g. nodes)
  if (!Array.isArray(v) || v.length === 0 || !v.every(isTraitPair)) {
    problems.push(`${path} must be a non-empty list of [text,type] pairs`);
    return;
  }
  // truncated-fragment guard: a 1-2 char trait text is the "Ip" signature.
  v.forEach(([t], i) => {
    if (/^[A-Za-z]{1,2}$/.test(t.trim()))
      problems.push(`${path}[${i}] suspected truncated fragment: ${JSON.stringify(t)}`);
  });
}

// ── GBN / GRN: planet -> 12 house/sign slots -> list of pairs ────────────────
for (const name of ["GBN", "GRN"]) {
  const obj = loadObject(name);
  if (!obj) continue;
  for (const [planet, slots] of Object.entries(obj)) {
    if (!Array.isArray(slots) || slots.length !== 12) {
      problems.push(`${name}.${planet} must contain 12 entries; found ${Array.isArray(slots) ? slots.length : typeof slots}`);
      continue;
    }
    slots.forEach((traits, i) => {
      // GBN.Saturn[0] is a conditional row: a list of pairs, still valid shape.
      assertTraitList(traits, `${name}.${planet}[${i}]`, false);
    });
  }
}

// ── GP_TRAITS: dignity -> planet -> list of pairs ────────────────────────────
{
  const obj = loadObject("GP_TRAITS");
  if (obj) {
    // KAR-088-CI. Empty is legitimate ONLY for the specific node slots that
    // are empty by design in the accepted corpus: nodes own no signs, so they
    // have no moolatrikona / own-sign entries, and this corpus also leaves
    // their friend/enemy slots empty. But Rahu and Ketu DO carry content under
    // Exalted and Debilitated, so "node" alone is too broad a permission — it
    // would let that content be erased silently. The exception is therefore an
    // exact allowlist of slot paths, not a per-planet flag.
    for (const [dignity, planets] of Object.entries(obj)) {
      for (const [planet, traits] of Object.entries(planets)) {
        const allowEmpty = ALLOWED_EMPTY_GP_TRAITS.has(`${dignity}.${planet}`);
        assertTraitList(traits, `GP_TRAITS.${JSON.stringify(dignity)}.${planet}`, allowEmpty);
      }
    }
  }
}

// ── KAR-088 site guards ──────────────────────────────────────────────────────
// The single-pair selector must not return.
if (/GBN\['Saturn'\]\[0\]\[[01]\]/.test(js) || /GBN\.Saturn\[0\]\[[01]\]\s*[:;]/.test(js))
  problems.push("KAR-088 regression: a single Saturn pair is selected directly");

// Exactly one helper definition and exactly two production call sites.
const helperDefs = (js.match(/function\s+saturnFirstHouseTraits\s*\(/g) || []).length;
const helperMentions = (js.match(/\bsaturnFirstHouseTraits\s*\(/g) || []).length;
const helperCalls = helperMentions - helperDefs;
if (helperDefs !== 1)
  problems.push(`KAR-088: expected exactly one helper definition; found ${helperDefs}`);
if (helperCalls !== 2)
  problems.push(`KAR-088: expected exactly two production call sites (drawer + planetCorpus); found ${helperCalls}`);
// Assert the two sites individually, not only by count.
if (!/if\s*\(pn==='Saturn'\s*&&\s*p\.house===1\)\s*traits\s*=\s*saturnFirstHouseTraits\(p\.sign_index\)/.test(js))
  problems.push("KAR-088: drawer (getGBNHtml) does not resolve Saturn-H1 through the helper");
if (!/if\s*\(pn\s*===\s*'Saturn'\s*&&\s*h\s*===\s*1\)\s*gbnRaw\s*=\s*saturnFirstHouseTraits\(lagnaIdx\)/.test(js))
  problems.push("KAR-088: planetCorpus does not resolve Saturn-H1 through the helper");

// The unsourced fabricated trait must not reappear as a value.
if (/\[\s*['"]Favored by fortune['"]/.test(js))
  problems.push("KAR-088: fabricated trait 'Favored by fortune' still present as a value");

if (problems.length) {
  console.error("CORPUS VALIDATION FAILED");
  for (const p of problems) console.error("  - " + p);
  process.exit(1);
}
console.log(`corpus validation passed (helper defs ${helperDefs}, call sites ${helperCalls})`);
