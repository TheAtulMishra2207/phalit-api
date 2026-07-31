#!/usr/bin/env node
'use strict';
/**
 * KAR-093 · PRODUCT FIX v5 · D1 chip cutover, recast lifecycle, marker contract
 * Usage: node apply_product_fix.js <in.html> <out.html>
 *
 * v1 was rejected for two runtime regressions and incomplete markers. What
 * changed and why:
 *
 *  1. v1 inserted `await d1Prepare(...)` immediately after `++_d1DrawerEpoch`,
 *     which sat BEFORE the existing `_d1PayloadCache.clear()`. The freshly
 *     seeded payload was therefore evicted and the drawer refetched, so one
 *     chart cost two /d1/prepare calls and the two results could disagree one
 *     click apart. I anchored on a string without reading the three lines that
 *     followed it. The seed now happens AFTER the cache clear and the cache is
 *     never cleared behind it.
 *
 *  2. The same await sat before closeDrawer() and renderChartView(), so during
 *     a recast the old drawer, overlay and chart stayed visible while the new
 *     chart_token was already global. That reopened the stale-interpretation
 *     window closed in step 6b v3, and blocked the primary chart render on D1
 *     latency. The chart now renders immediately with unknown badges and the
 *     seed is applied asynchronously under a chart-token AND epoch guard.
 *
 *  3. Markers covered the chip only, so the drawer would have needed a second
 *     HTML change and a second KAR-091 rebind, defeating the one-rebind
 *     rationale. Markers now cover the drawer leaves, the dṛṣṭi block and the
 *     corpus output, and the composite chip position is split into granular
 *     fields.
 *
 * Every replacement is EXACT-ONCE and throws otherwise.
 */
const fs = require('fs');
const crypto = require('crypto');

function patch(src, from, to, label) {
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error(`patch "${label}" matched ${n} times, expected exactly 1`);
  exactOnce++;
  return src.replace(from, to);
}
/** Replace a whole span delimited by two unique markers, inclusive. */
function replaceSpan(src, startMark, endMark, to, label) {
  if (src.split(startMark).length - 1 !== 1) throw new Error(`span "${label}": start marker not unique`);
  const s = src.indexOf(startMark);
  const e = src.indexOf(endMark, s);
  if (e === -1) throw new Error(`span "${label}": end marker not found after start`);
  if (src.indexOf(endMark, e + endMark.length) !== -1 && label !== 'drawer renderer')
    throw new Error(`span "${label}": end marker not unique`);
  return src.slice(0, s) + to + src.slice(e + endMark.length);
}

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) { console.error('usage: node apply_product_fix.js <in.html> <out.html>'); process.exit(2); }
let src = fs.readFileSync(inPath, 'utf8');
const before = crypto.createHash('sha256').update(fs.readFileSync(inPath)).digest('hex');
let n = 0, exactOnce = 0, bulk = 0;
const step = (fn) => { src = fn(src); n++; };

// ── 1 · D1 seed state and the guarded async seeder ─────────────────────────
step(s => patch(s,
  "let _d1DrawerEpoch = 0;",
  "let _d1DrawerEpoch = 0;\n" +
  "// KAR-093: TWO generations, deliberately separate.\n" +
  "//   _d1ChartEpoch  bumps only when a new chart is committed.\n" +
  "//   _d1DrawerEpoch bumps on every drawer OPEN and every CLOSE.\n" +
  "// v2 reused the drawer counter for the badge seed, so merely clicking a chip\n" +
  "// while the seed was in flight discarded a perfectly current payload and left\n" +
  "// the chip unknown beside a populated drawer. Clicking must not invalidate the\n" +
  "// chart's own data, and closing must invalidate a pending drawer write.\n" +
  "let _d1ChartEpoch = 0;\n" +
  "let _d1Seed = null;\n" +
  "\n" +
  "function _d1BadgeFor(pn) {\n" +
  "  const d = (_d1Seed && _d1Seed.drawers && _d1Seed.drawers.drawers || [])\n" +
  "              .find(x => x.graha === pn) || null;\n" +
  "  return d ? { label: d.position.dignity_label || '\\u2014',\n" +
  "               cls: D1_DIGNITY_CLASS[d.position.dignity] || '' }\n" +
  "           : { label: '\\u2014', cls: '' };\n" +
  "}\n" +
  "\n" +
  "function _applyD1ChipBadges() {\n" +
  "  document.querySelectorAll('#planet-list .planet-chip').forEach(chip => {\n" +
  "    const pn = chip.getAttribute('data-d1-graha');\n" +
  "    const badge = chip.querySelector('.chip-badge');\n" +
  "    if (!pn || !badge) return;\n" +
  "    const b = _d1BadgeFor(pn);\n" +
  "    badge.className = b.cls ? ('chip-badge ' + b.cls) : 'chip-badge';\n" +
  "    badge.textContent = b.label;\n" +
  "  });\n" +
  "}\n" +
  "\n" +
  "// THE SINGLE ACCEPTANCE POINT. Every successful d1Prepare for the CURRENT\n" +
  "// chart lands here, whether it came from the initial seed or from a drawer\n" +
  "// click that happened to be the first successful request. One path in means\n" +
  "// the chips and the drawer can never be fed by different payloads.\n" +
  "function _acceptD1Payload(token, chartEpoch, payload) {\n" +
  "  if (!payload) return false;\n" +
  "  if (chartEpoch !== _d1ChartEpoch) return false;\n" +
  "  if (!chartData || chartData.chart_token !== token) return false;\n" +
  "  _d1Seed = payload;\n" +
  "  _applyD1ChipBadges();\n" +
  "  return true;\n" +
  "}\n" +
  "\n" +
  "async function _seedD1Badges(token, chartEpoch) {\n" +
  "  let payload = null;\n" +
  "  try { payload = await d1Prepare(token); } catch (e) { payload = null; }\n" +
  "  _acceptD1Payload(token, chartEpoch, payload);\n" +
  "}",
  'seed state, split epochs, single acceptance point'));

