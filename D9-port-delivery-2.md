# D9 backend port · delivery 2 of 2 · synthesis

30 July 2026. `d1_synthesis.py` parameterised. The backend port is complete
except for one thing that is page-side and named in §6.

| Transport name | Target name | SHA-256 | newlines | bytes |
|---|---|---|---|---|
| `D9PORT_d1_synthesis.py` | `d1_synthesis.py` | `8fed4f85dfe30eb97efe659ff8ac3511df6d6c9568732790474068874a463216` | 651 | 30,382 |

Pinned set still untouched: `c2809d4a`, `2e028771`, `7689984f`, `10841e99`.
Sequencing unchanged: nothing replaces them until QA certifies.

---

## 1. A defect I introduced and caught before shipping

`DrishtiBlock.applicability` was declared `Literal["applicable","not_applicable"]`
while `Literal` was **not imported** in that module. Pydantic left the field as an
unresolved `ForwardRef` and validated nothing. The module imported cleanly and
every functional test passed, because the field still held the right values.

```
before : applicability field type: ForwardRef("Literal['applicable',...]")
         DrishtiBlock(applicability='bogus')  ->  ACCEPTED
after  : applicability field type: typing.Literal['applicable','not_applicable']
         DrishtiBlock(applicability='bogus')  ->  refused
```

This is the ticket's signature defect wearing a new hat: a declared constraint
with nothing behind it, green all the way. Recording it because the only reason
it did not ship is that I probed the field object instead of trusting that the
import succeeded.

---

## 2. The marked not-applicable state

`DrishtiBlock` gains `applicability` and `not_applicable_basis`.

`_drishti_block` branches on **the policy**, not on whether the manifest happens
to be empty. That distinction is the whole point: under `"none"` the contract
already forces `aspects == []`, so a source-count test would have produced
`UNASSESSED` and collapsed the two states exactly as warned.

Measured across all three drishti blocks in every drawer:

```
D1  house/bhavesh/graha_saar   net=mixed|challenging     applicability=applicable
D9  house/bhavesh/graha_saar   net=not_applicable        applicability=not_applicable
    basis: graha-dṛṣṭi is not cast in D9 (varga_aspect_policy=none);
           this is doctrine, not an absence of evidence

D9 net is NOT_APPLICABLE, not UNASSESSED : True
D9 sources empty AND state marked        : True
D1 never marked not_applicable           : True
```

**The verdict explanation states it rather than going silent.** A
`VerdictFactor(factor="house_drishti", direction="not_applicable")` is emitted in
D9. Silence would have read as "evaluated, found neutral". It carries no
direction, so it neither creates nor blocks a verdict.

`_overall_verdict` needed no change to its decision table, and I checked rather
than assumed: `is_strong` tests `house_net not in (CHALLENGING, MIXED)`, so
`NOT_APPLICABLE` is excluded from the arithmetic instead of counted as zero. The
table was already correct by construction.

---

## 3. Corpus refs carry the varga

`CorpusRef.varga` selects which corpus **table** the renderer reads. `CorpusName`
stays the kind of lookup. Keeping them orthogonal means D10 adds a `Varga` member
and no `CorpusName` members, the same reasoning that made the policy key
`varga_aspect_policy` rather than `d9_aspect_policy`.

Stamped in **one** place, `_stamp_varga`, which walks the built payload
recursively. Passing the varga into each corpus-ref construction site would work
today and be silently incomplete the first time a fifth section gains one. The
parity table below shows it reaching all four refs per drawer, including
`bhavat_bhavam` and `bhava_karaka`, which I did not enumerate anywhere.

---

## 4. Two things deliberately not done

**`SYNTHESIS_VERSION` is not bumped.** Bumping it changes a *value* in the D1
payload, and the D1 regression property that matters is added fields only, zero
changed values. The varga is a new field instead.

**`build_d1_drawers` keeps its name.** The generator, the gate fixture and the
route all call it. Renaming it would ripple through four accepted artifacts to
say the same thing. It builds drawers for whatever varga the response declares.

---

## 5. D1 regression · exact, again

Full D1 drawer payload through pinned modules vs ported modules:

```
added fields   : 118
changed/removed: 0

  /varga                                          x1
  /drawers[]/varga                                x9
  /drawers[]/rashi/corpus_ref/varga               x9
  /drawers[]/house/corpus_ref/varga               x9
  /drawers[]/bhavat_bhavam/corpus_ref/varga       x9
  /drawers[]/bhava_karaka/corpus_ref/varga        x9
  /drawers[]/house/drishti/applicability          x9   (+ not_applicable_basis x9)
  /drawers[]/bhavesh/drishti/applicability        x9   (+ not_applicable_basis x9)
  /drawers[]/graha_saar/house_drishti/…           x9   (+ …)
  /drawers[]/graha_saar/bhavesh_drishti/…         x9   (+ …)
```

Both vargas re-parse through `D1DrawerPayload`.

---

## 6. The one thing left, and it is page-side

**The D9 corpus prose does not exist yet, and I did not write it.**

What this delivery supplies is the D9 corpus *reference*: corpus name, key,
graha, dignity, `resolvable`, and now `varga`. The prose tables themselves live
in `newphalit.html` as `D1_RASHI_CORPUS`, `HOUSE_CORPUS` and the rest, and the
page is out of scope for this pass.

So the backend is complete and a D9 drawer rendered today would resolve every
reference against D1 prose. That is wrong content behind a correct contract, and
it needs one of:

- you supply the D9 prose tables and I stage them for the cutover, or
- the cutover ticket writes them alongside `openD9Drawer`, or
- D9 launches with `resolvable: false` on prose-bearing refs until the corpus
  exists, which is honest but renders empty sections.

Flagging rather than choosing, because it is content doctrine, not engineering.

---

## 7. State

Backend port done. Contract, engine and synthesis parameterised;
`d1_functional_roles.py` needed no change. Nothing has been re-pinned, no module
replaced, `openD9Drawer` untouched.
