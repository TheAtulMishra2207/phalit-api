# KAR-093 step 10 · interpretation layer frozen

30 July 2026. Interpretation layer done. Astronomy layer waits on the `/chart`
capture, as ruled.

| File | SHA-256 | newlines | bytes |
|---|---|---|---|
| `KAR-093-step10-golden-D1.json` | `82aa86d3cc1acdab12eeb3b89cf1e352793dfc11c9dac34da7943bfc2f155ea6` | 2,723 | 79,553 |
| `KAR-093-step10-golden-D9.json` | `74504ead9d63da7c9965f528d76fca31dd217f2dd8bb6ffdda63c13a7fe72076` | 2,275 | 70,039 |
| `freeze_step10.py` | `25aed7b9f61f25150b1dc529f1020246f0c4e05a103b6d8a4ccb0785aaf29160` | 117 | 5,539 |

The freeze script ships so the freeze is reproducible rather than asserted. It
calls only certified module functions and contains no computation of its own.

**Both goldens regenerate byte-identically.** Verified by generating each twice
and comparing hashes. `response.generated_at` is excluded and the exclusion is
named in the header, because it is clock-dependent and would make the freeze
unreproducible by construction.

---

## 1. What each golden is stamped with

```
D1   modules  contract=c2809d4a engine=2e028771 roles=7689984f synthesis=10841e99   (PINNED)
D9   modules  contract=88b9392f engine=9ae0a02c roles=7689984f synthesis=8fed4f85   (PORTED)

both subject  newphalit_fixed.html  93a5caeb29dece1c
both swiss    chart_engine_version 1.1.0, lahiri-linear-fit-2026-07, whole-sign,
              365.2425, mean, swisseph, modern-era-se1,
              ephemeris_dataset_hash 73377f2ff4977882…, [semo_18.se1, sepl_18.se1],
              manifest verified + enforced, supported_year_range [1800, 2150]
both interp   python 3.12.3, pydantic 1.10.13
```

`d1_functional_roles.py` is `7689984f` on both sides, which is the freeze
recording that the port did not touch it.

Content check: D1 froze 13 edges and 9 drawers; D9 froze 0 edges, 9 drawers,
`varga_aspect_policy=none`, drishti `not_applicable` on both the value and the
applicability field, and corpus refs tagged `varga: D9`.

---

## 2. A difference between the two goldens that you should expect

The D1 golden's `policy` block has five keys. The D9 golden's has eight, and D1
has no `birth_lagna_sign_index`. That is not a defect: the D1 golden was frozen
from the **pinned** modules, which predate the varga fields.

The consequence matters for how the golden gets used. **After the cutover
replaces the modules, re-running D1 through the ported stack will produce a
payload that differs from this golden by exactly the added fields already
measured: 16 on the response and doctrine, 118 on the drawer payload, zero
changed values.** So either the D1 golden is re-frozen at cutover, or whatever
compares against it must be added-fields-tolerant.

My recommendation is re-freeze at cutover, in the same pass as the P6 re-pin, and
keep both files so the pre-cutover D1 stays reproducible. An added-fields-tolerant
comparator is a detector with a hole in it, and this ticket has enough of those on
record.

---

## 3. What this does NOT freeze, stated plainly in the header

The input is declared, not certified. The D1 placements are the accepted P6
generator's reviewed SPEC, so they are reviewed rather than invented here. **The
D9 view in this golden is a DECLARED interpretation-layer input and is not a
certified navamsa mapping.** The header says so in those words, because a future
reader finding nine navamsa sign indices in a file called "golden" would
reasonably assume otherwise.

What is frozen is the interpretation layer's behaviour given a declared input.
Certified astronomy is the `/chart` golden, and it is separate for the reason you
gave: a locally computed chart proves the local install matches the certificate,
not that production does.

---

## 4. Corpus re-screened here, not carried

Run with your `kar091_classify.js`, against all 91 entries extracted from the
workbook:

```
screened      : 91
flagged       : 0
high-risk hits: 0
dispositions required: 0
```

Independently reproduced. The corpus enters KAR-091 clean.

### And a second extractor trap, worse than the footnote

My first extraction returned **82**, not 91. Nine dignity rows were silently
dropped, one per graha, all of them the `Own Sign` tier:

```
row_id       RASHI-Sun-Own_Sign     (underscore)
dignity_label  Own Sign             (space)
```

The `row_id` underscores the space; the `dignity_label` column does not. So a
lookup table built by joining `RASHI-{graha}-{dignity_label}` misses tier 2 for
all nine grahas, and misses it *silently*, returning nothing rather than raising.

**The corpus table must key off the authoritative `graha` and `dignity_label`
columns, not off `row_id`.** `row_id` is a spreadsheet convenience. I will build
it that way at cutover, and the builder will assert 9 x 7 and 9 x 3 completeness
so a silent drop cannot recur.

Not a defect in your workbook. It is a defect in the obvious way to read it, and
it would have shipped as nine missing corpus entries.

---

## 5. State

Interpretation layer frozen. Astronomy layer blocked on the `/chart` and
`/health` capture, and correctly so. If `/health` does not match the
fixture-freeze certificate, this note's Swiss block is what it should be compared
against: it is embedded verbatim in both golden headers.
