"""KAR-093 step 10 · astronomy golden freeze.

Computes NOTHING. The astronomy came from the deployed service; this wraps the
captured bytes with the evidence that says which backend produced them. That is
the whole point of an astronomy golden: a locally computed chart would prove the
local install matches the certificate, not that production does.

Strict utf-8 only. If a capture needs utf-8-sig it is a transport artefact and
this refuses it rather than working around it.
"""
import hashlib, json, sys

# Session-scoped, excluded from the governing digest for the same reason
# response.generated_at is excluded from the interpretation goldens: they change
# on every request and would make the golden unmatchable by construction. They
# stay in the recorded capture as provenance.
SESSION_KEYS = ["chart_token", "anon_session"]

CERT = {
 "chart_engine_version":"1.1.0","ayanamsha_model":"lahiri-linear-fit-2026-07",
 "house_system":"whole-sign","dasha_year_days":365.2425,"node_type":"mean",
 "ephemeris_backend":"swisseph","ephemeris_dataset":"modern-era-se1",
 "ephemeris_dataset_hash":"73377f2ff49778826c12346af0626023cff457f85c08d526dc8ebf8627296a65",
 "ephemeris_files":["semo_18.se1","sepl_18.se1"],
 "ephemeris_manifest_status":"verified","ephemeris_manifest_enforced":True,
 "supported_year_range":[1800,2150]}

def load_strict(path):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"REFUSED: {path} carries a UTF-8 BOM. That is a transport "
                         f"artefact, not the bytes production sent. Re-capture it.")
    return raw, json.loads(raw.decode("utf-8"))   # strict; never utf-8-sig

def canon(obj):
    """Defined here, not borrowed: sha256 over sorted-key compact JSON."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()

if __name__ == "__main__":
    health_path, chart_path, out_path = sys.argv[1:4]
    h_raw, health = load_strict(health_path)
    c_raw, chart  = load_strict(chart_path)

    if list(chart) == ["detail"]:
        raise SystemExit("REFUSED: the chart capture is an error envelope, not a chart.")
    for k in ("lagna", "planets", "houses", "calculation_meta"):
        if k not in chart:
            raise SystemExit(f"REFUSED: chart capture has no {k!r}.")

    lagna, mars = chart["lagna"], chart["planets"]["Mars"]
    sanity = {
        "lagna_sign_is_libra": lagna["sign"] == "Libra",
        "lagna_degree_20_0586": abs(lagna["degree"] - 20.0586) < 0.001,
        "mars_sign_is_libra": mars["sign"] == "Libra",
        "mars_degree_24_4068": abs(mars["degree"] - 24.4068) < 0.001,
        "mars_d9_taurus": mars["d9_sign"] == "Taurus",
        "mars_d20_leo": mars["d20_sign"] == "Leo",
        "dasha_rahu_md_saturn_ad": (chart["dasha"]["current_mahadasha"]["planet"] == "Rahu"
                                    and chart["dasha"]["current_antardasha"]["planet"] == "Saturn"),
    }
    if not all(sanity.values()):
        raise SystemExit("REFUSED: sanity check failed -> " +
                         json.dumps({k: v for k, v in sanity.items() if not v}))

    cert_match = {k: health["calculation_meta"].get(k) == v for k, v in CERT.items()}
    if not all(cert_match.values()):
        raise SystemExit("REFUSED: /health does not match the fixture-freeze certificate.")
    if chart["calculation_meta"] != health["calculation_meta"]:
        raise SystemExit("REFUSED: the chart's calculation_meta differs from /health's. "
                         "The two captures did not come from the same build.")

    governing = {k: v for k, v in chart.items() if k not in SESSION_KEYS}

    golden = {
        "_header": {
            "ticket": "KAR-093 step 10",
            "layer": "astronomy",
            "provenance": "CAPTURED from the deployed service with curl.exe -o. Nothing "
                          "here was computed locally. A locally computed chart would prove "
                          "the local install matches the certificate, not that production does.",
            "captures": {
                "health": {"file": health_path.split("/")[-1], "sha256": hashlib.sha256(h_raw).hexdigest(),
                           "bytes": len(h_raw), "utf8_bom": False},
                "chart":  {"file": chart_path.split("/")[-1], "sha256": hashlib.sha256(c_raw).hexdigest(),
                           "bytes": len(c_raw), "utf8_bom": False},
            },
            "certified_backend": {
                "fields_checked": len(CERT), "fields_matched": sum(cert_match.values()),
                "chart_meta_equals_health_meta": True,
            },
            "sanity_check": sanity,
            "governing_subtree": {
                "keys": sorted(governing),
                "excluded": SESSION_KEYS,
                "excluded_reason": "session-scoped, differ on every request; keeping them "
                                   "would make the golden unmatchable by construction",
                "digest_definition": "sha256 over json.dumps(sort_keys=True, "
                                     "separators=(',',':'), ensure_ascii=False)",
                "sha256": canon(governing),
            },
            "declared_production_pin": "3.11.0",
            "freeze_interpreter": {
                "python": sys.version.split()[0],
                "note": "the interpreter that ASSEMBLED this wrapper. It computed no "
                        "astronomy; production did. Recorded separately from "
                        "declared_production_pin because they are different kinds of fact.",
            },
            "observed_production_python": None,
            "comparison_rule": "Compare the `chart` subtree minus the excluded session keys, "
                               "against governing_subtree.sha256. NEVER the whole-file hash, "
                               "which is host-specific by header content.",
        },
        "health": health,
        "chart": chart,
    }
    with open(out_path, "w") as f:
        json.dump(golden, f, indent=2, ensure_ascii=False, sort_keys=True)
    print("written :", out_path)
    print("governing subtree sha256:", golden["_header"]["governing_subtree"]["sha256"])
    print("sanity  :", sum(sanity.values()), "of", len(sanity), "checks pass")
    print("cert    :", sum(cert_match.values()), "of", len(CERT), "fields match")