// ── 2 · commit sequence: invalidate, render, THEN seed ─────────────────────
step(s => patch(s,
  "    ++_d1DrawerEpoch;\n" +
  "    _d1PayloadCache.clear();\n" +
  "    closeDrawer();\n" +
  "    renderChartView();",
  "    ++_d1DrawerEpoch;\n" +
  "    ++_d1ChartEpoch;\n" +
  "    _d1PayloadCache.clear();   // discard the PREVIOUS chart before seeding the new one\n" +
  "    _d1Seed = null;            // never carry a previous chart's reading\n" +
  "    closeDrawer();             // stale drawer dies immediately, not after a network round trip\n" +
  "    renderChartView();         // chart is visible before /d1/prepare is even sent\n" +
  "    _seedD1Badges(chartData.chart_token, _d1ChartEpoch);   // not awaited; guarded on arrival",
  'commit sequence'));

// ── 3 · chip badge from the payload, granular markers ──────────────────────
step(s => patch(s,
  "    const score   = getScore(pn, p.sign_index);\n" +
  "    const label   = getDignityLabel(pn, score);\n" +
  "    const digCls  = getDignityClass(score);\n",
  "    // KAR-093: dignity is server-authored. No client scoring on this surface.\n" +
  "    const _b      = _d1BadgeFor(pn);\n" +
  "    const label   = _b.label;\n" +
  "    const digCls  = _b.cls;\n",
  'chip badge from payload'));

step(s => patch(s,
  "    chip.className= 'planet-chip';",
  "    chip.className= 'planet-chip';\n" +
  "    chip.setAttribute('data-d1-graha', pn);",
  'chip root graha marker'));

step(s => patch(s,
  "      <span class=\"chip-sym\">${P_SYM[pn]}</span>\n" +
  "      <div class=\"chip-info\">\n" +
  "        <div class=\"chip-name\">${P_SA[pn]} · ${pn}</div>\n" +
  "        <div class=\"chip-sub\">${p.sign} · H${p.house} · ${p.degree.toFixed(1)}°${p.retrograde?' · ℞':''}</div>\n" +
  "      </div>\n" +
  "      <span class=\"chip-badge ${digCls}\">${label}</span>\n" +
  "      <span class=\"chip-arrow\">›</span>`;",
  "      <span class=\"chip-sym\" data-d1-literal=\"graha-symbol\">${P_SYM[pn]}</span>\n" +
  "      <div class=\"chip-info\">\n" +
  "        <div class=\"chip-name\" data-d1-literal=\"graha-name\">${P_SA[pn]} · ${pn}</div>\n" +
  "        <div class=\"chip-sub\"><span data-d1-chart-field=\"planet.sign\">${p.sign}</span><span data-d1-literal=\"separator\"> · </span><span data-d1-chart-field=\"planet.house\">H${p.house}</span><span data-d1-literal=\"separator\"> · </span><span data-d1-chart-field=\"planet.degree\">${p.degree.toFixed(1)}°</span><span data-d1-chart-field=\"planet.retrograde\">${p.retrograde?' · ℞':''}</span></div>\n" +
  "      </div>\n" +
  "      <span class=\"chip-badge ${digCls}\" data-d1-field=\"position.dignity_label\">${label}</span>\n" +
  "      <span class=\"chip-arrow\" data-d1-literal=\"chevron\">›</span>`;",
  'chip leaf markers'));

