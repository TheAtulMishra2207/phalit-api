#!/usr/bin/env python3
"""
KAR-093 GATE v3 · P6 VERIFIER  (answers QA blocker P6-001)

WHAT WAS WRONG. Gate v3 read `_evidence` out of kar093_p6_fixture.json and set
phaseResults.P6 from it. The fixture was both the subject and the witness, so
P6 meant "the JSON says it was model-generated", not "this gate demonstrated
it". A hand-written fixture with a forged `_evidence` block passed.

WHAT THIS IS. A subprocess the gate runs DURING the gate run. It executes the
accepted generator against the accepted modules and REPORTS WHAT IT OBSERVED.
It renders no verdict of its own about what is acceptable.

  verifier  = mechanism. Derives facts by execution.
  gate      = oracle. Holds the accepted constants and does the comparing.

That split is deliberate. If the accepted hashes lived in here, this file would
be asserting its own correctness, which is the same shape as the defect being
fixed. kar093_gate3.js declares ACCEPTED_P6 and compares every field below
against it.

EVERY REPORTED FACT IS DERIVED BY EXECUTION, NEVER READ BACK OUT OF THE
ARTIFACT. The aspect edges come from the live AspectEdge objects, the doctrine
flags from the live D1Doctrine, the product hash from the bytes at the path the
GATE passed in, and the collisions from those same bytes. Nothing here consults
payload["_evidence"], which is now diagnostic output only.

Usage:
  python3 kar093_p6_verify.py --product=<newphalit_fixed.html>
                              --out=<fixture.json to write>
                              --result=<result.json to write>
                              [--modules=<dir containing the four d1_*.py>]
                              [--shipped=<fixture.json shipped in the bundle>]

Exit 0  generation completed and the result file was written. The gate still
        has to accept the reported facts; exit 0 is NOT a P6 pass.
Exit 1  hard failure. No payload exists, so the gate has nothing to test with.
"""
import hashlib
import json
import os
import re
import sys
import traceback

