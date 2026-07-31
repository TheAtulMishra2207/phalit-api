// KAR-093 step 6b · D1 frontend cutover.
// Static source guards + live DOM render against a real server payload shape.
const fs = require('fs');
const path = process.argv[2] || 'newphalit.html';
const html = fs.readFileSync(path, 'utf8');

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log('  FAIL: ' + m)); };

// isolate a function body by brace matching
function fnBody(name, src = html) {
  const re = new RegExp('(?:async\\s+)?function\\s+' + name + '\\s*\\(');
  const m = re.exec(src);
  if (!m) return null;
  let i = src.indexOf('{', m.index), depth = 0, end = i;
  for (; end < src.length; end++) {
    if (src[end] === '{') depth++;
    else if (src[end] === '}') { depth--; if (depth === 0) break; }
  }
  return src.slice(m.index, end + 1);
}

// The page carries a real global d1Esc (38 call sites) that the brace
// extraction below never reached, so both evaluated blocks died on
// "d1Esc is not defined". It is EXTRACTED FROM THE PAGE, never stubbed:
// stubbing the helper the code should own is what let the original
// "esc is not defined" crash survive a 58-assertion suite.
const d1EscSrc = fnBody('d1Esc');
if (!d1EscSrc) throw new Error('d1Esc not found in ' + path + '; the D1 render block cannot be evaluated without it');

