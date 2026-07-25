# Phalit D1 QA bundle — 2026-07-25 (KAR-091 v7 closed + KAR-079)

newphalit.html here = KAR-088 + KAR-091 v7 (accepted) + KAR-079 rasi numerals.
kar091_reviewed_manifest.json is REBOUND to this exact HTML — do not mix with
the manifest from the earlier v7 archive.

    node test_kar091_corpus.js newphalit.html kar091_reviewed_manifest.json   # 32/32
    node test_kar079_nichart.js newphalit.html                                # 9/9
    node kar091_audit.js newphalit.html kar091_reviewed_manifest.json         # gate
    node validate_corpus.js newphalit.html                                    # KAR-088

acorn 8.15.0 vendored; `npm ci` also works. After ANY future edit to
newphalit.html: node kar091_review_manifest.js newphalit.html kar091_reviewed_manifest.json
