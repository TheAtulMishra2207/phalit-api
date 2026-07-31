# KAR-093 · D9 cutover · verification run

## 1. Verify the subject before anything else

    sha256sum newphalit_fixed.html

Must be `c475284dd5da80daae757e8702b3bf837715ae646ed6e93100c3d3e6335ca252`
(34,657 newlines, 2,504,020 bytes). Every other pin is in `MANIFEST.txt`.

## 2. The manifest describes this archive exactly

31 of 31 listed entries verified byte-for-byte before packing. Column widths are
normalised so a fixed-width parser reads every row.

`test_kar093_p6_verify.js` is recorded under NOT SHIPPED IN THIS ARCHIVE with its
accepted hash and the reason. It is the P6 adversarial suite, not a gate
component: `kar093_gate3.js` does not require it and the certifying run does not
load it. Listing it as shipped when it was not is the inconsistency you correctly
stopped on, and the manifest now says what is true.

## 3. You already hold these — do not re-extract

`phalit-py311/` (CPython 3.11.12 + pydantic 1.10.13) and
`node_modules/playwright-core` (1.57.0). Extract this archive beside them.

## 4. Clear stale temp artifacts (KAR-093-B02)

    rm -f "${TMPDIR:-/tmp}/kar093_p6_result.json" "${TMPDIR:-/tmp}/kar093_p6_fixture.generated.json"

## 5. The certifying run

    nohup node kar093_gate3.js newphalit_fixed.html \
      --driver=playwright \
      --executable=/usr/bin/chromium \
      --python=./phalit-py311/bin/python3 > gate.log 2>&1 &

Run detached; the previous full run exceeded a five-minute cap. Poll with
`sleep 120; tail -40 gate.log`. Confirm the post-launch line reads
`playwright-core 1.57.0`. Do NOT use `KAR093_P6=0`.

## 6. Then the four release gates

    node validate_corpus.js newphalit_fixed.html
    node test_kar079_nichart.js newphalit_fixed.html
    node test_kar091_corpus.js newphalit_fixed.html kar091_reviewed_manifest.json
    node test_kar093_d1_cutover.js newphalit_fixed.html

and the KAR-091 rebind:

    node kar091_review_manifest.js newphalit_fixed.html kar091_reviewed_manifest.json <new-out.json>

PREDICTION to judge that against: it should carry all 1,740 dispositions forward
with 0 new and 0 drift, only `source_file_sha256` changing. The D9 corpus sits
outside `collectMaleficYogas` / `collectBeneficYogas`, so the extractor does not
see it. If it reports new entries, STOP and report rather than dispositioning.

## 7. Two disclosures in MANIFEST.txt are deliberate

The goldens stamp four module hashes while the gate pins five, because
`freeze_step10.py` never calls the adapter. And the coverage statement names what
the fixture does NOT prove: the dignity collapse behaviour (unreachable from the
live engine) and `vargottama: true` (absent from the chart of record).

## 8. Report

Result per phase, the certifying verdict, the four gate results, the rebind
result, and any release-blocking product finding. Bar unchanged: wrong doctrine,
wrong computation, or a client engine contradicting the server on the same screen.
