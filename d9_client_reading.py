"""D9-002 · THE PUBLICATION WALL. Whitelist model plus a fail-closed scanner.

Two independent defences, as D7 learned to build them:

  1. the customer model is built BY WHITELIST, field by field — nothing reaches a
     reader because it happened to be in the engine dict;
  2. a fail-closed scanner runs over the finished payload and rejects it WHOLE.

Never scrub. A payload that trips the scanner is discarded and the caller shows a
neutral unavailable state, because a scrubbed payload is a payload whose author
does not know what it said.

WHAT THIS FILE ENFORCES THAT D9-001 RULED
-----------------------------------------
· certified dignity only, published in the approved plain vocabulary
· Moolatrikona COLLAPSED to the own-sign band — the certified engine emits it
  unconditionally for five placements because it computes D9 dignity at degree 0
· nodes remain UNGRADED; no Rahu/Ketu dignity is manufactured
· Pushkara, Gandanta, Ashtamamsha, Gana, D9 aspects: no live publication path
· spouse appearance, spouse profession, third-party temperament: absent
· no ordinal or scored partnership grade
· Practical Navigation is structurally separate and marked editorial
"""

import re
from typing import Any, Dict, List, Optional

# ─── prohibited publication families ─────────────────────────────────────────
#
# Patterns are deliberately narrow enough not to catch approved vocabulary. The
# word "partner" is not prohibited — the report is allowed to discuss the
# native's experience of partnership. A claim ABOUT the partner is.

PROHIBITED_PATTERNS = [
    # concepts D9-001 omitted outright. A live publication path for any of these
    # is a regression, and the scanner is the thing that proves there is none.
    ("omitted_concept", r"\bpushkara\b"),
    ("omitted_concept", r"\bgandanta\b"),
    ("omitted_concept", r"\bashtamamsha\b"),
    ("omitted_concept", r"\barrival\s+fallacy\b"),
    ("omitted_concept", r"\bgana\b"),
    ("omitted_concept", r"\b(?:deva|nara|rakshasa)\s+gana\b"),
    ("omitted_concept", r"\bmoolatrikona\b"),
    ("omitted_concept", r"\bmoola\s*trikona\b"),

    # third-party claims about an unknown spouse
    ("spouse_attribute", r"\byour\s+spouse\s+(?:is|will\s+be|has|carries|combines)\b"),
    ("spouse_attribute", r"\bcomplexion\b"),
    ("spouse_attribute", r"\bwheatish\b"),
    ("spouse_attribute", r"\bfair[- ]skinned\b"),
    ("spouse_attribute", r"\bappearance\s+blend\b"),
    ("spouse_attribute", r"\bpartner(?:'s)?\s+appearance\b"),
    ("spouse_attribute", r"\blikely\s+professional\s+domain\b"),
    ("spouse_attribute", r"\bspouse(?:'s)?\s+profession\b"),
    ("spouse_attribute", r"\byour\s+(?:spouse|partner)\s+works?\s+in\b"),

    # fatalistic relationship register, D9-B14
    ("fatalistic_relationship", r"\bsexless\b"),
    ("fatalistic_relationship", r"\bemotionally\s+(?:remote|unavailable)\b"),
    ("fatalistic_relationship", r"\blow\s+on\s+warmth\b"),
    ("fatalistic_relationship", r"\bdivorce\s+risk\b"),
    ("fatalistic_relationship", r"\bunpleasant\s+married\s+life\b"),
    ("fatalistic_relationship", r"\bmarital\s+(?:stability|instability)\b"),
    ("fatalistic_relationship", r"\bkuja\s+dosha\b"),
    ("fatalistic_relationship", r"\bmangal(?:ik)?\s+dosha\b"),

    # graded partnership verdicts
    ("partnership_grade", r"\bstability\s+score\b"),
    ("partnership_grade", r"\bpartnership\s+growth\s+level\b"),
    ("partnership_grade", r"\bhigh\s+friction\b"),

    # remedial prescription, deferred from v1
    ("prescription", r"\b\d+\s*(?:times|repetitions|malas|japa)\b"),
    ("prescription", r"\brecite\b"),
    ("prescription", r"\bwear\s+a\s+\w+\s+(?:gemstone|stone|ring)\b"),
    ("prescription", r"\bon\s+(?:mondays?|tuesdays?|wednesdays?|thursdays?|"
                     r"fridays?|saturdays?|sundays?)\b"),

    # timing, which the D9 report does not carry at all
    ("timing", r"\bmahadasha\b"),
    ("timing", r"\bantardasha\b"),
    ("timing", r"\bwill\s+happen\s+(?:in|by|within)\b"),
    ("timing", r"\b(?:19|20)\d{2}\b"),

    # longevity, explicitly disclaimed by the accepted H8 authority
    ("longevity", r"\blife\s*span\b"),
    ("longevity", r"\blongevity\b"),
    ("longevity", r"\byears\s+to\s+live\b"),
]

_COMPILED = [(family, re.compile(pat, re.IGNORECASE))
             for family, pat in PROHIBITED_PATTERNS]

