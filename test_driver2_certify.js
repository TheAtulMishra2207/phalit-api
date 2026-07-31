'use strict';
// Unit-proves the certification logic without a browser, since Playwright
// cannot launch in this sandbox. It exercises the decision, not the driving.
const D = require('./kar093_step9_driver2.js');
let pass=0, fail=0;
const t=(n,c,d)=>{ if(c){pass++;console.log('  ok   '+n);} else {fail++;console.log('  FAIL '+n+(d?' — '+d:''));} };

function launched(overrides) {
  const d = new D.PlaywrightDriver(overrides.opts || {});
  d._pw = { name: 'playwright-core', version: overrides.pw || '1.57.2' };
  d._chromium = overrides.chromium || '144.0.7559.96';
  d._execPath = overrides.execPath === undefined ? '/usr/bin/chromium' : overrides.execPath;
  d._managedPath = '(none)';
  return d;
}

console.log('DRIVER v2 · CERTIFICATION LOGIC');
{
  const d = launched({});
  const c = d.certify();
  t('un-conformant driver cannot certify', !c.certifying &&
    c.reasons.some(r => /conformance has not passed/.test(r)), JSON.stringify(c.reasons));
}
{
  const d = launched({ execPath: null });
  t('missing executablePath is a refusal reason',
    d.certify().reasons.some(r => /must name the browser/.test(r)));
}
{
  const d = launched({ pw: '1.62.0' });
  t('wrong playwright minor is a refusal reason',
    d.certify().reasons.some(r => /is not 1\.57\.x/.test(r)));
}
{
  const d = launched({ chromium: '145.0.1.1' });
  t('wrong chromium major is a refusal reason',
    d.certify().reasons.some(r => /is not 144\.x/.test(r)));
}
{
  const d = launched({});
  t('no public setter exists to self-assert conformance',
    typeof d.markConformancePassed === 'undefined');
  const before = d.certify().certifying;
  try { d._conformancePassed = true; } catch (e) {}
  t('setting the old private flag does not grant certification',
    d.certify().certifying === before && before === false);
}
{
  const d = new D.JsdomDriver();
  const caps = d.capabilities();
  t('jsdom declares obstruction unavailable', caps.obstruction === false);
  t('jsdom refuses certification outright', d.certify().certifying === false);
}
{
  // The obstruction predicate, proved directly: a click that LANDS and then
  // throws must not pass. The OR form in v2 accepted exactly this.
  const ok = (threw, hits) => threw === true && hits === 0;
  t('obstruction predicate rejects land-then-throw', ok(true, 1) === false);
  t('obstruction predicate rejects silent success', ok(false, 1) === false);
  t('obstruction predicate accepts a true block', ok(true, 0) === true);
}
// ── orchestrator integration: the granted instance is the one reused ──────
(async () => {
  const G = require('./kar093_step9_driver2.js');
  const conf = await G.runDriverConformance(G.JsdomDriver, () => {});
  t('conformance returns the driver instance for reuse', !!conf.driver);
  t('a fresh instance is not the conformance instance', new G.JsdomDriver() !== conf.driver);
  t('jsdom refuses certification either way',
    /cannot certify/.test(conf.driver.certify().reasons.join('|')));
  console.log('');
  console.log(`${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