ACCEPTED_MODULE_FILES = ["d1_contract.py", "d1_engine.py",
                         "d1_functional_roles.py", "d1_synthesis.py",
                         # D9 port: the adapter is the seam that turns a live
                         # /chart response into engine input. It is NOT in the
                         # fixture's construction path (the generator builds
                         # CertifiedChart from its declared SPEC), so it is
                         # hashed AND imported here so the pin is backed by the
                         # same evidence as its neighbours rather than by a bare
                         # digest.
                         "d1_chart_adapter.py"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def arg(name, default=None):
    pref = "--" + name + "="
    for a in sys.argv[1:]:
        if a.startswith(pref):
            return a[len(pref):]
    return default


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    modules_dir = os.path.abspath(arg("modules", here))
    product = arg("product")
    out_path = arg("out", os.path.join(here, "kar093_p6_fixture.json"))
    result_path = arg("result", os.path.join(here, "kar093_p6_result.json"))
    shipped = arg("shipped")

    result = {
        "verifier": "kar093_p6_verify.py",
        "ok": False,
        "errors": [],
        "runtime": {},
        "modules": {},
        "import_chain": {},
        "generated": {},
        "product": {},
        "shipped_fixture": {},
    }

    def fail(msg):
        result["errors"].append(msg)

    def emit(code):
        try:
            with open(result_path, "w") as fh:
                json.dump(result, fh, indent=2, ensure_ascii=False, sort_keys=True)
        except Exception as exc:                      # pragma: no cover
            sys.stderr.write("could not write result file: %r\n" % (exc,))
            return 1
        return code

    # ── runtime ─────────────────────────────────────────────────────────────
    result["runtime"]["python"] = sys.version.split()[0]
    result["runtime"]["executable"] = sys.executable
    try:
        import pydantic
        result["runtime"]["pydantic"] = pydantic.VERSION
    except Exception as exc:
        fail("pydantic is not importable: %r" % (exc,))
        return emit(1)

    # ── hash the module FILES before importing anything ─────────────────────
    for name in ACCEPTED_MODULE_FILES:
        fp = os.path.join(modules_dir, name)
        entry = {"path": fp, "present": os.path.exists(fp)}
        if entry["present"]:
            entry["sha256"] = sha256_file(fp)
        else:
            fail("accepted module missing: %s" % fp)
        result["modules"][name] = entry
    if any(not e["present"] for e in result["modules"].values()):
        return emit(1)

    # ── import, then prove the import resolved to the files just hashed ─────
    # Hashing a path and importing a name are two different operations. If
    # sys.path resolves the name somewhere else, the hash describes a file that
    # took no part in the run. Comparing realpaths closes that gap.
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)
    try:
        import d1_contract
        import d1_engine
        import d1_functional_roles
        import d1_synthesis
        import d1_chart_adapter
        import kar093_p6_generate_fixture as GEN
    except Exception as exc:
        fail("import of the accepted modules failed: %r" % (exc,))
        result["traceback"] = traceback.format_exc()
        return emit(1)

    loaded = {
        "d1_contract.py": d1_contract,
        "d1_engine.py": d1_engine,
        "d1_functional_roles.py": d1_functional_roles,
        "d1_synthesis.py": d1_synthesis,
        "d1_chart_adapter.py": d1_chart_adapter,
    }
    for name, mod in loaded.items():
        imported_from = os.path.realpath(getattr(mod, "__file__", "") or "")
        result["modules"][name]["imported_from"] = imported_from
        result["modules"][name]["path_matches_import"] = (
            imported_from == os.path.realpath(result["modules"][name]["path"]))
    result["generator_file"] = os.path.realpath(getattr(GEN, "__file__", "") or "")

    # ── import chain closed: one contract underlies all three consumers ─────
    # `import_chain_closed: true` was a literal in the old evidence block. It is
    # derived here from object identity: if d1_engine and d1_synthesis each
    # carried their own copy of Graha, the enum members would not be the same
    # objects and a payload valid to one could be invalid to the other.
    try:
        base = d1_contract.Graha
        result["import_chain"] = {
            "engine_shares_contract_graha": d1_engine.Graha is base,
            "synthesis_shares_contract_graha": getattr(d1_synthesis, "Graha", None) is base,
            "roles_shares_contract_graha": getattr(d1_functional_roles, "Graha", None) is base,
            "generator_shares_contract_graha": getattr(GEN, "Graha", None) is base,
            "adapter_shares_contract_graha": getattr(d1_chart_adapter, "Graha", None) is base,
        }
        result["import_chain"]["closed"] = all(result["import_chain"].values())
    except Exception as exc:
        fail("import chain check failed: %r" % (exc,))
        return emit(1)

    # ── generate through CertifiedChart -> compute_d1 -> build_d1_drawers ────
    live = {}
    try:
        payload = GEN.generate(product_html=product, out_path=out_path, live=live)
    except SystemExit as exc:
        fail("generator aborted: %s" % (exc,))
        return emit(1)
    except Exception as exc:
        fail("generation raised: %r" % (exc,))
        result["traceback"] = traceback.format_exc()
        return emit(1)

    resp, doc, drawers = live.get("resp"), live.get("doc"), live.get("drawers")
    if resp is None or doc is None or drawers is None:
        fail("the generator did not expose its live model objects")
        return emit(1)

    # Facts from the LIVE objects.
    result["generated"]["fixture_path"] = out_path
    result["generated"]["fixture_sha256"] = sha256_file(out_path)
    result["generated"]["chart_token"] = live["chart"].chart_token
    result["generated"]["engine_version"] = resp.policy.engine_version
    result["generated"]["aspect_policy_version"] = resp.policy.aspect_policy_version
    result["generated"]["node_aspect_policy"] = resp.policy.node_aspect_policy
    result["generated"]["graha_count"] = len(resp.grahas)
    result["generated"]["house_count"] = len(resp.houses)
    result["generated"]["drawer_count"] = len(drawers.drawers)
    result["generated"]["aspect_edges"] = sorted(
        "%s %s" % (a.source.value, a.kind.value) for a in resp.aspects)
    result["generated"]["edge_count"] = len(resp.aspects)
    result["generated"]["doctrine"] = {
        "functional_roles_status": str(doc.functional_roles_status),
        "orthogonal_roles_publishable": bool(doc.orthogonal_roles_publishable),
        "legacy_flat_roles_publishable": bool(doc.legacy_flat_roles_publishable),
    }
    result["generated"]["unresolvable_rashi_refs"] = (
        payload.get("_variants", {}).get("unresolvable_rashi_refs"))

    # Re-validate HERE rather than trusting the generator's own note. The
    # revalidated_through string was one of the six things P6 used to accept.
    try:
        d1_synthesis.D1DrawerPayload.parse_obj(payload["drawers"])
        result["generated"]["revalidated_through"] = "d1_synthesis.D1DrawerPayload.parse_obj"
        result["generated"]["revalidated"] = True
    except Exception as exc:
        result["generated"]["revalidated"] = False
        fail("the generated payload does not re-parse through D1DrawerPayload: %r" % (exc,))

    # ── the product subject, hashed from the bytes the GATE named ───────────
    sentinels = sorted(set(re.findall(r"ZQX[A-Z]+Q7",
                                      json.dumps(payload, ensure_ascii=False))))
    result["generated"]["sentinels_distinct"] = len(sentinels)
    if not product:
        fail("no --product path was supplied; the subject cannot be bound")
    elif not os.path.exists(product):
        fail("product subject does not exist: %s" % product)
    else:
        with open(product, "rb") as fh:
            raw = fh.read()
        text = raw.decode("utf-8", "replace")
        result["product"] = {
            "path": os.path.realpath(product),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "newlines": raw.count(b"\n"),
            "sentinel_collisions": [s for s in sentinels if s in text],
        }

    # ── diagnostic: does a fixture shipped in the bundle match this run? ─────
    if shipped and os.path.exists(shipped):
        sh = sha256_file(shipped)
        result["shipped_fixture"] = {
            "path": os.path.realpath(shipped),
            "sha256": sh,
            "matches_generated": sh == result["generated"]["fixture_sha256"],
        }

    result["ok"] = not result["errors"]

    print("KAR-093 · P6 VERIFIER")
    print("  python/pydantic : %s / %s" % (result["runtime"]["python"],
                                           result["runtime"]["pydantic"]))
    print("  modules hashed  : %d" % len(result["modules"]))
    print("  import chain    : %s" % result["import_chain"]["closed"])
    print("  edges           : %d" % result["generated"].get("edge_count", -1))
    print("  drawers         : %d" % result["generated"].get("drawer_count", -1))
    print("  fixture sha256  : %s" % result["generated"].get("fixture_sha256", "")[:16])
    print("  product sha256  : %s" % (result["product"].get("sha256", "") or "")[:16])
    print("  collisions      : %s" % (result["product"].get("sentinel_collisions") or "none"))
    print("  result          : %s" % result_path)
    for e in result["errors"]:
        print("  ERROR: %s" % e)
    return emit(0 if result["ok"] else 1)


if __name__ == "__main__":
    sys.exit(main())