// ── 4 · corpus element carries its own provenance ──────────────────────────
step(s => patch(s,
  "// One payload per chart_token, fetched once.",
  "// KAR-093: corpus output states which branch the SERVER selected, so a\n" +
  "// locally chosen branch is detectable in the DOM rather than only in review.\n" +
  "function d1CorpusEl(ref, sign) {\n" +
  "  if (!ref || ref.resolvable === false || !ref.key)\n" +
  "    return '<p data-d1-corpus-state=\"unresolvable\"></p>';\n" +
  "  return '<p data-d1-corpus=\"' + d1Esc(ref.corpus) +\n" +
  "         '\" data-d1-corpus-graha=\"' + d1Esc(ref.graha || '') +\n" +
  "         '\" data-d1-corpus-key=\"' + d1Esc(ref.key) +\n" +
  "         '\" data-d1-corpus-state=\"resolved\">' + d1Esc(d1Corpus(ref, sign)) + '</p>';\n" +
  "}\n" +
  "\n" +
  "// One payload per chart_token, fetched once.",
  'corpus element helper'));

// ── 5 · dṛṣṭi block markers ────────────────────────────────────────────────
step(s => patch(s,
  "  const rows = block.sources.map(s =>\n" +
  "    `<div class=\"kv-row\"><span class=\"kv-key\">${d1Esc(s.source)} · ${d1Esc(s.kind)}</span>` +\n" +
  "    `<span class=\"kv-val ${d1PolarityClass(s.polarity)}\">${d1Esc(s.polarity)}</span></div>`).join('');\n" +
  "  return rows + `<div class=\"kv-row\"><span class=\"kv-key\">Net</span>` +\n" +
  "         `<span class=\"kv-val ${d1PolarityClass(block.net)}\">${d1Esc(block.net)}</span></div>`;",
  "  const rows = block.sources.map((s, i) =>\n" +
  "    `<div class=\"kv-row\"><span class=\"kv-key\"><span data-d1-field=\"${path}.sources.${i}.source\">${d1Esc(s.source)}</span><span data-d1-literal=\"separator\"> · </span><span data-d1-field=\"${path}.sources.${i}.kind\">${d1Esc(s.kind)}</span></span>` +\n" +
  "    `<span class=\"kv-val ${d1PolarityClass(s.polarity)}\" data-d1-field=\"${path}.sources.${i}.polarity\">${d1Esc(s.polarity)}</span></div>`).join('');\n" +
  "  return rows + `<div class=\"kv-row\"><span class=\"kv-key\" data-d1-literal=\"net\">Net</span>` +\n" +
  "         `<span class=\"kv-val ${d1PolarityClass(block.net)}\" data-d1-field=\"${path}.net\">${d1Esc(block.net)}</span></div>`;",
  'drishti markers'));

step(s => patch(s,
  "    return `<p class=\"dim\">${d1Esc(block && block.subject || 'This bhāva')} receives no external drishti.</p>`;",
  "    return `<p class=\"dim\" data-d1-field=\"${path}.subject\" data-d1-drishti-state=\"none\">${d1Esc(block && block.subject || 'This bhāva')} receives no external drishti.</p>`;",
  'drishti empty-state marker'));