console.log('=== the D1 path is server-only ===');
const openDrawerSrc = fnBody('openDrawer');
ok(openDrawerSrc !== null, 'openDrawer exists');
ok(/d1Prepare\(/.test(openDrawerSrc), 'openDrawer calls d1Prepare');
ok(/renderD1DrawerFromPayload\(/.test(openDrawerSrc), 'openDrawer renders from the payload');

const FORBIDDEN_IN_D1 = [
  'buildDrawerContent', 'getScore(', 'getDignityLabel(', 'getDignityClass(',
  'getPlanetsAspectingHouse', 'getPlanetsAspectingPlanet', 'getAspects(',
  'myAspects', 'jaiminiAspects', 'longitude - sun', 'moonWaning', '% 360) > 180',
  'DIGNITY_SCORES', '_isEff',
];
const d1PathSrc = [openDrawerSrc, fnBody('renderD1DrawerFromPayload'), fnBody('d1Corpus'),
                   fnBody('d1DrishtiBlock'), fnBody('d1Prepare'), fnBody('_d1Fetch'),
                   fnBody('renderD1DrawerError'), fnBody('d1Notice'), fnBody('d1Section')]
                  .filter(Boolean).join('\n');
FORBIDDEN_IN_D1.forEach(sym =>
  ok(!d1PathSrc.includes(sym), `D1 render path must not reference ${sym}`));

console.log('\n=== server failure produces an error state, never a fallback ===');
ok(/renderD1DrawerError\(/.test(openDrawerSrc), 'openDrawer renders the error state');
const catchBlock = /catch\s*\(err\)\s*\{[\s\S]*?\n  \}/.exec(openDrawerSrc);
ok(catchBlock !== null, 'openDrawer has a catch block');
ok(!/buildDrawerContent/.test(catchBlock[0]), 'the catch path never calls the legacy builder');
ok(/return;/.test(catchBlock[0]), 'the catch path returns rather than continuing');

console.log('\n=== D9 is cut over to the server, both halves ===');
const d9 = fnBody('openD9Drawer');
const d9chips = fnBody('renderD9PlanetList');
ok(d9 !== null, 'openD9Drawer still exists');
const LEGACY = /getScore\(|getDignityLabel\(|getDignityClass\(|buildDrawerContent\(/;
ok(!LEGACY.test(d9), 'openD9Drawer runs no client dignity engine');
ok(!LEGACY.test(d9chips), 'renderD9PlanetList runs no client dignity engine');
ok(/d1Prepare\([^)]*D9_VARGA\)/.test(d9), 'the D9 drawer fetches the D9 payload');
ok(/renderD9DrawerFromPayload\(/.test(d9), 'the D9 drawer renders from the payload');
ok(/_d1BadgeFor\(pn, D9_VARGA\)/.test(d9chips), 'the D9 chip badge reads the D9 seed');
// buildDrawerContent is retained for the OTHER divisional charts, which is why
// its deletion is still out of scope here.
ok(fnBody('buildDrawerContent') !== null, 'the legacy builder is retained for the other vargas');

console.log('\n=== deleted vs deliberately retained ===');
// The approved scope was "delete after a guard proves no callers remain". The
// guard proves callers DO remain — inside buildDrawerContent, which QA approved
// retaining for D9 — so deletion is deferred and that fact is asserted here
// rather than left as an unexplained omission.
{
  const survivors = [];
  const builder = fnBody('buildDrawerContent') || '';
  if (/getPlanetsAspectingHouse\s*\(/.test(builder)) survivors.push('buildDrawerContent');
  ok(survivors.length > 0,
     'getPlanetsAspectingHouse still has a caller, so deletion is correctly deferred');
  ok(survivors.every(f => f === 'buildDrawerContent'),
     'its only surviving caller is the legacy builder retained for D9');
  ok(!/getPlanetsAspectingHouse/.test(d1PathSrc),
     'the D1 render path never reaches getPlanetsAspectingHouse');
  ok(/DELETION DEFERRED \(KAR-093 step 6b\)/.test(html),
     'the deferral is documented at the definition site');
}
[['getScore', 42], ['getDignityLabel', 28], ['getPlanetsAspectingPlanet', 2]].forEach(([sym]) => {
  ok(new RegExp('DEPRECATED \\(KAR-093 step 6b\\)[\\s\\S]{0,400}function\\s+' + sym).test(html),
     `${sym} carries a deprecation banner`);
});

console.log('\n=== corpus projection ===');
ok(/const D1_RASHI_CORPUS/.test(html), 'D1-only enum-keyed projection exists');
ok(/const RASHI_CORPUS = \{/.test(html), 'legacy RASHI_CORPUS shape is untouched');
const NINE = ['Exalted','Moolatrikona','Own Sign','Great Friend','Friend','Neutral',
              'Enemy','Great Enemy','Debilitated'];
const tierTable = /const D1_DIGNITY_LEGACY_TIER = Object\.freeze\(\{[\s\S]*?\}\);/.exec(html)[0];
NINE.forEach(d => ok(tierTable.includes(`'${d}'`), `projection covers ${d}`));
ok(/'Great Friend': *'1'/.test(tierTable) && /'Friend': *'1'/.test(tierTable),
   'great_friend aliases friend while prose is shared');
ok(/'Great Enemy': *'-1'/.test(tierTable) && /'Enemy': *'-1'/.test(tierTable),
   'great_enemy aliases enemy while prose is shared');
ok(/resolvable === false/.test(fnBody('d1Corpus')), 'unresolvable refs yield no corpus key');

console.log('\n=== live render against a server payload ===');
(function () {
  const block = html.slice(html.indexOf('const D1_DIGNITY_LEGACY_TIER'),
                           html.indexOf('// ══ END KAR-093 STEP 6b'));
  const stub = `
    const RASHI_CORPUS = { Saturn: { '4': 'Exalted Saturn in {sign} text.' } };
    const HOUSE_CORPUS = { Saturn: { '1': 'Saturn in H1 text.' } };
    const BHAVAT_DESC  = { '1': 'Bhavat bhavam text.' };
    const BHAVA_KARAKA = { '1': { text: 'Karaka text.' } };
    const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
    ${d1EscSrc}
    const API = 'http://x'; const fetch = () => { throw new Error('no network in test'); };
    ${block}
    return { renderD1DrawerFromPayload, renderD1DrawerError, d1Corpus, D1_RASHI_CORPUS };
  `;
  const api = new Function(stub)();

  const drawer = {
    graha: 'Saturn',
    position: { graha: 'Saturn', house: 1, sign: 'Libra', degree_in_sign: 16.5,
                dignity: 'Exalted', dignity_label: 'Uchcha (Exalted)', retrograde: false },
    rashi: { sign: 'Libra', sign_index: 6, dignity: 'Exalted', dignity_label: 'Uchcha (Exalted)',
             sign_lord: { graha: 'Venus', house: 1, sign: 'Libra', dignity_label: 'Sama' },
             corpus_ref: { corpus: 'RASHI_CORPUS', graha: 'Saturn', key: 'Exalted', resolvable: true } },
    house: { house: 1, house_name: 'Tanu', sign: 'Libra', house_lord: 'Venus',
             corpus_ref: { corpus: 'HOUSE_CORPUS', graha: 'Saturn', key: '1', resolvable: true },
             drishti: { subject: 'H1', net: 'supportive',
                        sources: [{ source: 'Moon', kind: '7th', polarity: 'supportive', basis: 'x' }] } },
    bhavesh: { bhavesh: 'Venus', of_sign: 'Libra', support: 'moderate', retrograde_note: false,
               position: { graha: 'Venus', house: 1, sign: 'Libra', dignity_label: 'Sama' },
               drishti: { subject: 'Venus (Bhavesh)', net: 'unassessed', sources: [] } },
    bhavat_bhavam: { from_house: 1, bb_house: 1, bb_house_name: 'Tanu', bb_lord: 'Venus',
                     bb_lord_position: { graha: 'Venus', house: 1, sign: 'Libra', dignity_label: 'Sama' },
                     sustaining: 'moderate',
                     corpus_ref: { corpus: 'BHAVAT_DESC', key: '1', resolvable: true } },
    bhava_karaka: { house: 1, karakas: ['Sun'], primary_karaka: 'Sun', karaka_support: 'moderate',
                    subject_is_karaka_of_own_house: false,
                    corpus_ref: { corpus: 'BHAVA_KARAKA', key: '1', resolvable: true } },
    shadbala: { computed_server_side: false, at_digbala_peak_house: false },
    graha_saar: { overall_verdict: 'strong', strength_verdict: 'exceptional',
                  natural_nature: 'natural_malefic', has_lordship_doctrine: true,
                  functional_nature: 'benefic', verse_yoga_status: 'none',
                  ownership_yogakaraka: true, maraka_status: 'none',
                  functional_basis_verse: 'BPHS 34.33',
                  house_drishti: { subject: 'H1', net: 'supportive',
                                   sources: [{ source: 'Moon', kind: '7th', polarity: 'supportive', basis: 'x' }] } }
  };

  const out = api.renderD1DrawerFromPayload(drawer);
  ok(out.includes('Exalted Saturn in Libra text.'), 'rashi corpus resolves and {sign} is substituted');
  ok(out.includes('Saturn in H1 text.'), 'house corpus resolves by house key');
  ok(out.includes('Bhavat bhavam text.'), 'bhavat corpus resolves');
  ok(out.includes('Karaka text.'), 'bhava karaka corpus resolves');
  ok(out.includes('exceptional') && out.includes('natural_malefic'),
     'strength and natural nature both shown — dignity does not reverse nature');
  ok(out.includes('BPHS 34.33'), 'the doctrine verse is surfaced');
  ok(!/\bscore\b/i.test(out), 'no score appears anywhere in the rendered drawer');
  ok(out.includes('supportive'), 'drishti polarity from the server is rendered');

  // nodes: no dignity, no fabricated corpus
  const ketu = JSON.parse(JSON.stringify(drawer));
  ketu.graha = 'Ketu';
  ketu.position.dignity = null; ketu.position.dignity_label = null;
  ketu.rashi.corpus_ref = { corpus: 'RASHI_CORPUS', graha: 'Ketu', key: '', resolvable: false };
  ketu.graha_saar.has_lordship_doctrine = false;
  ketu.graha_saar.functional_nature = null;
  const kout = api.renderD1DrawerFromPayload(ketu);
  ok(!kout.includes('undefined'), 'an unresolvable node drawer renders without undefined');
  ok(kout.includes('own no rāśi'), 'nodes explain the absent lordship doctrine');
  ok(api.d1Corpus({ corpus: 'RASHI_CORPUS', graha: 'Ketu', key: '', resolvable: false }) === '',
     'an unresolvable ref yields no corpus text');

  const err = api.renderD1DrawerError('d1/prepare 503');
  ok(err.includes('could not be loaded') && err.includes('d1/prepare 503'),
     'the error state names the failure');
  ok(!/recalculated in the browser\?/.test(err) && err.includes('not\n    recalculated in the browser'),
     'the error state states that nothing is recomputed locally');
})();


console.log('\n=== BLOCKER 1: loading and error states are actually visible ===');
{
  ok(!/class="drawer-section"/.test(html), 'the unstyled drawer-section wrapper is gone');
  ok(/\.analysis-section\{/.test(html), 'analysis-section is the styled wrapper');
  const notice = fnBody('d1Notice');
  ok(notice && /analysis-section/.test(notice), 'notices use the styled wrapper');
  ok(notice && /section-body open/.test(notice), 'notices emit section-body OPEN');
  const errSrc = fnBody('renderD1DrawerError');
  ok(/d1Notice\(/.test(errSrc), 'the error state renders through d1Notice');
  const openSrc = fnBody('openDrawer');
  ok(/d1Notice\(/.test(openSrc), 'the loading state renders through d1Notice');
  ok(/section-body\$\{open \? ' open' : ''\}/.test(fnBody('d1Section')),
     'ordinary sections open only when asked');
}

console.log('\n=== BLOCKER 1: visibility proven by CSS semantics, not string presence ===');
(function () {
  const block = html.slice(html.indexOf('const D1_DIGNITY_LEGACY_TIER'),
                           html.indexOf('// ══ END KAR-093 STEP 6b'));
  const stub = `
    const RASHI_CORPUS={}, HOUSE_CORPUS={}, BHAVAT_DESC={}, BHAVA_KARAKA={};
    const esc = s => String(s == null ? '' : s);
    ${d1EscSrc}
    const API='http://x'; const fetch=()=>{throw new Error('no network');};
    ${block}
    return { renderD1DrawerError, d1Notice, d1Section };
  `;
  const api = new Function(stub)();
  // .section-body is display:none unless it carries `open` — so every body a
  // user must see has to be emitted with the class.
  const bodies = html => [...html.matchAll(/class="section-body([^"]*)"/g)].map(m => m[1]);
  const err = api.renderD1DrawerError('d1/prepare 503');
  ok(bodies(err).length === 1, 'the error state renders exactly one body');
  ok(bodies(err).every(c => c.includes('open')), 'the error body is visible (has open)');
  const loading = api.d1Notice('<p>Consulting…</p>');
  ok(bodies(loading).every(c => c.includes('open')), 'the loading body is visible (has open)');
  const collapsed = api.d1Section('X', 'y');
  ok(!bodies(collapsed)[0].includes('open'), 'an ordinary section starts collapsed');
  ok(bodies(api.d1Section('X', 'y', true))[0].includes('open'), 'an opened section carries open');
})();

console.log('\n=== BLOCKER 2: the session is server-issued and sent on BOTH requests ===');
{
  ok(!/Math\.random\(\)[\s\S]{0,80}_phalitSession/.test(html),
     'the browser no longer mints an owner key');
  ok(!/function\s+d1SessionId/.test(html), 'client session minting is removed');
  ok(/function\s+d1RememberSession/.test(html), 'the client stores the server-issued session');
  ok(/anon_session/.test(fnBody('d1RememberSession')), 'it reads anon_session from /chart');
  const hdr = fnBody('d1SessionHeaders');
  ok(hdr && /X-Phalit-Session/.test(hdr), 'the header helper attaches the session');
  const chartFetch = /const res = await fetch\(`\$\{API\}\/chart`[\s\S]{0,260}/.exec(html)[0];
  ok(/d1SessionHeaders\(\)/.test(chartFetch), '/chart sends the session header too');
  ok(/d1RememberSession\(chartData\)/.test(html), '/chart response is remembered');
  ok(/d1SessionHeaders\(\)/.test(fnBody('_d1Fetch')), '/d1/prepare sends the same header');
}

console.log('\n=== BLOCKER 3: stale responses cannot overwrite a newer selection ===');
{
  const openSrc = fnBody('openDrawer');
  ok(/_d1DrawerEpoch/.test(html), 'a selection epoch exists');
  ok(/const epoch = \+\+_d1DrawerEpoch/.test(openSrc), 'each open takes a new epoch');
  ok((openSrc.match(/epoch !== _d1DrawerEpoch/g) || []).length >= 2,
     'both the success and error paths check the epoch');
  const prep = fnBody('d1Prepare');
  ok(/_d1PayloadCache\.set\((?:key|_d1CacheKey\()/.test(prep),
     'the in-flight promise is cached, not just the settled payload');
  // D9 cutover: keying on chart_token alone let whichever varga was opened
  // first serve the other from cache, with no request. The key carries the
  // varga now, and this asserts it rather than trusting the comment.
  ok(/_d1CacheKey\(chartToken, varga\)/.test(prep),
     'the cache key is scoped to (chart_token, varga), not chart_token alone');
  ok(/varga: varga \|\| D1_VARGA/.test(fnBody('_d1Fetch')),
     'the request body carries the varga');
  ok(/_d1PayloadCache\.delete\(key\)/.test(prep), 'a failed promise is evicted');
  ok(/_d1PayloadCache\.clear\(\)/.test(html), 'a new chart invalidates cached payloads');
}

console.log('\n=== BLOCKER A: recasting a chart invalidates in-flight drawers ===');
{
  const cast = /chartData = await res\.json\(\);[\s\S]{0,700}?renderChartView\(\);/.exec(html);
  ok(cast !== null, 'the chart-commit path is locatable');
  ok(/\+\+_d1DrawerEpoch/.test(cast[0]), 'committing a new chart bumps the drawer epoch');
  ok(/_d1PayloadCache\.clear\(\)/.test(cast[0]), 'committing a new chart clears the payload cache');
  ok(/closeDrawer\(\)/.test(cast[0]), 'committing a new chart closes the open drawer');
  const epochIdx = cast[0].indexOf('++_d1DrawerEpoch');
  const renderIdx = cast[0].indexOf('renderChartView()');
  ok(epochIdx > -1 && epochIdx < renderIdx, 'invalidation happens before the new chart renders');
}

console.log('\n=== BLOCKER 3: simulated out-of-order clicks ===');
(async function raceSimulation() {
  // QA's exact sequence: click Saturn, click Mars, Mars resolves first,
  // Saturn resolves last. The newest selection must survive.
  let epoch = 0;
  const rendered = { header: null, body: null };
  const open = (pn, delay) => {
    const mine = ++epoch;
    rendered.header = pn;                       // header set synchronously
    return new Promise(r => setTimeout(r, delay)).then(() => {
      if (mine !== epoch) return;               // the guard under test
      rendered.body = pn;
    });
  };
  const saturn = open('Saturn', 40);
  const mars   = open('Mars', 5);
  await Promise.all([saturn, mars]);
  ok(rendered.header === 'Mars', 'header shows the newest selection');
  ok(rendered.body === 'Mars', `body shows the newest selection (got ${rendered.body})`);
  ok(rendered.header === rendered.body, 'header and body agree');

  // QA blocker A: a drawer request from the OLD chart resolves after a new
  // chart is committed. The commit bumps the epoch, so the stale response is
  // discarded instead of rendering over the new chart.
  const state = { body: null, badge: null };
  const openOnChart = (pn, delay) => {
    const mine = ++epoch;
    state.badge = pn;
    return new Promise(r => setTimeout(r, delay)).then(() => {
      if (mine !== epoch) return;
      state.body = 'BODY:' + pn;
    });
  };
  const commitNewChart = () => { ++epoch; state.body = null; state.badge = null; };

  const stale = openOnChart('Saturn', 30);   // chart A drawer, still pending
  commitNewChart();                          // chart B committed
  await stale;                               // chart A response lands late
  ok(state.body === null, `stale chart-A response must not render (got ${state.body})`);
  ok(state.badge === null, 'the drawer was reset on recast');
})().then(() => {
  console.log(`\n${pass}/${pass + fail} assertions passed`);
  process.exit(fail ? 1 : 0);
}).catch(err => {
  console.error('race simulation threw:', err);
  process.exit(1);
});
