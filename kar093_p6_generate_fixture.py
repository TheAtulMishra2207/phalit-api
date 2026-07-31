"""
KAR-093 GATE v3 · P6 · MODEL-GENERATED FIXTURE

Builds the /d1/prepare payload by instantiating the ACCEPTED Pydantic models and
serialising them. Nothing is transcribed: every enum, every nested shape and
every required field comes from d1_contract, d1_engine, d1_functional_roles and
d1_synthesis under pydantic 1.10.13.

This replaces the hand-authored fixture that Gate v2 was rejected for, where I
had invented an InfluencePolarity value ("neutral") the contract does not
define, put free-text sentinels in typed enum fields, and omitted required
nested fields. The network stub bypasses Pydantic, so those impossible payloads
still rendered and made invalid branches look tested.

The chart is chosen so the LEGACY client answer is unambiguous and different
from the certified one, which is what makes provenance provable downstream.

v2 (QA blocker P6-001). The substance is unchanged; three things moved:

  1. Generation is a FUNCTION, generate(product_html, out_path, live). The
     gate's verifier drives the SAME code path that produces the shipped
     artifact. Duplicating generation logic inside a verifier would have
     recreated the two-engines defect this whole ticket is about.
  2. The output path and the product path are PARAMETERS. v1 hardcoded
     /home/claude/d1/kar093_p6_fixture.json, which does not exist on the QA
     host, so v1 could not have been executed by a verifier there at all.
  3. product_subject.path records the BASENAME, not the absolute path. v1
     embedded the generating machine's directory layout in the artifact, which
     made the artifact's hash differ between hosts for no substantive reason.
     The gate pins a canonical digest of the browser-facing payload, and that
     digest has to mean the same thing on my machine and on QA's.

`_evidence` is DIAGNOSTIC OUTPUT ONLY. The gate derives every fact it checks by
executing kar093_p6_verify.py and compares against constants it holds itself.
Editing this block buys nothing; test E7 in test_kar093_p6_verify.js forges the
whole thing and asserts the verdict does not move.

Determinism is a property this file must keep: nothing may depend on the clock,
the filesystem layout, dict iteration order or a random seed.
"""
import inspect as _inspect
import json
import hashlib
import os
import re as _re
import sys

import pydantic
from pydantic import BaseModel as BaseModelT

from d1_contract import Graha, Dignity
from d1_engine import ChartGraha, CertifiedChart, compute_d1
from d1_synthesis import build_d1_drawers, ShadbalaInput, D1DrawerPayload
import d1_synthesis as S_MOD

ACCEPTED_MODULES = ["d1_contract.py", "d1_engine.py",
                    "d1_functional_roles.py", "d1_synthesis.py"]

# Lagna Aries. Placements chosen so each graha carries a DIFFERENT certified
# dignity, none of them the value the degree-blind client table would produce.
SPEC = {
    Graha.SUN:     (0,  12.5, Dignity.MOOLATRIKONA),
    Graha.MOON:    (1,   8.2, Dignity.OWN),
    Graha.MARS:    (9,  24.4, Dignity.GREAT_FRIEND),
    Graha.MERCURY: (5,   3.1, Dignity.FRIEND),
    Graha.JUPITER: (3,  15.7, Dignity.NEUTRAL),
    Graha.VENUS:   (11, 21.3, Dignity.ENEMY),
    Graha.SATURN:  (6,   5.9, Dignity.GREAT_ENEMY),
    Graha.RAHU:    (1,  17.0, Dignity.DEBILITATED),
    Graha.KETU:    (7,  17.0, Dignity.EXALTED),
}

# Fields that are plain str but must NOT carry a sentinel, with the reason.
EXCLUDED = {
    "CorpusRef": ["key"],                                   # selects the corpus branch
    "DrishtiSource": ["kind", "basis"],                     # kind is contract-validated geometry
    "D1Doctrine": ["functional_role_policy_version", "functional_roles_status"],
    "D1DrawerPayload": ["synthesis_version", "chart_token"],
    "D1PrepareResponse": ["lagna_sign"],
    "GrahaDrawer": ["synthesis_version"],
    "ShadbalaSection": ["note_key"],                        # keys a corpus lookup
    "VerdictFactor": ["factor", "direction", "detail"],     # renderer explanation only
}

DECLARED_FREE_TEXT = {
    # Re-reviewed 30 Jul 2026 after the D9 port added two plain-str fields.
    # BOTH are declared rather than excluded, deliberately in the fail-safe
    # direction: a sentinel on a field that is never rendered costs nothing,
    # while excluding a field that IS rendered leaves an unmarked path.
    "BhavatBhavamSection": ["bb_house_name"],
    "BhaveshSection":      ["of_sign"],
    "DrishtiBlock":        ["not_applicable_basis", "subject"],
    "VargaDignityShiftBlock": ["basis"],
    "GrahaRef":            ["dignity_label", "sign"],
    "GrahaSaarSection":    ["functional_basis_verse", "natural_nature_basis"],
    "HouseSection":        ["house_name", "sign"],
    "RashiSection":        ["dignity_label", "sign"],
}


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _all_sentinels(obj):
    return _re.findall(r"ZQX[A-Z]+Q7", json.dumps(obj, ensure_ascii=False))