// ── 6 · drawer leaf markers ────────────────────────────────────────────────
// One entry per rendered leaf. Composite values are split into granular fields
// rather than given a single composite key, which was the smaller contract
// objection against v1's data-d1-field="chart.position".
const DRAWER_MARKERS = [
  ['<span class="kv-val">${d1Esc(d.rashi.sign)}</span>',
   '<span class="kv-val" data-d1-field="rashi.sign">${d1Esc(d.rashi.sign)}</span>'],
  ['<span class="kv-val">${d1Esc(d.rashi.dignity_label || \u2019\u2014\u2019)}</span>', null],
  ['<span class="kv-val">${d1Esc(d.rashi.sign_lord.graha)} \u2014 H${d.rashi.sign_lord.house} ${d1Esc(d.rashi.sign_lord.sign)}</span>',
   '<span class="kv-val"><span data-d1-field="rashi.sign_lord.graha">${d1Esc(d.rashi.sign_lord.graha)}</span><span data-d1-literal="separator"> \u2014 </span><span data-d1-field="rashi.sign_lord.house">H${d.rashi.sign_lord.house}</span><span data-d1-literal="separator"> </span><span data-d1-field="rashi.sign_lord.sign">${d1Esc(d.rashi.sign_lord.sign)}</span></span>'],
  ['<span class="kv-val">H${d.house.house} \u00b7 ${d1Esc(d.house.house_name)}</span>',
   '<span class="kv-val"><span data-d1-field="house.house">H${d.house.house}</span><span data-d1-literal="separator"> \u00b7 </span><span data-d1-field="house.house_name">${d1Esc(d.house.house_name)}</span></span>'],
  ['<span class="kv-val">${d1Esc(d.house.house_lord)}</span>',
   '<span class="kv-val" data-d1-field="house.house_lord">${d1Esc(d.house.house_lord)}</span>'],
  ['<span class="kv-val">${d1Esc(bh.bhavesh)} (lord of ${d1Esc(bh.of_sign)})</span>',
   '<span class="kv-val"><span data-d1-field="bhavesh.bhavesh">${d1Esc(bh.bhavesh)}</span><span data-d1-literal="separator"> (lord of </span><span data-d1-field="bhavesh.of_sign">${d1Esc(bh.of_sign)}</span><span data-d1-literal="separator">)</span></span>'],
  ['<span class="kv-val">${d1Esc(bh.support)}</span>',
   '<span class="kv-val" data-d1-field="bhavesh.support">${d1Esc(bh.support)}</span>'],
  ['<span class="kv-val">H${bb.from_house}</span>',
   '<span class="kv-val" data-d1-field="bhavat_bhavam.from_house">H${bb.from_house}</span>'],
  ['<span class="kv-val">H${bb.bb_house} \u00b7 ${d1Esc(bb.bb_house_name)}</span>',
   '<span class="kv-val"><span data-d1-field="bhavat_bhavam.bb_house">H${bb.bb_house}</span><span data-d1-literal="separator"> \u00b7 </span><span data-d1-field="bhavat_bhavam.bb_house_name">${d1Esc(bb.bb_house_name)}</span></span>'],
  ['<span class="kv-val">${d1Esc(bb.sustaining)}</span>',
   '<span class="kv-val" data-d1-field="bhavat_bhavam.sustaining">${d1Esc(bb.sustaining)}</span>'],
  ["<span class=\"kv-val\">${bk.karakas.map(d1Esc).join(' / ') || '\u2014'}</span>",
   "<span class=\"kv-val\" data-d1-field=\"bhava_karaka.karakas\">${bk.karakas.map(d1Esc).join(' / ') || '\u2014'}</span>"],
  ['<span class="kv-val">${d1Esc(bk.karaka_support)}</span>',
   '<span class="kv-val" data-d1-field="bhava_karaka.karaka_support">${d1Esc(bk.karaka_support)}</span>'],
  ['<span class="kv-val">${d1Esc(gs.functional_nature)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.functional_nature">${d1Esc(gs.functional_nature)}</span>'],
  ['<span class="kv-val">${d1Esc(gs.verse_yoga_status)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.verse_yoga_status">${d1Esc(gs.verse_yoga_status)}</span>'],
  ["<span class=\"kv-val\">${gs.ownership_yogakaraka ? 'yes' : 'no'}</span>",
   "<span class=\"kv-val\" data-d1-field=\"graha_saar.ownership_yogakaraka\">${gs.ownership_yogakaraka ? 'yes' : 'no'}</span>"],
  ['<span class="kv-val">${d1Esc(gs.maraka_status)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.maraka_status">${d1Esc(gs.maraka_status)}</span>'],
  ['<span class="kv-val">${d1Esc(gs.overall_verdict)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.overall_verdict">${d1Esc(gs.overall_verdict)}</span>'],
  ['<span class="kv-val">${d1Esc(gs.strength_verdict)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.strength_verdict">${d1Esc(gs.strength_verdict)}</span>'],
  ['<span class="kv-val">${d1Esc(gs.natural_nature)}</span>',
   '<span class="kv-val" data-d1-field="graha_saar.natural_nature">${d1Esc(gs.natural_nature)}</span>']
];
DRAWER_MARKERS.forEach(([from, to], i) => {
  if (to === null) return;
  step(x => patch(x, from, to, 'drawer marker ' + i));
});

// Composite rows whose optional branches need their own anchors.
step(s2 => patch(s2,
  '<span class="kv-val">${d1Esc(d.rashi.dignity_label || \'\u2014\')}</span>',
  '<span class="kv-val" data-d1-field="rashi.dignity_label">${d1Esc(d.rashi.dignity_label || \'\u2014\')}</span>',
  'rashi dignity_label'));
step(s2 => patch(s2,
  '<span class="kv-val">H${bh.position.house} \u00b7 ${d1Esc(bh.position.sign)} \u00b7 ${d1Esc(bh.position.dignity_label || \'\u2014\')}</span>',
  '<span class="kv-val"><span data-d1-field="bhavesh.position.house">H${bh.position.house}</span><span data-d1-literal="separator"> \u00b7 </span><span data-d1-field="bhavesh.position.sign">${d1Esc(bh.position.sign)}</span><span data-d1-literal="separator"> \u00b7 </span><span data-d1-field="bhavesh.position.dignity_label">${d1Esc(bh.position.dignity_label || \'\u2014\')}</span></span>',
  'bhavesh position'));
step(s2 => patch(s2,
  '<span class="kv-val">${d1Esc(bb.bb_lord)} \u2014 H${bb.bb_lord_position.house} ${d1Esc(bb.bb_lord_position.dignity_label || \'\u2014\')}</span>',
  '<span class="kv-val"><span data-d1-field="bhavat_bhavam.bb_lord">${d1Esc(bb.bb_lord)}</span><span data-d1-literal="separator"> \u2014 </span><span data-d1-field="bhavat_bhavam.bb_lord_position.house">H${bb.bb_lord_position.house}</span><span data-d1-literal="separator"> </span><span data-d1-field="bhavat_bhavam.bb_lord_position.dignity_label">${d1Esc(bb.bb_lord_position.dignity_label || \'\u2014\')}</span></span>',
  'bb lord'));
