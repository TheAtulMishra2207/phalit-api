// KAR-079 · North Indian chart numerals regression test.
// Houses stay fixed geometrically; the PRINCIPAL numeral per compartment is the
// rasi number of the occupying sign; house numbers appear only as small
// secondary H-labels. Extracts the SHIPPED renderNIChart from newphalit.html.
const fs = require('fs');
const js = fs.readFileSync(process.argv[2] || 'newphalit.html', 'utf8');

const start = js.indexOf('function renderNIChart(');
const end = js.indexOf('\nfunction renderD1Chart', start);
const fnSrc = js.slice(start, end);

let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log('  FAIL: ' + m)); };

function render(lagnaSignIdx) {
  let captured = '';
  const sandbox = new Function('SIGNS', 'P_COLOR', 'P_SYM', 'P_SA', 'document', fnSrc + `
    renderNIChart('t-svg', ${lagnaSignIdx}, {});
  `);
  sandbox(
    ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'],
    {}, {}, {},
    { getElementById: () => ({ set innerHTML(v) { captured = v; } }) }
  );
  return captured;
}

// principal numerals appear as Cinzel 13 texts; secondary as "H<n> · <Sig>"
function principals(svg) {
  return [...svg.matchAll(/font-family="Cinzel" font-size="13"[^>]*>(\d+)<\/text>/g)].map(m => +m[1]);
}
function secondaries(svg) {
  return [...svg.matchAll(/>H(\d+) · ([A-Za-z]{3})<\/text>/g)].map(m => ({ h: +m[1], sig: m[2] }));
}

console.log('=== Libra Lagna (founder chart): compartment numerals are rasi numbers ===');
{
  const svg = render(6); // Libra, 0-based idx 6
  const nums = principals(svg);
  const expect = [7,8,9,10,11,12,1,2,3,4,5,6]; // H1..H12 for Libra Lagna
  ok(nums.length === 12, `12 principal numerals rendered (got ${nums.length})`);
  ok(JSON.stringify(nums) === JSON.stringify(expect), `Libra Lagna numerals H1..H12 = ${expect.join(',')} (got ${nums.join(',')})`);
  ok(nums[0] === 7, 'Lagna compartment shows 7 (Libra), the exact QA repro');
  const secs = secondaries(svg);
  ok(secs.length === 12, `12 secondary H-labels present (got ${secs.length})`);
  ok(secs[0].h === 1 && secs[0].sig === 'Lib', 'secondary label H1 · Lib in Lagna compartment');
  ok(secs[6].h === 7 && secs[6].sig === 'Ari', 'secondary label H7 · Ari opposite');
}

console.log('=== Aries Lagna (identity case): rasi equals house everywhere ===');
{
  const svg = render(0);
  const nums = principals(svg);
  ok(JSON.stringify(nums) === JSON.stringify([1,2,3,4,5,6,7,8,9,10,11,12]), `Aries Lagna numerals 1..12 (got ${nums.join(',')})`);
}

console.log('=== Pisces Lagna: wrap-around ===');
{
  const svg = render(11);
  const nums = principals(svg);
  ok(JSON.stringify(nums) === JSON.stringify([12,1,2,3,4,5,6,7,8,9,10,11]), `Pisces Lagna numerals wrap (got ${nums.join(',')})`);
}

console.log('=== permanent negative: house numbers must not be the principal numerals ===');
{
  const svg = render(6);
  const nums = principals(svg);
  ok(JSON.stringify(nums) !== JSON.stringify([1,2,3,4,5,6,7,8,9,10,11,12]), 'Libra Lagna principals are NOT house numbers 1..12 (the KAR-079 defect)');
}

console.log(`\n${pass}/${pass + fail} assertions passed`);
process.exit(fail ? 1 : 0);