# Internal vocabulary that must never reach a customer or a provider.
INTERNAL_TOKENS = re.compile(
    # AK_AMBIGUOUS is deliberately NOT here. The ticket names it as a required
    # reduced state, so it is a contract value the frontend must be able to
    # branch on, not internal vocabulary leaking outward. It appears only in a
    # `status` field and never in prose.
    r"\bKL_H\d+_\w+\b|\brule_id\b|\bfired\b|\bcertified_dignity\b|"
    r"\bd9_sign_index\b|\bsign_index\b|\bgetScore\b|"
    r"\bgetDignityLabel\b|\bchart_token\b",
    re.IGNORECASE,
)


class PublicationViolation(Exception):
    """A prohibited claim reached a publication surface. Fail closed."""

    def __init__(self, family: str, pattern: str, path: str, excerpt: str):
        self.family = family
        self.pattern = pattern
        self.path = path
        super().__init__(f"{family} at {path}: /{pattern}/ matched {excerpt!r}")


def _walk_strings(node: Any, path: str = "$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}")
            if isinstance(k, str):
                yield f"{path}<key>", k
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")


# ─── the one approved span, and why it exists ────────────────────────────────
#
# THE SOURCE-SCAN TRAP, twelfth recurrence and the first inside a payload rather
# than a source file: prose that DOCUMENTS a ban matches the scan for it.
#
# The accepted Karakamsha H8 authority carries its own disclaimer, "Longevity
# itself is not assessed by this module." That sentence is the safest thing in
# the block — it is the authority telling the reader what it is NOT doing — and
# the coarse `\blongevity\b` pattern rejected the whole report because of it.
#
# An earlier revision of this file asserted that D9 needed no allowance list
# because nothing in its approved vocabulary collided with a prohibited pattern.
# That claim was wrong and the suite caught it. The allowance below is therefore
# as narrow as D7's: whole-string equality against an exact approved value, at
# an approved path, and nowhere else. A narrative that QUOTES the disclaimer
# inside a sentence does not match, because the whole string must be equal.

APPROVED_SPANS = frozenset({
    "Longevity itself is not assessed by this module.",
})
_APPROVED_PATH_SUFFIX = ".disclaimer"


def _is_approved_span(path: str, text: str) -> bool:
    return text in APPROVED_SPANS and path.endswith(_APPROVED_PATH_SUFFIX)


def scan_publication(payload: Any) -> List[Dict[str, str]]:
    """Every prohibited hit in `payload`. Empty list means clean."""
    hits: List[Dict[str, str]] = []
    for path, text in _walk_strings(payload):
        if _is_approved_span(path, text):
            continue
        for family, rx in _COMPILED:
            m = rx.search(text)
            if m:
                hits.append({"family": family, "pattern": rx.pattern,
                             "path": path, "excerpt": m.group(0)})
        m = INTERNAL_TOKENS.search(text)
        if m:
            hits.append({"family": "internal_vocabulary",
                         "pattern": "INTERNAL_TOKENS",
                         "path": path, "excerpt": m.group(0)})
    return hits


def assert_publication_safe(payload: Any) -> None:
    """Fail closed. Never scrub, never partially retain."""
    hits = scan_publication(payload)
    if hits:
        first = hits[0]
        raise PublicationViolation(first["family"], first["pattern"],
                                   first["path"], first["excerpt"])


# ─── the approved dignity vocabulary ─────────────────────────────────────────
#
# D9 dignity ruling: consume the certified classification, and translate into
# plain language WITHOUT increasing astrological specificity. Collapsing
# Moolatrikona into the own-sign band is a DECREASE in specificity and is
# therefore authorized by the ruling as written.
#
# The certified engine calls get_dignity with degree pinned to 0, so it returns
# Moolatrikona unconditionally for Sun in Leo, Mars in Aries, Jupiter in
# Sagittarius, Venus in Libra and Saturn in Aquarius. Without this collapse the
# report would publish a degree-sensitive distinction the engine cannot make.

DIGNITY_PUBLICATION = {
    "Exalted (Uccha)": "Exalted",
    "Moolatrikona": "Own Sign",        # ← THE RULED COLLAPSE
    "Own Sign (Swa)": "Own Sign",
    "Friendly Sign (Mitra)": "Friendly Sign",
    "Neutral Sign (Sama)": "Neutral Sign",
    "Enemy Sign (Shatru)": "Enemy Sign",
    "Debilitated (Neecha)": "Debilitated",
    "Node": "Not graded",              # nodes stay ungraded
}
UNAVAILABLE_DIGNITY = "Unavailable"

STRONG_PUBLICATION_BANDS = ("Exalted", "Own Sign", "Friendly Sign")


NODES = ("Rahu", "Ketu")
UNGRADED_PUBLICATION = "Not graded"