step(s2 => patch(s2,
  '<span class="kv-val">${d1Esc(gs.functional_basis_verse || \'\u2014\')}</span>',
  '<span class="kv-val" data-d1-field="graha_saar.functional_basis_verse">${d1Esc(gs.functional_basis_verse || \'\u2014\')}</span>',
  'basis verse'));

// ── 7 · corpus output routed through the provenance-bearing element ────────
[['d.rashi.corpus_ref, d.rashi.sign', 'rashi'], ['d.house.corpus_ref', 'house'],
 ['bb.corpus_ref', 'bhavat_bhavam'], ['bk.corpus_ref', 'bhava_karaka']].forEach(([args, name]) => {
  step(x => patch(x, '<p>${d1Esc(d1Corpus(' + args + '))}</p>',
                     '${d1CorpusEl(' + args + ')}', 'corpus element ' + name));
});

// ── 8 · node branch and drawer identity ────────────────────────────────────
step(s2 => patch(s2,
  ": '<p class=\"dim\">R\u0101hu and Ketu own no r\u0101\u015bi, so the lordship doctrine of BPHS 34 does not apply to them.</p>';",
  ": '<p class=\"dim\" data-d1-literal=\"node-no-lordship\" data-d1-lordship-state=\"absent\">R\u0101hu and Ketu own no r\u0101\u015bi, so the lordship doctrine of BPHS 34 does not apply to them.</p>';",
  'node branch marker'));
step(s2 => patch(s2,
  "    body.innerHTML = renderD1DrawerFromPayload(drawer);",
  "    body.setAttribute('data-d1-graha', pn);   // drawer identity, provable in the DOM\n" +
  "    body.innerHTML = renderD1DrawerFromPayload(drawer);",
  'drawer identity marker'));
step(s2 => patch(s2,
  "    body.innerHTML = renderD1DrawerError(err && err.message ? err.message : String(err));",
  "    body.removeAttribute('data-d1-graha');    // error state carries no graha identity\n" +
  "    body.innerHTML = renderD1DrawerError(err && err.message ? err.message : String(err));",
  'drawer error identity clear'));



// ── 9 · drawer identity does not outlive the drawer ────────────────────────
// Caught in my own verification: after a recast the drawer body still carried
// data-d1-graha from the previous chart. A stale identity marker is exactly the
// kind of thing the marker contract exists to make impossible.
step(s2 => patch(s2,
  "function closeDrawer() {\n" +
  "  document.getElementById('overlay').classList.remove('active');\n" +
  "  document.getElementById('drawer').classList.remove('open');\n" +
  "}",
  "function closeDrawer() {\n" +
  "  document.getElementById('overlay').classList.remove('active');\n" +
  "  document.getElementById('drawer').classList.remove('open');\n" +
  "  const _b = document.getElementById('drawer-body');\n" +
  "  if (_b) _b.removeAttribute('data-d1-graha');   // KAR-093: identity dies with the drawer\n" +
  "}",
  'clear drawer identity on close'));



// ── 10 · a drawer success also seeds the chips ─────────────────────────────
step(s2 => patch(s2,
  "    body.setAttribute('data-d1-graha', pn);   // drawer identity, provable in the DOM\n" +
  "    body.innerHTML = renderD1DrawerFromPayload(drawer);",
  "    body.setAttribute('data-d1-graha', pn);   // drawer identity, provable in the DOM\n" +
  "    body.innerHTML = renderD1DrawerFromPayload(drawer);\n" +
  "    // If the initial seed failed or was still in flight, THIS payload is the\n" +
  "    // first success for the current chart. Feed it to the chips too, or the\n" +
  "    // chips stay unknown beside a populated drawer.\n" +
  "    if (!_d1Seed) _acceptD1Payload(chartData && chartData.chart_token, _d1ChartEpoch, payload);",
  'drawer success seeds chips'));

// ── 11 · closing invalidates a pending drawer write ───────────────────────
step(s2 => patch(s2,
  "  const _b = document.getElementById('drawer-body');\n" +
  "  if (_b) _b.removeAttribute('data-d1-graha');   // KAR-093: identity dies with the drawer",
  "  ++_d1DrawerEpoch;   // KAR-093: a response still in flight must not write back\n" +
  "  const _b = document.getElementById('drawer-body');\n" +
  "  if (_b) _b.removeAttribute('data-d1-graha');   // identity dies with the drawer",
  'close cancels pending drawer write'));

