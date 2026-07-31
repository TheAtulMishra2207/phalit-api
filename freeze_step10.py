"""KAR-093 step 10 · interpretation-layer golden freeze.

Calls ONLY the certified modules. No computation of its own, no new logic: it
selects a declared input, runs compute_d1 -> build_d1_drawers, and writes the
result under a header. Shipped so the freeze is reproducible rather than
asserted.

D1 is frozen from the PINNED modules, D9 from the PORTED ones, because those are
the two sets that will actually be in service on either side of the cutover.
"""
import hashlib, json, os, sys, importlib

MODULES = ["d1_contract.py", "d1_engine.py", "d1_functional_roles.py", "d1_synthesis.py"]

# DECLARED INPUT. Lagna Aries, the same nine placements the accepted P6 generator
# uses, so the input is reviewed rather than invented here. The D9 view is a
# DECLARED interpretation-layer input: it is NOT a certified navamsa mapping and
# must never be read as one. Certified astronomy is the /chart golden, separate.
SPEC = {"Sun":(0,12.5,"Moolatrikona"), "Moon":(1,8.2,"Own Sign"),
        "Mars":(9,24.4,"Great Friend"), "Mercury":(5,3.1,"Friend"),
        "Jupiter":(3,15.7,"Neutral"), "Venus":(11,21.3,"Enemy"),
        "Saturn":(6,5.9,"Great Enemy"), "Rahu":(1,17.0,"Debilitated"),
        "Ketu":(7,17.0,"Exalted")}
D9_VIEW = {"Sun":4,"Moon":7,"Mars":1,"Mercury":9,"Jupiter":2,
           "Venus":5,"Saturn":10,"Rahu":6,"Ketu":0}
D9_LAGNA = 3
D9_DIGNITY = "Friend"

SWISS_CERTIFICATE = {
    "chart_engine_version": "1.1.0",
    "ayanamsha_model": "lahiri-linear-fit-2026-07",
    "house_system": "whole-sign",
    "dasha_year_days": 365.2425,
    "node_type": "mean",
    "ephemeris_backend": "swisseph",
    "ephemeris_dataset": "modern-era-se1",
    "ephemeris_dataset_hash":
        "73377f2ff49778826c12346af0626023cff457f85c08d526dc8ebf8627296a65",
    "ephemeris_files": ["semo_18.se1", "sepl_18.se1"],
    "ephemeris_manifest_status": "verified",
    "ephemeris_manifest_enforced": True,
    "supported_year_range": [1800, 2150],
}

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

GOVERNING_KEYS = ["input", "response", "drawers"]

def canon(obj):
    """Defined here, not borrowed. Matches freeze_step10_astronomy.py exactly."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()

def freeze(module_dir, varga_name, subject_path):
    for m in list(sys.modules):
        if m.startswith("d1_"):
            del sys.modules[m]
    sys.path.insert(0, module_dir)
    C  = importlib.import_module("d1_contract")
    E  = importlib.import_module("d1_engine")
    S  = importlib.import_module("d1_synthesis")

    grahas = {}
    for name, (si, deg, dig) in SPEC.items():
        g = C.Graha(name)
        kw = dict(sign_index=si, degree_in_sign=deg, longitude=si * 30 + deg,
                  dignity=C.Dignity(dig), retrograde=False, combust=False,
                  nakshatra="Ashwini", nakshatra_pada=1)
        if varga_name == "D9":
            kw["varga_sign_index"] = D9_VIEW[name]
            kw["varga_dignity"] = C.Dignity(D9_DIGNITY)
        grahas[g] = E.ChartGraha(**kw)
    ckw = dict(chart_token="KAR093STEP10GOLDEN", lagna_sign_index=0,
               lagna_degree=20.0586, grahas=grahas)
    if varga_name == "D9":
        ckw["varga_lagna_sign_index"] = D9_LAGNA
    chart = E.CertifiedChart(**ckw)

    varga = C.Varga(varga_name) if hasattr(C, "Varga") else None
    resp, doc = E.compute_d1(chart, varga) if varga else E.compute_d1(chart)
    drawers = S.build_d1_drawers(
        resp, doc, shadbala_inputs={g: S.ShadbalaInput(value=42.0) for g in C.Graha})

    body = json.loads(resp.json())
    body.pop("generated_at", None)          # clock-dependent, excluded by design
    sys.path.pop(0)
    golden = {
        "_header": {
            "ticket": "KAR-093 step 10",
            "layer": "interpretation",
            "varga": varga_name,
            "subject_html": {"file": os.path.basename(subject_path),
                             "sha256": sha(subject_path)},
            "swiss_certificate": SWISS_CERTIFICATE,
            "modules": {m: sha(os.path.join(module_dir, m)) for m in MODULES},
            "interpreter": {"python": sys.version.split()[0],
                            "pydantic": importlib.import_module("pydantic").VERSION},
            "input_provenance":
                "DECLARED interpretation-layer input. The D1 placements are the "
                "accepted P6 generator's reviewed SPEC. The D9 view is DECLARED, "
                "not a certified navamsa mapping, and must never be read as one. "
                "Certified astronomy is frozen separately by the /chart golden.",
            "excluded": ["response.generated_at (clock-dependent)"],
            # RULING 1, enforced by the artefact rather than remembered as a
            # convention. Comparisons use these subtrees and this digest, NEVER
            # the whole-file hash, which is host-specific through the header.
            "governing_subtree": {
                "keys": GOVERNING_KEYS,
                "digest_definition": "sha256 over json.dumps(sort_keys=True, "
                                     "separators=(',',':'), ensure_ascii=False)",
                "sha256": None,        # filled below, once the parts exist
            },
            "comparison_rule": "Compare the input, response and drawers subtrees "
                               "against governing_subtree.sha256. NEVER the "
                               "whole-file hash.",
            "declared_production_pin": "3.11.0",
            "freeze_interpreter": {"python": sys.version.split()[0],
                                   "pydantic": importlib.import_module("pydantic").VERSION},
            "observed_production_python": None,
        },
        "input": {"lagna_sign_index": 0, "lagna_degree": 20.0586, "spec": SPEC,
                  "d9_view": (D9_VIEW if varga_name == "D9" else None),
                  "d9_lagna_sign_index": (D9_LAGNA if varga_name == "D9" else None),
                  "d9_dignity": (D9_DIGNITY if varga_name == "D9" else None)},
        "response": body,
        "drawers": json.loads(drawers.json()),
    }
    golden["_header"]["governing_subtree"]["sha256"] = canon(
        {k: golden[k] for k in GOVERNING_KEYS})
    return golden

if __name__ == "__main__":
    # ONE LAYER PER PROCESS. pydantic v1 caches validator refs by qualified name
    # globally, so importing a second d1_contract in the same interpreter raises
    # "duplicate validator function". Re-importing under a different name, or
    # setting allow_reuse, would both be edits to certified modules to suit a
    # freeze script. A second process is free and changes nothing.
    subject, module_dir, varga_name, out_path = sys.argv[1:5]
    g = freeze(module_dir, varga_name, subject)
    with open(out_path, "w") as f:
        json.dump(g, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"{varga_name}: {out_path}  sha256 {sha(out_path)}")