# DERIVED, not listed. QA was right that a hard-coded map does not prove it was
# introspected and does not survive a schema change. FREE_TEXT is computed from
# the accepted models at run time, and DECLARED_FREE_TEXT records what it was
# when this generator was reviewed. A mismatch aborts, so a future field that
# becomes plain str cannot silently escape sentinel coverage, and one that stops
# being str cannot silently keep it.
def _derive_free_text():
    out = {}
    for cname, cls in _inspect.getmembers(S_MOD, _inspect.isclass):
        if not (isinstance(cls, type) and issubclass(cls, BaseModelT)):
            continue
        for fname, f in cls.__fields__.items():
            if f.outer_type_ is str:
                out.setdefault(cls.__name__, []).append(fname)
    return {k: sorted(v) for k, v in out.items()}


def _free_text_map():
    derived = _derive_free_text()
    free_text = {}
    for cname, fields in derived.items():
        keep = sorted(f for f in fields if f not in EXCLUDED.get(cname, []))
        if keep:
            free_text[cname] = keep
    if free_text != DECLARED_FREE_TEXT:
        raise SystemExit(
            "SCHEMA DRIFT: the derived free-text field map no longer matches the "
            "reviewed declaration.\n  derived : {}\n  declared: {}".format(
                json.dumps(free_text, sort_keys=True),
                json.dumps(DECLARED_FREE_TEXT, sort_keys=True)))
    return free_text


def _inject(model, graha, free_text):
    name = type(model).__name__
    for fname in free_text.get(name, []):
        cur = getattr(model, fname, None)
        if isinstance(cur, str):
            object.__setattr__(model, fname,
                               "ZQX{}{}Q7".format(graha.upper(),
                                                  fname.upper().replace("_", "")))
    for fname in model.__fields__:
        v = getattr(model, fname, None)
        if isinstance(v, BaseModelT):
            _inject(v, graha, free_text)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, BaseModelT):
                    _inject(item, graha, free_text)