// ── 12 · corpus keeps its provenance even when unresolvable ───────────────
step(s2 => patch(s2,
  "  if (!ref || ref.resolvable === false || !ref.key)\n" +
  "    return '<p data-d1-corpus-state=\"unresolvable\"></p>';",
  "  if (!ref || ref.resolvable === false || !ref.key)\n" +
  "    return '<p data-d1-corpus=\"' + d1Esc((ref && ref.corpus) || '') +\n" +
  "           '\" data-d1-corpus-graha=\"' + d1Esc((ref && ref.graha) || '') +\n" +
  "           '\" data-d1-corpus-key=\"' + d1Esc((ref && ref.key) || '') +\n" +
  "           '\" data-d1-corpus-state=\"unresolvable\"></p>';",
  'unresolvable corpus keeps provenance'));

// ── 13 · drishti paths fully qualified by owning block ───────────────────
step(s2 => patch(s2, "function d1DrishtiBlock(block) {", "function d1DrishtiBlock(block, path) {", 'drishti signature'));
[['d.house.drishti', 'house.drishti'], ['bh.drishti', 'bhavesh.drishti'],
 ['gs.house_drishti', 'graha_saar.house_drishti']].forEach(([expr, path]) => {
  step(x => patch(x, 'd1DrishtiBlock(' + expr + ')', "d1DrishtiBlock(" + expr + ", '" + path + "')", 'drishti call ' + path));
});

// ── 14 · drawer header joins the marked contract ─────────────────────────
step(s2 => patch(s2,
  "  const db    = document.getElementById('dr-dignity-badge');\n" +
  "\n" +
  "  document.getElementById('dr-planet-name').textContent",
  "  const db    = document.getElementById('dr-dignity-badge');\n" +
  "\n" +
  "  // KAR-093: the drawer header is part of the marked contract. The dignity\n" +
  "  // badge in particular is server-backed and must carry its payload path.\n" +
  "  document.getElementById('dr-planet-name').setAttribute('data-d1-literal', 'graha-name');\n" +
  "  document.getElementById('dr-planet-meta').setAttribute('data-d1-chart-field', 'planet.summary');\n" +
  "  db.setAttribute('data-d1-field', 'position.dignity_label');\n" +
  "  document.getElementById('dr-planet-name').textContent",
  'drawer header markers'));


// ── 15 · unknown badge class is exactly "chip-badge", no trailing space ────
step(s2 => patch(s2,
  '      <span class="chip-badge ${digCls}" data-d1-field="position.dignity_label">${label}</span>',
  '      <span class="${digCls ? \'chip-badge \' + digCls : \'chip-badge\'}" data-d1-field="position.dignity_label">${label}</span>',
  'chip badge class normalised'));

// ── 16 · section titles carry an explicit marker ──────────────────────────
step(s2 => patch(s2,
  "function d1Section(title, inner, open) {\n" +
  "  return `<div class=\"analysis-section\"><div class=\"section-head\" onclick=\"toggleSection(this)\">` +\n" +
  "         `<span>${d1Esc(title)}</span><span class=\"section-arrow${open ? ' open' : ''}\">\u25be</span></div>` +",
  "function d1Section(title, inner, open, mark) {\n" +
  "  // KAR-093: a section title is either an approved literal or a payload-bound\n" +
  "  // value. It is never unmarked, because an unmarked text leaf is exactly what\n" +
  "  // the closed contract has to reject.\n" +
  "  const _m = mark && mark.field ? ` data-d1-field=\"${mark.field}\"`\n" +
  "                                : ` data-d1-literal=\"${(mark && mark.literal) || 'section-title'}\"`;\n" +
  "  return `<div class=\"analysis-section\"><div class=\"section-head\" onclick=\"toggleSection(this)\">` +\n" +
  "         `<span${_m}>${d1Esc(title)}</span><span class=\"section-arrow${open ? ' open' : ''}\" data-d1-literal=\"chevron\">\u25be</span></div>` +",
  'section title marker'));



// ── 17 · remaining conditional and static leaves ──────────────────────────
step(s2 => patch(s2,
  "'<p class=\"dim\">Retrograde \u2014 inward review, delay then intensification.</p>'",
  "'<p class=\"dim\" data-d1-field=\"bhavesh.retrograde_note\">Retrograde \u2014 inward review, delay then intensification.</p>'",
  'retrograde note marker'));
step(s2 => patch(s2,
  "'<p>This is the house of <strong>Digbala</strong> \u2014 maximum directional strength.</p>'",
  "'<p data-d1-field=\"shadbala.at_digbala_peak_house\">This is the house of <strong data-d1-literal=\"digbala\">Digbala</strong> \u2014 maximum directional strength.</p>'",
  'digbala marker'));
step(s2 => patch(s2,
  "<div class=\"note-box\">Full \u1e62a\u1e0dbala",
  "<div class=\"note-box\" data-d1-literal=\"shadbala-pending\">Full \u1e62a\u1e0dbala",
  'shadbala note marker'));

