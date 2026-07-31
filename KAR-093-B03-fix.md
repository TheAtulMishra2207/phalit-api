# KAR-093-B03 · the whole-file fixture hash no longer gates

30 July 2026. Bounded as authorized. Two files, four hunks, 24/24 on the re-run.

| File | SHA-256 | newlines | bytes |
|---|---|---|---|
| `kar093_p6_bind.js` | `e97eae1420bdffac7b05f71433c9ba04aa8cca2d3e1ff8cf6003ba629393735b` | 251 | 12,798 |
| `test_kar093_p6_verify.js` | `3d6afc25e31acd0f3f4ff0270ec916e494279ea7d4dc785f604529ce654a82db` | 294 | 13,579 |

Superseded: bind `4ca865ed` (242 nl, 12,167 b), suite `156ef5d7` (279 nl, 12,777 b).

`fixtureSha256` stays at `b38e4990` as recorded provenance. **Not re-pinned to
`4b2199b4`**, and the comment at the declaration says why: any new value is
host-specific in exactly the same way and would fail on the next Python.

---

## 1. Diff · nothing else moved

**`kar093_p6_bind.js`** — two hunks, one of which is comment only.

```
64a65,67    + three comment lines at the fixtureSha256 declaration
213,214c216,223
  - if (g.fixture_sha256 !== ACCEPTED_P6.fixtureSha256)
  -   problems.push(`regenerated fixture sha256 … is not the accepted …`);
  + eight comment lines explaining the removal
```

The only executable change is the deletion of one `if` and its `problems.push`.
No comparison, branch or function body was touched. `grep fixtureSha256` now
returns two lines: the declaration and a comment.

**`test_kar093_p6_verify.js`** — two hunks, both retargets.

```
108,110c108,117    E0c retargeted to the canonical digest
247,249c254,264    J6 inverted (see below)
```

---

## 2. E0c · retargeted

Was `regeneration is byte-deterministic (accepted fixture sha256)`. That property
is host-specific, because the artifact embeds the generating interpreter's
version, so the case was asserting something that must be allowed to vary. It now
asserts the canonical digest of the browser-facing subtrees, computed gate-side
from the generated payload.

Disclosure: E0c and E0e now assert the same property from the same value. I left
both rather than deleting one, because removing a case is churn beyond the
authorized scope and the redundancy costs nothing. If you want it merged, say so
and it is a one-hunk follow-up.

---

## 3. J6 · inverted by design

Was `regenerated fixture does not match the accepted hash`, expecting a catch.
That comparison no longer exists, so the case as written would have asserted a
catch that can never happen — a mutant that cannot mutate, which is a failure
mode already on this ticket's record.

It now asserts the opposite: a differing whole-file hash produces **no** finding.
That is B03 stated as a regression test, the same shape E7 has for P6-001. J6b is
unchanged and still proves a real payload change moves the canonical digest and
**is** caught, so the pair covers both directions and neither can pass vacuously.

```
✓ J6  a differing whole-file fixture hash is NOT a finding (B03)
✓ J6b generated payload altered -> canonical digest moves
```

---

## 4. Your point about E7, and it is the sharpest thing in the ruling

E7 forges the entire `_evidence` block and asserts the verdict does not move. It
passed before this fix, but it passed **accidentally**: the forgery was applied to
the served object, so `fixture_sha256` still arrived unchanged from the verifier.
Had the same forgery been applied to the artifact on disk, the whole-file
comparison would have fired, which means `_evidence` did still have a path to the
verdict. E7's claim was true of the test as written and false of the mechanism.

With the comparison gone there is no path at all. E7 now asserts what it always
said it asserted.

---

## 5. Full adversarial suite re-run

```
node test_kar093_p6_verify.js --python=<3.11 or 3.12 with pydantic 1.10.13> \
  --pydantic2=<pydantic 2.x> --bundle=. --product=./newphalit_fixed.html

E · execution
  E0a ✓  E0b ✓  E0c ✓  E0e ✓  E0d ✓
  E1  ✓  E2  ✓  E3  ✓  E4  ✓  E5 ✓  E6 ✓  E7 ✓  E8 ✓
J · judgement
  J1 ✓  J2 ✓  J3 ✓  J4 ✓  J5 ✓  J6 ✓  J6b ✓  J7 ✓  J8 ✓  J9 ✓  J10 ✓

RESULT: 24 passed, 0 failed
```

E5 ran this time, so the pydantic-pin refusal is exercised rather than skipped.

---

## 6. What this does not change

`ACCEPTED_P6.modules`, `payloadCanonicalSha256`, `productSha256`, `payloadKeys`,
the 13-edge doctrine oracle, and every other comparison in `judgeP6` are
untouched. The D9 re-pin authorization is separate and still applies once, at
cutover.
