# D9 backend port · delivery 1 of 2 · contract and engine

30 July 2026. Contract and engine parameterised. `d1_functional_roles.py` needed
no change. `d1_synthesis.py` is delivery 2, the D9 drawer sections and corpus.

---

## 1. Files

| Transport name | Target name in the repo | SHA-256 | newlines | bytes |
|---|---|---|---|---|
| `D9PORT_d1_contract.py` | `d1_contract.py` | `88b9392f813261b443508c20e1f774f59303ca54d5e930e2838859dff095fa39` | 321 | 15,300 |
| `D9PORT_d1_engine.py` | `d1_engine.py` | `9ae0a02c8c04ca1ae636df6a31001f7210412d4f8f4d5113ff87a19e4502d69e` | 532 | 28,126 |
| `test_kar093_d1_cutover.js` | same | `1ed17cfed7bf99a1490dc47a32cf6c1b0f69124c784782be1b0e876b7ab58d19` | 307 | 17,105 |

The `D9PORT_` prefix exists only for transport. Four custody failures in two days
were all confusion between same-named files at different revisions, so nothing
ships under a pinned name.

**Sequencing, and it matters.** These replace the pinned modules only **after QA
certifies step 9**. The gate holds `ACCEPTED_P6.modules` and the fixture pin
`b38e4990`; dropping these into the repo root before certification breaks P6 on
QA's host with a module hash mismatch. The four pinned copies in the bundle
directory are untouched and still hash to `c2809d4a`, `2e028771`, `7689984f`,
`10841e99`.

---

## 2. What the ruling became in code

```python
class Varga(str, Enum):
    D1 = "D1"
    D9 = "D9"

VARGA_ASPECT_POLICY = {Varga.D1: "parashari_full", Varga.D9: "none"}
```

`EnginePolicy` gains `varga`, `varga_aspect_policy: Literal["parashari_full","none"]`
and `functional_role_lagna_anchor: Literal["birth_lagna"]`. The key is not
D9-prefixed, so D10 is a new enum member and a new mapping row, never a rename.
A third aspect position later is a new explicit value.

**The pairing is enforced, not defaulted.** A root validator refuses any policy
whose `varga_aspect_policy` is not the one its varga declares, in both
directions. `Varga.D9` with `parashari_full` is invalid, and so is `Varga.D1`
with `none`. Proved:

```
refused : varga D9 carries varga_aspect_policy='none', not 'parashari_full'
refused : varga D1 carries varga_aspect_policy='parashari_full', not 'none'
```

---

## 3. Constraint 1 · the policy is enforced by the contract

`_complete_and_consistent` branches. Under `"none"` an empty manifest is
**required**, not permitted, and no house may record an aspecting graha. Under
`"parashari_full"` the exact 13-edge check is untouched.

Four probes, because a gate that only ever sees a correct payload proves nothing:

```
M1  D9 payload carrying one real edge      -> refused: manifest carries 1 edge(s)
M2  D9 payload with houses[0].aspected_by  -> refused: houses [1] record aspected_by
M3  D1 payload with 12 of 13 edges         -> refused: missing edge
    clean D9 revalidates
    clean D1 revalidates
```

M3 is there deliberately: the branch must not have loosened the D1 path while
adding the D9 one.

---

## 4. Constraint 2 · `NOT_APPLICABLE` is not `UNASSESSED`

`InfluencePolarity.NOT_APPLICABLE` added as a distinct member, documented at the
definition site as doctrine saying there is nothing to resolve, against
`UNASSESSED` meaning the doctrine could not be resolved.

- **Aggregation excludes it.** `build_house_influences` filters both
  `UNASSESSED` and `NOT_APPLICABLE` out of the assessed set, so neither can act
  as a zero-weight vote that dilutes a net.
- **Declared path for binding.** `HouseInfluence.drishti_applicability:
  Literal["applicable","not_applicable"]`. P3 gets a marked leaf rather than an
  unmarked one, and the drawer has something to render an explicit state from.
  Measured: D9 gives `{'not_applicable'}` across all twelve houses, D1 gives
  `{'applicable'}`.