// ── 18 · kv-key labels, scoped to the D1 drawer renderer only ─────────────
// Scoped rather than global: the same markup exists in renderers this ticket
// does not touch, and a global replace would silently edit them.
step(s2 => {
  const start = 'function renderD1DrawerFromPayload(d) {';
  const end = "  return parts.join('');\n}";
  const i = s2.indexOf(start);
  if (i === -1) throw new Error('drawer renderer not found');
  const j = s2.indexOf(end, i);
  if (j === -1) throw new Error('drawer renderer end not found');
  const region = s2.slice(i, j + end.length);
  const EXPECTED_KV_KEYS = 22;   // asserted, not merely non-zero
  const found = region.split('<span class="kv-key">').length - 1;
  if (found !== EXPECTED_KV_KEYS)
    throw new Error(`bulk "kv-key labels": found ${found}, expected exactly ${EXPECTED_KV_KEYS}`);
  bulk += found;
  const marked = region.split('<span class="kv-key">').join('<span class="kv-key" data-d1-literal="label">');
  return s2.slice(0, i) + marked + s2.slice(j + end.length);
});

// ── 19 · error state leaves ───────────────────────────────────────────────
step(s2 => patch(s2,
  "    <p><strong>The D1 analysis could not be loaded.</strong></p>\n" +
  "    <p class=\"dim\">${d1Esc(message)}</p>",
  "    <p data-d1-literal=\"error-heading\"><strong>The D1 analysis could not be loaded.</strong></p>\n" +
  "    <p class=\"dim\" data-d1-literal=\"error-detail\">${d1Esc(message)}</p>",
  'error state markers'));
step(s2 => patch(s2,
  "    <p class=\"dim\">This view is computed by the certified server engine.",
  "    <p class=\"dim\" data-d1-literal=\"error-rationale\">This view is computed by the certified server engine.",
  'error rationale marker'));







// ── 21 · loading and error states are marker-closed ───────────────────────
// The authorized contract requires the error state to contain NO data-d1-field
// element. v3 set the header markers once and left them, so loading and error
// both carried a field marker over text that was not payload-bound.
step(s2 => patch(s2,
  "  document.getElementById('dr-planet-name').setAttribute('data-d1-literal', 'graha-name');\n" +
  "  document.getElementById('dr-planet-meta').setAttribute('data-d1-chart-field', 'planet.summary');\n" +
  "  db.setAttribute('data-d1-field', 'position.dignity_label');\n",
  "  document.getElementById('dr-planet-name').setAttribute('data-d1-literal', 'graha-name');\n" +
  "  // Field markers are applied ONLY when payload-bound text is present. Loading\n" +
  "  // and error states carry a state marker instead.\n" +
  "  document.getElementById('dr-planet-meta').setAttribute('data-d1-chart-field', 'planet.summary');\n" +
  "  document.getElementById('dr-planet-meta').setAttribute('data-d1-state', 'loading');\n" +
  "  db.removeAttribute('data-d1-field');\n" +
  "  db.setAttribute('data-d1-state', 'loading');\n",
  'loading state markers'));

step(s2 => patch(s2,
  "    body.setAttribute('data-d1-graha', pn);   // drawer identity, provable in the DOM",
  "    document.getElementById('dr-planet-meta').removeAttribute('data-d1-state');\n" +
  "    document.getElementById('dr-planet-meta').setAttribute('data-d1-chart-field', 'planet.summary');\n" +
  "    db.removeAttribute('data-d1-state');\n" +
  "    db.setAttribute('data-d1-field', 'position.dignity_label');\n" +
  "    body.removeAttribute('data-d1-state');\n" +
  "    body.setAttribute('data-d1-graha', pn);   // drawer identity, provable in the DOM",
  'success state markers'));

step(s2 => patch(s2,
  "    body.removeAttribute('data-d1-graha');    // error state carries no graha identity",
  "    document.getElementById('dr-planet-meta').removeAttribute('data-d1-field');\n" +
  "    document.getElementById('dr-planet-meta').setAttribute('data-d1-state', 'error');\n" +
  "    db.removeAttribute('data-d1-field');\n" +
  "    db.setAttribute('data-d1-state', 'error');\n" +
  "    body.setAttribute('data-d1-state', 'error');\n" +
  "    body.removeAttribute('data-d1-graha');    // error state carries no graha identity",
  'error state markers'));

step(s2 => patch(s2,
  "  body.innerHTML = d1Notice('<p class=\"dim\">Consulting the engine\u2026</p>');",
  "  body.setAttribute('data-d1-state', 'loading');\n" +
  "  body.innerHTML = d1Notice('<p class=\"dim\" data-d1-literal=\"loading\">Consulting the engine\u2026</p>');",
  'loading text marker'));

// ── 22 · error detail is error-state text, not an approved static literal ──
step(s2 => patch(s2,
  '<p class="dim" data-d1-literal="error-detail">${d1Esc(message)}</p>',
  '<p class="dim" data-d1-error-field="message">${d1Esc(message)}</p>',
  'error detail contract'));