def publish_dignity(certified: Optional[str], graha: Optional[str] = None) -> str:
    """Certified band → approved plain label. Unknown bands fail closed.

    NODES ARE ALWAYS UNGRADED IN PUBLICATION, whatever the certified engine
    returns. CORR-01 correction: the certified `get_dignity` does grade Rahu in
    Taurus and Ketu in Scorpio as Exalted, and their opposites as Debilitated
    (BPHS Ch.47), so a band-only mapping published a node dignity on those four
    placements. The ruling is that nodes remain ungraded in this report, so the
    graha is checked FIRST and the certified band never decides for a node.

    The certified engine is not altered. This is a publication-layer rule, and
    the underlying value stays available to QA through the engine block.

    An unrecognised certified value is NOT passed through. If the certified
    vocabulary ever grows a band this table does not know, the report says
    Unavailable rather than publishing a raw internal string.
    """
    if graha in NODES:
        return UNGRADED_PUBLICATION
    if certified is None:
        return UNAVAILABLE_DIGNITY
    return DIGNITY_PUBLICATION.get(certified, UNAVAILABLE_DIGNITY)


# ─── reduced states ──────────────────────────────────────────────────────────

REDUCED = {
    "AK_AMBIGUOUS": "Two planets share the highest degree exactly, so the chart "
                    "does not name a single soul indicator. That ambiguity is "
                    "the finding, and the sections that depend on it are held "
                    "back rather than decided arbitrarily.",
    "UNAVAILABLE": "This part of the reading needs a chart value that is not "
                   "present, so it is not shown.",
    "NO_SIGNAL": "Nothing in this area of the chart rises to a statement. That "
                 "is a real result, not a missing one.",
}


def _reduced(status: str) -> Dict[str, Any]:
    return {"available": False, "status": status,
            "note": REDUCED.get(status, REDUCED["UNAVAILABLE"])}


# ─── whitelist builders ──────────────────────────────────────────────────────