- The D9 drawer's explicit marked state is delivery 2. This delivery supplies the
  field it binds to; it does not yet render it.

A house with no occupants and no drishti in D9 is still `UNASSESSED`, not
`NOT_APPLICABLE`. Absence of grahas is absence of data. Only the drishti
dimension is doctrinally not-applicable, which is why the state lives on its own
field rather than being smeared into `net`.

---

## 5. How the varga actually flows

One certified snapshot carries every view. `ChartGraha` gains
`varga_sign_index` and `varga_dignity`; `CertifiedChart` gains
`varga_lagna_sign_index`. `compute_d1(chart, varga)` selects a view and computes
the whole thing from it. The snapshot, `chart_token`, session, resolver and
adapter are unchanged; this is extra certified fields on the object they already
pass around.

The engine still computes no astronomy. Requesting `Varga.D9` without the varga
view raises `D1EngineError` rather than deriving the navamsa mapping, because
astronomy and dignity come from chart engine 1.1.0 only.

**Three things the varga is deliberately withheld from:**

1. **Functional roles.** `resolve_functional_roles` and `_bphs34_roles` both read
   `birth_lagna_idx`, never the varga lagna. Your ruling.
2. **Moon pakṣa.** Computed from true sidereal longitudes, which every view
   shares, so it is anchored by construction rather than by discipline. It cannot
   drift even if a caller gets the varga wrong.
3. **Natural nature.** A property of the graha.

`birth_lagna_sign_index` is published on the response so
`functional_role_lagna_anchor` is checkable rather than asserted.

Measured on the chart of record, Libra lagna:

```
D1: varga=D1 policy=parashari_full edges=13 lagna=6 birth_lagna=6
D9: varga=D9 policy=none          edges=0  lagna=3 birth_lagna=6
D9 Mars sign: Taurus   |  D1 Mars sign: Capricorn
functional roles identical across both views: True
moon paksha identical across both views: True (waxing)
D9 evidence contains zero drishti entries: True
```

Mars Libra 24.4068 landing in D9 Taurus matches the test chart of record.

---

## 6. D1 regression · exact parity

The same D1 chart through the pinned modules and through the ported modules,
whole response and whole doctrine block compared field by field:

```
16 differences, ALL of them ADDED fields, zero changed values, zero removals

  /resp/birth_lagna_sign_index
  /resp/policy/varga
  /resp/policy/varga_aspect_policy
  /resp/policy/functional_role_lagna_anchor
  /doc/house_influences[0..11]/drishti_applicability
```

Nothing the D1 path already produced has moved.

---

## 7. Cutover suite, repaired and shipped with this

`test_kar093_d1_cutover.js` threw `ReferenceError: d1Esc is not defined`.
Reproduced first, then three exact-once edits and nothing else: extract
`d1Esc` from the page with the suite's own `fnBody`, inject it into both
evaluated blocks, throw if the page does not carry it. Not stubbed.

```
was : e338a9e3457f34ef6cf2a2cb858cb05bebd8575b62ca787897c930276547f6c8   297 nl   16,579 b
now : 1ed17cfed7bf99a1490dc47a32cf6c1b0f69124c784782be1b0e876b7ab58d19   307 nl   17,105 b

node test_kar093_d1_cutover.js newphalit_fixed.html   ->   94/94 assertions passed
```

38 call sites for `d1Esc`, not 34. The guard throws rather than asserting, so it
fails loudly without changing the assertion count.

---

## 8. Delivery 2

`d1_synthesis.py`: the D9 drawer sections and corpus, including the explicit
marked not-applicable drishti state. `openD9Drawer` stays out; it edits
`newphalit.html` and waits for step 9.

One thing to decide before the frontend cutover, not now. Verification is gate v3
with a D9 fixture, but a D9 fixture generated from these modules changes
`ACCEPTED_P6.modules` and the fixture pins, and those live in
`kar093_p6_bind.js`. Re-pinning is a gate edit. The freeze says no gate changes,
so either the re-pin is an explicit exception or the D9 fixture run needs a
different arrangement. Flagging it now rather than discovering it at cutover.