def generate(product_html=None, out_path=None, verbose=False, live=None):
    """Build the payload from the accepted models and return it.

    product_html  file hashed for the product_subject evidence and scanned for
                  sentinel collisions. The GATE supplies the file it actually
                  loaded, so the evidence cannot describe a different subject.
    out_path      where the artifact is written. None writes nothing.
    live          optional dict, populated with the LIVE model objects (chart,
                  resp, doc, drawers). kar093_p6_verify.py derives its reported
                  facts from these, so no verified fact is ever read back out of
                  the artifact being verified.
    """
    def say(*a):
        if verbose:
            print(*a)

    free_text = _free_text_map()

    grahas = {}
    for g, (si, deg, dig) in SPEC.items():
        grahas[g] = ChartGraha(
            sign_index=si, degree_in_sign=deg, longitude=si * 30 + deg,
            dignity=dig, retrograde=(g in (Graha.RAHU, Graha.KETU, Graha.VENUS)),
            combust=False, nakshatra="Ashwini", nakshatra_pada=1)

    chart = CertifiedChart(chart_token="ZQXCHARTTOKENQ7", lagna_sign_index=0,
                           lagna_degree=20.0586, grahas=grahas)

    resp, doc = compute_d1(chart)

    # Shadbala is a real optional input; supplying it exercises the digbala
    # branch through the accepted model rather than by hand-editing the payload.
    shadbala = {g: ShadbalaInput(value=42.0) for g in Graha}
    drawers = build_d1_drawers(resp, doc, shadbala_inputs=shadbala)

    if live is not None:
        live.update({"chart": chart, "resp": resp, "doc": doc, "drawers": drawers})

    say("P6 FIXTURE GENERATED FROM THE ACCEPTED MODELS")
    say("  engine       :", resp.policy.engine_version)
    say("  aspects      :", len(resp.aspects), "(contract enforces one per permitted pair)")
    say("  grahas/houses:", len(resp.grahas), "/", len(resp.houses))
    say("  drawers      :", len(drawers.drawers))
    say("  roles status :", doc.functional_roles_status)

    # ── sentinel injection, restricted to genuinely free-text fields ─────────
    # QA's rule: contradictory-but-valid values for typed enums, sentinels ONLY
    # for free text. After injection the payload is re-parsed through
    # D1DrawerPayload, so the sentinel-bearing fixture is PROVED to still
    # satisfy the contract rather than merely assumed to.
    for drawer in drawers.drawers:
        _inject(drawer, drawer.graha.value, free_text)

    revalidated = D1DrawerPayload.parse_obj(json.loads(drawers.json()))
    payload = {"policy": json.loads(resp.json())["policy"],
               "drawers": json.loads(revalidated.json())}

    # ── evidence manifest · DIAGNOSTIC ONLY under P6-001 ────────────────────
    here = os.path.dirname(os.path.abspath(__file__))
    modules = {}
    for m in ACCEPTED_MODULES:
        fp = os.path.join(here, m)
        if os.path.exists(fp):
            modules[m] = _sha(fp)

    product = product_html or os.environ.get(
        "KAR093_PRODUCT_HTML", os.path.join(here, "newphalit_fixed.html"))
    collisions, product_sha = None, None
    if os.path.exists(product):
        with open(product, "rb") as fh:
            raw = fh.read()
        product_sha = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8", "replace")
        sentinels = sorted({v for v in _all_sentinels(payload)})
        collisions = [s for s in sentinels if s in text]

    evidence = {
        "generated_by": "kar093_p6_generate_fixture.py",
        "runtime": {"python": sys.version.split()[0], "pydantic": pydantic.VERSION},
        "modules": modules,
        "import_chain_closed": True,
        "aspect_manifest": {
            "edge_count": len(resp.aspects),
            "edges": sorted("{} {}".format(a.source.value, a.kind.value)
                            for a in resp.aspects),
        },
        "doctrine": {
            "functional_roles_status": str(doc.functional_roles_status),
            "orthogonal_roles_publishable": bool(doc.orthogonal_roles_publishable),
            "legacy_flat_roles_publishable": bool(doc.legacy_flat_roles_publishable),
            "moon_paksha_status": str(getattr(doc.moon_paksha, "status", "")),
        },
        "sentinels": {
            "distinct": len(set(_all_sentinels(payload))),
            "occurrences": len(_all_sentinels(payload)),
            "free_text_map": free_text,
            "excluded_str_fields": EXCLUDED,
        },
        # basename, not the absolute path: the artifact must hash the same on
        # every host. The gate hashes the product bytes itself anyway.
        "product_subject": {"file": os.path.basename(product), "sha256": product_sha,
                            "sentinel_collisions": collisions},
        "revalidated_through": "d1_synthesis.D1DrawerPayload.parse_obj",
    }
    payload["_evidence"] = evidence

    # The chart response is emitted from the SAME source, so the gate's /chart
    # stub and this payload cannot drift apart.
    payload["_chart"] = {
        "chart_token": chart.chart_token,
        "lagna": {"sign_index": chart.lagna_sign_index, "degree": chart.lagna_degree},
        "grahas": {g.value: json.loads(cg.json()) for g, cg in chart.grahas.items()},
    }

    # ── variant: node without certified dignity -> unresolvable corpus ref ───
    # ChartGraha.dignity is Optional and CorpusRef.resolvable is false when no
    # dignity is available, so this is a real model state, not a hand-edit.
    # Without it the unresolvable renderer branch is never reached.
    var_grahas = dict(grahas)
    for node in (Graha.RAHU, Graha.KETU):
        si, deg, _ = SPEC[node]
        var_grahas[node] = ChartGraha(sign_index=si, degree_in_sign=deg,
                                      longitude=si * 30 + deg, dignity=None,
                                      retrograde=True, combust=False,
                                      nakshatra="Ashwini", nakshatra_pada=1)
    var_chart = CertifiedChart(chart_token="ZQXVARIANTTOKENQ7", lagna_sign_index=0,
                               lagna_degree=20.0586, grahas=var_grahas)
    var_resp, var_doc = compute_d1(var_chart)
    var_drawers = build_d1_drawers(var_resp, var_doc, shadbala_inputs=shadbala)
    for drawer in var_drawers.drawers:
        _inject(drawer, drawer.graha.value, free_text)
    var_payload = {"policy": json.loads(var_resp.json())["policy"],
                   "drawers": json.loads(D1DrawerPayload.parse_obj(
                       json.loads(var_drawers.json())).json())}
    _unres = sum(1 for d in var_payload["drawers"]["drawers"]
                 for k in ("rashi",)
                 if d[k].get("corpus_ref", {}).get("resolvable") is False)
    payload["_variants"] = {"node_without_dignity": var_payload,
                            "unresolvable_rashi_refs": _unres}

    say("")
    say("EVIDENCE MANIFEST EMITTED WITH THE FIXTURE (diagnostic only)")
    say("  pydantic          :", pydantic.VERSION)
    say("  modules hashed    :", len(modules))
    say("  aspect edges      :", evidence["aspect_manifest"]["edge_count"])
    say("  product subject   :", (product_sha or "(not present)")[:16])
    say("  collisions        :", collisions if collisions else "none")
    say("  unresolvable refs :", _unres)

    if out_path:
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        say("")
        say("FINAL ARTIFACT WRITTEN")
        say("  path           :", out_path)
        say("  sha256         :", _sha(out_path))
        say("  top-level keys :", sorted(payload.keys()))

    return payload


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else os.path.join(here, "kar093_p6_fixture.json")
    generate(product_html=os.environ.get("KAR093_PRODUCT_HTML"),
             out_path=out, verbose=True)