def _placements_public(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """D9 sign, house, approved dignity label, vargottama. Nothing else.

    Deliberately absent: sign indices, the raw certified band, any tag for
    Pushkara, Gandanta or Ashtamamsha, any Gana or nature column, and any
    aspect. The whitelist is the reason those cannot leak.
    """
    out = []
    for graha, p in facts["placements"].items():
        if p.get("status") != "RESOLVED":
            out.append({"graha": graha, "available": False,
                        "note": REDUCED["UNAVAILABLE"]})
            continue
        out.append({
            "graha": graha,
            "available": True,
            "d9_sign": p["d9_sign"],
            "house": p["d9_house"],
            "dignity": publish_dignity(p["certified_dignity"], graha),
            "integrated": p.get("vargottama"),
        })
    return out


def _strengths_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Built-in Power Centers and Integration. Certified reuse throughout."""
    centers = []
    for graha, p in facts["placements"].items():
        if p.get("status") != "RESOLVED":
            continue
        # A node can never be a power center. The dignity gate below would
        # already stop it, because `publish_dignity` returns "Not graded" for
        # nodes and that is not a strong band — but the exclusion is stated
        # explicitly so a later edit to the band list cannot let one through.
        if graha in NODES:
            continue
        label = publish_dignity(p["certified_dignity"], graha)
        if label in STRONG_PUBLICATION_BANDS:
            centers.append({"graha": graha, "d9_sign": p["d9_sign"],
                            "house": p["d9_house"], "dignity": label})
    integration = facts.get("integration") or {}
    status = integration.get("status", "UNAVAILABLE")
    integrated = list(integration.get("integrated_grahas") or [])

    # CORR-05 · QA-17. Four states, and the note never asserts absence from an
    # incomplete set. "No planet repeats its birth sign" is only publishable when
    # every position is known.
    if status == "RESOLVED":
        note = ("Where the birth chart and the divisional chart agree on a "
                "sign, outward promise and inner expression are working from "
                "the same ground.")
    elif status == "PARTIAL":
        note = ("Where the birth chart and the divisional chart agree on a "
                "sign, outward promise and inner expression are working from "
                "the same ground. Not every position could be checked, so this "
                "list may be incomplete.")
    elif status == "NO_SIGNAL":
        note = ("No planet repeats its birth sign here, so each carries some "
                "distance between outward promise and inner expression.")
    else:
        note = ("Some positions could not be checked, so whether anything "
                "repeats its birth sign is not established either way.")

    return {
        "available": True,
        "power_centers": centers,
        "integration_status": status,
        "integration_complete": bool(integration.get("complete")),
        "integrated_grahas": integrated if status in ("RESOLVED", "PARTIAL") else [],
        "integration_note": note,
    }


def _talents_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Latent Talents · CERTIFIED REUSE from the accepted Karakamsha H5.

    NO FALSE ABSENCE. When no rule fires the section reports NO_SIGNAL with the
    accepted note, and it never says the native has no talent signature. That
    was D9-B13, and it is closed here by the authority emitting nothing rather
    than by a patched fallback.
    """
    h5 = facts["karakamsha_houses"].get(5) or {}
    if h5.get("status") != "RESOLVED":
        return _reduced(h5.get("status", "UNAVAILABLE"))
    fired = h5.get("fired") or []
    if not fired:
        return _reduced("NO_SIGNAL")
    return {"available": True,
            "readings": [{"text": _publish_reading_text(r), "tone": r["polarity"]}
                         for r in fired],
            "authority": "accepted_karakamsha"}


# ─── D9 publication translation · CORR-05 · QA-19 ───────────────────────────
#
# `karak_house_data.py` is the VERBATIM accepted authority and stays byte-faithful.
# It is not edited here and must not be.
#
# But one accepted plain text is a guaranteed future outcome — KL_H10_MAL reads
# "You will get there, and the road will not be level" — and the Career & Purpose
# row's own safety restriction says NO CAREER PREDICTION. The accepted wording is
# fine as an internal qualitative statement and unsafe as published copy, so the
# D9 publication layer owns the translation. The qualitative meaning is
# preserved as a PATTERN rather than an outcome. The guarantee is not, and
# neither is any replacement guarantee.
#
# The first translation of KL_H10_MAL said progress is "strengthened by
# sustained effort rather than by timing". The trailing contrast was mine, not
# the authority's: D9 has no basis for ruling timing in or out, and asserting
# that effort rather than timing carries someone is a second unsourced claim
# smuggled in while removing the first.
#
# Keyed by rule id, so a rule whose text changes upstream stops matching and the
# translation is not silently applied to something else.

PUBLICATION_TRANSLATION = {
    # BOTH branches are translated. The accepted authority states them as
    # outcomes — "Results arrive through doing the work properly" and "You will
    # get there" — and the Career & Purpose row's own restriction is NO CAREER
    # PREDICTION. Each is published as a working pattern instead.
    "KL_H10_BEN": ("Methodical, principled work is better supported here than "
                   "shortcuts."),
    "KL_H10_MAL": ("This area carries an uneven, effort-intensive pattern."),
}


def _publish_reading_text(rule: Dict[str, Any]) -> str:
    return PUBLICATION_TRANSLATION.get(rule["id"], rule["plain"])


def _house_family_public(facts: Dict[str, Any], house: int,
                         corroboration: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """One narrower evidence family from an accepted Karakamsha house.

    `requires_confirmation` SURVIVES to publication. Three of the five accepted
    partnership rules carry it in their own text and demand confirmation before
    a conclusion is drawn; flattening it here would publish a conclusion the
    accepted module declined to make.

    Pratiphala corroboration is presented as its OWN reading, never merged into
    the Karakamsha sentence. Two authorities blended into one compound statement
    is the shape KAR-048 warned about inside Karakamsha itself.
    """
    rec = facts["karakamsha_houses"].get(house) or {}
    if rec.get("status") != "RESOLVED":
        return _reduced(rec.get("status", "UNAVAILABLE"))
    fired = rec.get("fired") or []
    block: Dict[str, Any] = {
        "available": bool(fired),
        # NO `rule` FIELD. The translation is applied here at build time, so the
        # rule id has no downstream consumer, and exposing it put internal
        # vocabulary on a customer surface — the publication scanner caught it,
        # which is the guard working.
        "readings": [{"text": _publish_reading_text(r), "tone": r["polarity"],
                      "needs_confirmation": r["confidence"] == "requires_confirmation"}
                     for r in fired],
        "authority": "accepted_karakamsha",
    }
    if not fired:
        block.update(_reduced("NO_SIGNAL"))
        block["readings"] = []
    if rec.get("disclaimer"):
        block["disclaimer"] = rec["disclaimer"]
    if corroboration is None:
        block["corroboration"] = {"available": False,
                                  "note": "The second reading for this area is "
                                          "not available for this chart."}
    else:
        block["corroboration"] = corroboration
    return block


def _executive_snapshot_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    """CORR-01 · the two public server facts the Founder contract names.

    Soul Driver is the Atmakaraka TOGETHER WITH the Swamsa sign — the contract
    row is one statement about the graha and the sign it occupies in the
    navamsha, not two loose fields. Outer Path is the D9 Lagna.

    Each reduces on its own. An AK_AMBIGUOUS chart still publishes the Outer
    Path, because the D9 Lagna does not depend on the Atmakaraka.
    """
    ak = facts["atmakaraka"]
    kl = facts["karakamsha"]
    if ak["status"] == "RESOLVED" and kl["status"] == "RESOLVED":
        soul_driver = {
            "available": True,
            "graha": ak["graha"],
            "swamsa_sign": kl["sign"],
            "swamsa_sign_lord": kl["lord"],
        }
    else:
        soul_driver = _reduced(
            ak["status"] if ak["status"] != "RESOLVED" else kl["status"])

    d9l = facts["d9_lagna"]
    if d9l.get("status") == "RESOLVED":
        outer_path = {"available": True, "sign": d9l["sign"], "lord": d9l["lord"]}
    else:
        outer_path = _reduced(d9l.get("status", "UNAVAILABLE"))

    return {"soul_driver": soul_driver, "outer_path": outer_path}


def _ishta_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Guiding Frequency. MULTI-VALUED when the accepted rule returns co-indicators.

    The list is never collapsed. A single-valued shape would force exactly the
    array-order selection D9-B18 recorded.
    """
    ishta = facts["ishta_devata"]
    if ishta.get("status") == "UNRANKABLE":
        # CORR-01 · a multi-occupant house with an unrankable graha publishes
        # NOTHING. Not a deity, not a partial list, and explicitly not a
        # co-indicator set — that label is a positive finding and this is not one.
        return {"available": False, "status": "UNRANKABLE",
                "note": "The chart places more than one indicator here and one "
                        "of them cannot be compared with the others, so this "
                        "reading is not given rather than guessed at."}
    if ishta.get("status") != "RESOLVED":
        return _reduced(ishta.get("status", "UNAVAILABLE"))
    orientations = list(ishta.get("orientations") or [])
    if not orientations:
        return _reduced("UNAVAILABLE")
    co = bool(ishta.get("co_indicators"))
    return {
        "available": True,
        "deities": [o["deity"] for o in orientations],
        # Deity AND its accepted plain-language orientation, paired, and
        # multi-valued when the accepted rule returns co-indicators. Publishing
        # a bare deity name was D9-B15's untranslated technical exposure.
        "orientations": orientations,
        "co_indicators": co,
        "note": ("Two orientations carry equal weight here and the chart does "
                 "not choose between them. Both are given, because the "
                 "ambiguity is the finding rather than a gap in it."
                 if co else
                 "This is the orientation the chart points toward for inner "
                 "practice."),
        "derived_from_house_lord": ishta.get("mode") == "lord",
    }


# ─── Growth Frontiers · contract 3.3 and 3.4 · CORR-04 ──────────────────────
#
# QA-13. The contract's Section 3 publishes the frontier AND a navigation clause
# for it, 3.3 and 3.4, and D9-002 shipped only the evidence block. Rows 3.1
# Gandanta and 3.2 Ashtamamsha are omitted by Founder ruling, so Depth &
# Recovery is the only surviving frontier — but "only one frontier" is not the
# same as "no section", and the navigation half was simply missing.
#
# The clause is SERVER-OWNED and keyed to the tone the accepted authority already
# assigned. It introduces no astrology: it says what to do about a finding the
# chart already made, which contract 3.4 describes as behavioural instruction.

FRONTIER_NAVIGATION = {
    "support": "Where this is already working, the useful move is to notice when "
               "you are relying on it and let it carry more rather than less.",
    "caution": "Where this costs you something, name the situation it shows up "
               "in before deciding what to change about it.",
    "neutral": "Where this is mixed, watch it across a season rather than "
               "drawing a conclusion from one instance.",
}


def _growth_frontiers_public(depth: Dict[str, Any]) -> Dict[str, Any]:
    """Each published frontier with its navigation clause, 1:1."""
    if not depth.get("available"):
        return {"available": False,
                "status": depth.get("status", "NO_SIGNAL"),
                "note": "No growth frontier rises to a statement on this chart."}
    frontiers = []
    for r in (depth.get("readings") or []):
        frontiers.append({
            "reading": r["text"],
            "tone": r["tone"],
            "navigation": FRONTIER_NAVIGATION.get(r["tone"]),
            "needs_confirmation": bool(r.get("needs_confirmation")),
        })
    block = {"available": True, "frontiers": frontiers}
    if depth.get("disclaimer"):
        block["disclaimer"] = depth["disclaimer"]
    return block


# ─── Daily Alignment & Action Blueprint · contract 5.1-5.3 · CORR-04 ────────
#
# Three named bands, server-owned throughout, and each one reduces on its own.
#
# The hard line running through all three: NOTHING IS INVENTED TO FILL A BAND.
# D9-001 established that no certified graha→mantra, graha→weekday or
# graha→charity correspondence exists anywhere in the product, and the ticket
# forbade inventing them. So band 5.2 anchors to the already-certified Ishta
# orientation and offers a generic practice, and band 5.3 offers a generic
# service orientation over a mechanical fact. Neither names a material, a day, a
# count, a beneficiary or a promised result.

MICRO_RITUAL_FRAME = (
    "A short daily practice, held in the direction below. What matters is that "
    "it is brief, that it is daily, and that it points somewhere rather than "
    "nowhere."
)
MICRO_RITUAL_CONTRACT = (
    "Generic practice only. No prescribed words, day, count, material or "
    "promised result, because no certified source for those exists."
)

SEVA_ORIENTATION = (
    "A simple, repeatable act of service that expects nothing visible in "
    "return. Choose something ordinary and close to hand."
)
SEVA_CONTRACT = (
    "A general orientation, not a prescription. No specific charity, material, "
    "beneficiary, day or remedial result is named, because none is sourced."
)
SEVA_NO_SIGNAL = (
    "No part of this reading carries the emphasis this band responds to, so "
    "nothing is prescribed here."
)


def _daily_alignment_public(frontiers: Dict[str, Any],
                            guiding: Dict[str, Any],
                            dusthana: Dict[str, Any]) -> Dict[str, Any]:
    """The three bands. Each is independent and each may reduce alone."""

    # 5.1 · derived 1:1 from the published frontier navigation. No new material,
    # and explicitly no clinical framing: these are dispositions, not treatment.
    if frontiers.get("available"):
        adjustments = [f["navigation"] for f in frontiers["frontiers"]
                       if f.get("navigation")]
        band_1 = ({"available": True, "adjustments": adjustments,
                   "derived_from": "growth_frontiers"}
                  if adjustments else _reduced("NO_SIGNAL"))
    else:
        band_1 = _reduced("NO_SIGNAL")

    # 5.2 · available ONLY when the Guiding Frequency is. Co-indicators stay
    # multi-valued: the band anchors to every orientation the accepted rule
    # returned, because choosing one here would resolve by presentation order
    # exactly what the selector refused to resolve.
    if guiding.get("available") and guiding.get("orientations"):
        band_2 = {
            "available": True,
            "frame": MICRO_RITUAL_FRAME,
            "anchored_to": [{"deity": o["deity"], "orientation": o["orientation"]}
                            for o in guiding["orientations"]],
            "co_indicators": bool(guiding.get("co_indicators")),
            "contract": MICRO_RITUAL_CONTRACT,
        }
    else:
        band_2 = {"available": False,
                  "status": guiding.get("status", "UNAVAILABLE"),
                  "note": "This band follows the guiding orientation, which is "
                          "not available for this chart, so it is not shown."}

    # 5.3 · over the mechanical dusthana fact. No emphasis is a real answer.
    if dusthana.get("status") != "RESOLVED":
        band_3 = _reduced("UNAVAILABLE")
    elif not dusthana.get("emphasis"):
        band_3 = {"available": False, "status": "NO_SIGNAL", "note": SEVA_NO_SIGNAL}
    else:
        band_3 = {"available": True, "orientation": SEVA_ORIENTATION,
                  "contract": SEVA_CONTRACT}

    return {
        "psychological_adjustment": band_1,
        "daily_micro_ritual": band_2,
        "targeted_seva": band_3,
        "available": any(b.get("available") for b in (band_1, band_2, band_3)),
    }


# ─── Practical Navigation · FOUNDER-RULED EDITORIAL GUIDANCE ────────────────
#
# Structurally separate from the astrology and labelled as what it is. D9-001
# established that no accepted source supplies relational or practical actions:
# the Karakamsha atom schema carries an action seed but passes null for every
# house rule, and Pratiphala has no action field. So this block is EDITORIAL,
# it says so in its own contract, and it is not claimed to be derived from the
# chart.

NAVIGATION_CONTRACT = (
    "Practical guidance written in response to the partnership pattern above. "
    "This is editorial advice informed by that certified pattern, not a "
    "shastric prescription and not a further reading of the chart."
)

NAVIGATION_SEEDS = {
    "support": "Where the partnership reading is supportive, the useful move is "
               "usually to lean on it deliberately rather than assume it will "
               "keep working unattended.",
    "caution": "Where the partnership reading flags friction, name the specific "
               "situation it shows up in before deciding what to change.",
    "neutral": "Where the partnership reading is mixed, watch it for a season "
               "before drawing conclusions from any single instance.",
}

NAVIGATION_CONFIRMATION_NOTE = (
    "Part of the pattern this responds to is marked as needing confirmation "
    "elsewhere in the chart, so hold it lightly."
)


def _navigation_public(partnership: Dict[str, Any]) -> Dict[str, Any]:
    """CORR-01 · editorial guidance derived from the PARTNERSHIP block only.

    Two corrections to what D9-002 shipped:

    1. The previous version harvested tones from career, partnership and depth
       together, so a report with no partnership signal at all still emitted
       relationship-shaped guidance off the back of a career reading. It now
       reads one block.
    2. It described itself as "not derived from the chart", which was true of
       the wording and false of the trigger — the guidance appears BECAUSE a
       certified partnership pattern is present, and which line appears depends
       on that pattern's tone. It now says what it is: editorial advice informed
       by the certified partnership pattern.

    NO PARTNERSHIP SIGNAL → NO GUIDANCE. Not an empty list inside an available
    block: the whole section reports unavailable.
    """
    if not partnership.get("available"):
        return {"available": False,
                "kind": "editorial_guidance",
                "status": partnership.get("status", "NO_SIGNAL"),
                "note": "There is no partnership pattern to respond to, so no "
                        "guidance is offered here."}

    tones, needs_confirmation = [], False
    for r in (partnership.get("readings") or []):
        if r.get("tone") and r["tone"] not in tones:
            tones.append(r["tone"])
        needs_confirmation = needs_confirmation or bool(r.get("needs_confirmation"))

    if not tones:
        return {"available": False, "kind": "editorial_guidance",
                "status": "NO_SIGNAL",
                "note": "There is no partnership pattern to respond to, so no "
                        "guidance is offered here."}

    guidance = [NAVIGATION_SEEDS[t] for t in tones if t in NAVIGATION_SEEDS]
    if needs_confirmation:
        guidance.append(NAVIGATION_CONFIRMATION_NOTE)
    return {
        "available": True,
        "kind": "editorial_guidance",
        "informed_by": "certified_partnership_pattern",
        "not_a_shastric_prescription": True,
        "contract": NAVIGATION_CONTRACT,
        "guidance": guidance,
    }


# ─── the assembled customer model ────────────────────────────────────────────

MODULE_SECTIONS = ("soul_driver", "outer_path", "strengths", "talents",
                   "career_and_purpose", "partnership", "depth_and_recovery",
                   "growth_frontiers", "daily_alignment", "guiding_frequency",
                   "practical_navigation")


def build_client_reading(facts: Dict[str, Any],
                         pratiphala: Optional[Dict[int, Dict[str, Any]]] = None
                         ) -> Dict[str, Any]:
    """Build the customer model BY WHITELIST, then scan it fail-closed.

    `pratiphala` maps house → an already-safe corroboration block, or is None
    when the accepted Pratiphala authority is not wired. Its absence is a
    reduced state, never a failure: D9's own readings do not depend on it.
    """
    prati = pratiphala or {}

    families = {
        "career_and_purpose": _house_family_public(facts, 10, prati.get(10)),
        "partnership": _house_family_public(facts, 7, prati.get(7)),
        "depth_and_recovery": _house_family_public(facts, 8, prati.get(8)),
    }

    frontiers = _growth_frontiers_public(families["depth_and_recovery"])
    daily_alignment = _daily_alignment_public(
        frontiers, _ishta_public(facts), facts.get("dusthana") or {})

    snapshot = _executive_snapshot_public(facts)
    reading: Dict[str, Any] = {
        "executive_snapshot": snapshot,
        "soul_driver": snapshot["soul_driver"],
        "outer_path": snapshot["outer_path"],
        "strengths": _strengths_public(facts),
        "talents": _talents_public(facts),
        "career_and_purpose": families["career_and_purpose"],
        "partnership": families["partnership"],
        "depth_and_recovery": families["depth_and_recovery"],
        "growth_frontiers": frontiers,
        "daily_alignment": daily_alignment,
        "guiding_frequency": _ishta_public(facts),
        "placements": _placements_public(facts),
        "practical_navigation": _navigation_public(families["partnership"]),
        # NO `omitted_from_this_report` FIELD, and its absence is deliberate.
        # An earlier revision listed the omitted concepts here so the payload
        # would document its own scope. That field was itself a LIVE PUBLICATION
        # PATH for every term the ticket says must not have one — the scanner
        # rejected the whole report over it, which is the guard working. What a
        # report does not contain is not the reader's business, and naming the
        # bans is how the bans get shipped.
        "dignity_vocabulary": sorted(set(DIGNITY_PUBLICATION.values())),
    }

    # The report must remain useful under AK_AMBIGUOUS. Placements, strengths and
    # integration do not depend on the Atmakaraka and are still populated above;
    # only the Karakamsha-derived families reduce.
    reading["reduced"] = sorted(
        k for k in MODULE_SECTIONS
        if isinstance(reading.get(k), dict) and reading[k].get("available") is False)

    assert_publication_safe(reading)
    return reading


# ─── THE SYNTHESIS SEED LAYER · CORR-05 · QA-18 ─────────────────────────────
#
# CORR-03 closed the free-prose channel and CORR-05 closes the replay it left
# behind.
#
# The pool used to copy customer card sentences straight into atoms, so the
# "synthesis" was the structured report's own sentences stitched together with
# connectors. That is exactly what D9-B10 prohibited, arrived at from the
# opposite direction: the old defect was the provider rewriting the cards, the
# new one was the server reciting them.
#
# So the pool is now SYNTHESIS SEEDS: server-owned, plain-English restatements
# keyed by DOMAIN AND TONE. Each seed carries a proposition the structured report
# already published, in integrative wording that appears nowhere on a card, and
# with no technical vocabulary — contract 6.1 requires zero of it, and the old
# atoms and the old opening line both carried "navamsha".
#
# Seeds are keyed by (domain, tone) rather than per reading, so two findings of
# the same tone in one domain collapse into one seed. That is a synthesis
# operation and it is the reason the closing does not grow with the report.
#
# NOTHING IS ADDED. A seed exists only where the corresponding block published,
# and it asserts no more than that block did.

SYNTHESIS_SEEDS: Dict[str, Dict[str, str]] = {
    "strengths": {
        "integrated": "Some of what you show the world and what you actually "
                      "run on are the same thing, which is less common than it "
                      "sounds.",
        "centers": "Parts of you are working from settled ground rather than "
                   "from borrowed confidence.",
    },
    "talents": {
        "support": "You came in already able to do something nobody taught you.",
        "neutral": "What you are good at sits a little outside the ordinary "
                   "channels for it.",
        "caution": "What you arrived with is real, and getting it out of you "
                   "has never been smooth.",
    },
    "career": {
        "support": "In your working life the careful route suits you better "
                   "than the quick one.",
        "caution": "Your working life runs uneven, and it asks for effort.",
        "neutral": "Your working life moves in its own rhythm rather than a "
                   "borrowed one.",
    },
    "partnership": {
        "support": "Closeness tends to give you something back rather than "
                   "only cost you.",
        "caution": "Closeness asks something of you that solitude never does.",
        "neutral": "You meet closeness on terms of your own.",
    },
    "depth": {
        "support": "You have more held in reserve than anyone watching would "
                   "guess.",
        "caution": "You are carrying something that started before you did.",
        "neutral": "There is more underneath here than shows on the surface.",
    },
    "guiding": {
        "any": "There is a direction your attention returns to when nothing is "
               "demanding it, and it is worth taking seriously.",
    },
    "alignment": {
        # NOT "what changes this". The guidance may say what to practise; it may
        # not claim that practising it alters the astrological condition.
        "any": "The useful practices here are small, repeated and unglamorous "
               "rather than decisive.",
    },
}

SYNTHESIS_OPENING = ("Read as one thing rather than a list, this is what the "
                     "reading keeps pointing at. ")
SYNTHESIS_CLOSING = ("None of it is a verdict. It is the shape you keep "
                     "returning to, and you are the one who works with it.")


# ─── THE ATOM POOL · CORR-03, reseeded in CORR-05 ────────────────────────────
#
# THE CONTAINMENT MODEL CHANGED HERE, and it changed because the old one failed
# twice under adversarial QA.
#
# Until CORR-02 the provider wrote free prose and a blacklist scanned it. That is
# an unbounded enumeration around an unbounded generator, and it loses: CORR-01's
# sentence shapes lost to a comma, and CORR-02's vocabulary families lost to
# "your significant other", "they prefer a quiet routine", "you are doomed to
# loneliness" and eight more. Each round the dictionary grew and the next round
# found new wording. A third dictionary would fail the same way.
#
# The provider no longer writes sentences. The server publishes a POOL OF
# APPROVED ATOMS — every one of them text the server already authored and
# already published in the structured report — and the provider returns an
# ORDERING over atom ids. The server renders the narrative from its own strings.
#
# The provider keeps the job it is actually good at: choosing what belongs
# together, in what order, with what connective shape. It loses the job it cannot
# be trusted with: asserting anything.
#
# Every QA bypass now fails for one structural reason rather than fourteen
# lexical ones — there is no free-text channel to put them in.

ATOM_DOMAINS = ("strengths", "talents", "career", "partnership", "depth",
                "guiding", "alignment")

# CORR-04 · QA-15. Atom COUNT does not make a synthesis; DOMAIN SPREAD does.
# Three atoms drawn from two domains is a dressed-up replay of one narrow part
# of the report, which the contract's "one genuinely integrative essay" is not.
MIN_SUBSTANTIVE_DOMAINS = 3

PROVISIONAL_NOTICE_ID = "partnership.provisional_notice"
PROVISIONAL_NOTICE_TEXT = (
    "Some relationship indicators here remain provisional, so they are held out "
    "of this synthesis."
)


def build_atom_pool(client_reading: Dict[str, Any]) -> Dict[str, Any]:
    """The complete set of propositions the narrative may be built from.

    SEEDS, NOT CARDS. Every atom text below comes from `SYNTHESIS_SEEDS` and none
    is copied from the structured report, which is CORR-05's answer to QA-18.

    PROVISIONAL PARTNERSHIP FINDINGS ARE EXCLUDED, unchanged from CORR-03. A
    provisional finding never enters the pool at all: it stays fully visible in
    the deterministic Partnership section with its own flag, and a fixed
    server-owned notice says why it is not in the synthesis. Nothing depends on
    the model handling it correctly.
    """
    atoms: List[Dict[str, Any]] = []
    seen_keys = set()

    def _seed(domain: str, key: str, substantive: bool = True) -> None:
        """One atom per (domain, key). Repeats collapse — that is the synthesis."""
        table = SYNTHESIS_SEEDS.get(domain) or {}
        text = table.get(key)
        if not text or (domain, key) in seen_keys:
            return
        seen_keys.add((domain, key))
        atoms.append({"id": f"{domain}.{key}", "domain": domain,
                      "text": text, "substantive": substantive})

    strengths = client_reading.get("strengths") or {}
    if strengths.get("available"):
        if strengths.get("integrated_grahas"):
            _seed("strengths", "integrated")
        if strengths.get("power_centers"):
            _seed("strengths", "centers")

    for domain, section in (("talents", "talents"),
                            ("career", "career_and_purpose"),
                            ("depth", "depth_and_recovery")):
        block = client_reading.get(section) or {}
        if block.get("available"):
            for r in (block.get("readings") or []):
                _seed(domain, r["tone"])

    partnership = client_reading.get("partnership") or {}
    provisional_held = 0
    if partnership.get("available"):
        for r in (partnership.get("readings") or []):
            if r.get("needs_confirmation"):
                provisional_held += 1
                continue                      # never offered to the provider
            _seed("partnership", r["tone"])
    if provisional_held:
        # NOT substantive. It is a disclosure about what is absent, so it cannot
        # be the thing that makes partnership count toward domain diversity.
        atoms.append({"id": PROVISIONAL_NOTICE_ID, "domain": "partnership",
                      "text": PROVISIONAL_NOTICE_TEXT, "substantive": False})

    guiding = client_reading.get("guiding_frequency") or {}
    if guiding.get("available") and guiding.get("orientations"):
        _seed("guiding", "any")

    alignment = client_reading.get("daily_alignment") or {}
    if (alignment.get("psychological_adjustment") or {}).get("available"):
        _seed("alignment", "any")

    substantive = [a for a in atoms if a.get("substantive")]
    return {
        "atoms": atoms,
        "atom_ids": [a["id"] for a in atoms],
        "domains_present": sorted({a["domain"] for a in atoms}),
        "substantive_domains": sorted({a["domain"] for a in substantive}),
        "provisional_partnership_findings_withheld": provisional_held,
    }