// ── 23 · the dynamic section title gets a field marker, not a literal ─────
step(s2 => patch(s2,
  "  parts.push(d1Section(`Bh\u0101va \u00b7 H${d.house.house}`, `",
  "  parts.push(d1SectionF(`Bh\u0101va \u00b7 H${d.house.house}`, 'house.house', `",
  'bhava title field marker'));
step(s2 => patch(s2,
  "function d1Section(title, inner, open, mark) {",
  "// A title derived from the payload is field-bound, never a literal.\n" +
  "function d1SectionF(title, field, inner, open) { return d1Section(title, inner, open, { field }); }\n" +
  "function d1Section(title, inner, open, mark) {",
  'section field helper'));

// ── 24 · close control is an approved literal ─────────────────────────────
step(s2 => patch(s2,
  '<button class="drawer-close" onclick="closeDrawer()">\u2715</button>',
  '<button class="drawer-close" onclick="closeDrawer()" data-d1-literal="close">\u2715</button>',
  'close control marker'));


// ── 25 · placeholders are explicit, state never authorises text ───────────
// data-d1-state records WHICH state the drawer is in. It is not permission for
// arbitrary text. Every placeholder glyph is marked as an approved placeholder
// in its own right, so the closure rule is satisfied by the leaf, not by an
// ancestor's state attribute.
step(s2 => patch(s2,
  "  db.textContent = '\u2026';\n" +
  "  db.className   = 'drawer-dignity';",
  "  db.textContent = '\u2026';\n" +
  "  db.className   = 'drawer-dignity';\n" +
  "  db.setAttribute('data-d1-literal', 'placeholder');",
  'loading placeholder marker'));

step(s2 => patch(s2,
  "    db.textContent = drawer.position.dignity_label || '\u2014';",
  "    db.removeAttribute('data-d1-literal');   // real value, not a placeholder\n" +
  "    db.textContent = drawer.position.dignity_label || '\u2014';",
  'success clears placeholder'));

step(s2 => patch(s2,
  "    db.textContent = '\u2014';\n" +
  "    db.className   = 'drawer-dignity';",
  "    db.textContent = '\u2014';\n" +
  "    db.className   = 'drawer-dignity';\n" +
  "    db.setAttribute('data-d1-literal', 'placeholder');",
  'error placeholder marker'));

// The chip badge shows a placeholder when the chart has no seed. It must be
// marked as one rather than carrying a payload path over text the payload never
// supplied.
step(s2 => patch(s2,
  "    badge.className = b.cls ? ('chip-badge ' + b.cls) : 'chip-badge';\n" +
  "    badge.textContent = b.label;",
  "    badge.className = b.cls ? ('chip-badge ' + b.cls) : 'chip-badge';\n" +
  "    if (b.seeded) { badge.removeAttribute('data-d1-literal');\n" +
  "                    badge.setAttribute('data-d1-field', 'position.dignity_label'); }\n" +
  "    else          { badge.removeAttribute('data-d1-field');\n" +
  "                    badge.setAttribute('data-d1-literal', 'placeholder'); }\n" +
  "    badge.textContent = b.label;",
  'chip badge placeholder marker'));

step(s2 => patch(s2,
  "  return d ? { label: d.position.dignity_label || '\\u2014',\n" +
  "               cls: D1_DIGNITY_CLASS[d.position.dignity] || '' }\n" +
  "           : { label: '\\u2014', cls: '' };",
  "  return d ? { label: d.position.dignity_label || '\\u2014',\n" +
  "               cls: D1_DIGNITY_CLASS[d.position.dignity] || '', seeded: true }\n" +
  "           : { label: '\\u2014', cls: '', seeded: false };",
  'badge seeded flag'));

step(s2 => patch(s2,
  '      <span class="${digCls ? \'chip-badge \' + digCls : \'chip-badge\'}" data-d1-field="position.dignity_label">${label}</span>',
  '      <span class="${digCls ? \'chip-badge \' + digCls : \'chip-badge\'}" ${_b.seeded ? \'data-d1-field="position.dignity_label"\' : \'data-d1-literal="placeholder"\'}>${label}</span>',
  'chip badge initial marker'));

fs.writeFileSync(outPath, src);
const after = crypto.createHash('sha256').update(fs.readFileSync(outPath)).digest('hex');
const nl = t => { let c = 0; for (const b of Buffer.from(t)) if (b === 10) c++; return c; };
console.log(`PRODUCT FIX v5 APPLIED · ${n} steps · ${exactOnce} exact-once, ${bulk} bulk replacements`);
console.log('  in  sha256 : ' + before);
console.log('  out sha256 : ' + after);
console.log('  newlines   : ' + nl(fs.readFileSync(inPath, 'utf8')) + ' -> ' + nl(src));
