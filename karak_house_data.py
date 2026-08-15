"""D9-002 · karak_house_data · the ACCEPTED Karakamsha authority, extracted once.

WHAT THIS MODULE IS
-------------------
A VERBATIM extraction of the accepted Karakamsha rule tables and evaluator
semantics from the reviewed browser module, so that the server has ONE copy and
D9 does not become a second Karakamsha implementation.

D9-001-C bound four Founder rows to this authority. Its rules lived only in
`newphalit_fixed.html`, so a server consumer had two options: duplicate the table
inside `d9_engine`, or extract it once into a shared module that every server
consumer reads. The first is the duplicate-authority failure QA named during
D9-001-CORR-01. This module is the second.

`d9_engine` holds NO copy of anything here. It receives this authority by
injection, exactly as D4, D5 and D7 receive SIGNS and SIGN_LORDS from main.py.

PROVENANCE — verify before trusting
-----------------------------------
Source subject: newphalit_fixed.html
  5112178b921f777195ec7d558a0fad95cbfac2400ea3f0070441d555129122a2

Extracted ranges and their SHA-256 (first 16) at extraction time:

  KARAK_HOUSE_DATA      L28501-28568   fd999987b4459380
  KARAK_DEITY_JAIMINI   L28569-28580   fe950186ae1fff8b
  karakRuleMatches      L28664-28685   13cbc52babec52a2
  karakSelectDevata     L28697-28720   99a2c57d467ecec8

If the browser module changes, those hashes change and this extraction is stale.
`tests/test_d9_provenance.py` re-derives them from the subject when it is
available and skips loudly when it is not.

SCOPE OF THE EXTRACTION — deliberately partial
----------------------------------------------
Only houses 5, 7, 8 and 10 are extracted, because those are the only houses
D9-001-C bound to Founder rows. Houses 1-4, 6, 9, 11 and 12 exist in the accepted
table and are NOT extracted here. That is a scope decision, not an oversight:
extracting rules nothing consumes would create surface for drift with no reader.
A later consumer that needs them extends this module rather than starting a
third copy.

ONE RULED DIVERGENCE, AND IT IS DELIBERATE
------------------------------------------
The browser `karakSelectDevata` ranks candidates with `getScore`, the degree-blind
client dignity table. D9-001 ruled that D9 consumes CERTIFIED dignity and never
recreates `getScore`. So `select_devata` below takes a caller-supplied rank
function and the D9 caller supplies certified D9 dignity. Selection SHAPE — sole,
strongest, co-indicator, lord, and never resolving a tie by list order — is
preserved exactly. Only the comparator changes, and it changes because a ruling
said so.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence

EXTRACTION_SUBJECT = (
    "5112178b921f777195ec7d558a0fad95cbfac2400ea3f0070441d555129122a2"
)
SOURCE_RANGE_DIGESTS = {
    "KARAK_HOUSE_DATA": ("L28501-28568", "fd999987b4459380"),
    "KARAK_DEITY_JAIMINI": ("L28569-28580", "fe950186ae1fff8b"),
    "karakRuleMatches": ("L28664-28685", "13cbc52babec52a2"),
    "karakSelectDevata": ("L28697-28720", "99a2c57d467ecec8"),
    "KARAK_ISHTA_ARCHETYPE": ("L28611-28631", "319bd21d7733ac26"),
}

BENEFICS = ("Moon", "Mercury", "Jupiter", "Venus")
MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
ORDER9 = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
          "Saturn", "Rahu", "Ketu")

# ─── KARAK_DEITY_JAIMINI · verbatim ──────────────────────────────────────────
DEITY_JAIMINI: Dict[str, str] = {
    "Sun": "Shiva", "Moon": "Gauri", "Mars": "Skanda", "Mercury": "Vishnu",
    "Jupiter": "Sambasiva", "Venus": "Lakshmi", "Saturn": "Narayana",
    "Rahu": "Durga", "Ketu": "Ganapati",
}

# ─── KARAK_ISHTA_ARCHETYPE · verbatim ────────────────────────────────────────
#
# The accepted plain-language orientation for each Ishta graha. Extracted so the
# server publishes the reviewed wording rather than a bare deity name, which
# D9-B15 recorded as untranslated technical exposure.
#
# NOT extracted, deliberately: `MOKSHA_EMANCIPATION_SIGNS` and the moksha branch
# beside this table. The accepted module carries an explicit instruction on it —
# the occupancy proxy for benefic influence was ruled out because that module
# computes no drishti, and it says in terms that it must not be ported into the
# server engine. It is not ported.

ISHTA_ARCHETYPE: Dict[str, str] = {
    "Sun": "Your final orientation is toward dissolution of what you built, "
           "not its preservation.",
    "Moon": "Your final orientation is toward mercy, and toward being softened "
            "rather than proven right.",
    "Mars": "Your final orientation is toward clean decisive action taken "
            "without anger.",
    "Mercury": "Your final orientation is toward preservation, order, and "
               "sustaining what was entrusted to you.",
    "Jupiter": "Your final orientation is toward the union of discipline and "
               "grace, neither one alone.",
    "Venus": "Your final orientation is toward abundance held lightly and "
             "given away.",
    "Saturn": "Your final orientation is toward endurance in service of "
              "something that outlasts you.",
    "Rahu": "Your final orientation is toward meeting force with force, and "
            "knowing when to stop.",
    "Ketu": "Your final orientation is toward removing obstruction rather than "
            "overcoming it.",
}


# ─── KARAK_HOUSE_DATA · houses 5, 7, 8, 10 · verbatim ────────────────────────
#
# `when` keys carry the accepted matcher vocabulary. `any_malefic_single` is the
# Python spelling of the browser's `test: c => c.malOcc.length === 1`; `lord_is_
# benefic_occupant` is `test: c => c.benOcc.includes(c.lord)`; `benefic_not_lord`
# is `test: c => c.benOcc.length > 0 && !c.benOcc.includes(c.lord)`. The three
# arrow functions are the only rules that could not be expressed in the declarative
# vocabulary, and each is named rather than inlined so the port is auditable.

HOUSE_DATA: Dict[int, Dict[str, Any]] = {
    5: {
        "domain": "Inherited Talents",
        "rules": [
            {"id": "KL_H5_BEN", "when": {"any_benefic": True}, "polarity": "support",
             "plain": "You arrived with something you did not have to learn."},
            {"id": "KL_H5_2ML", "when": {"malefic_count": 2}, "polarity": "neutral",
             "plain": "You are drawn to disciplines that operate outside the "
                      "ordinary channels."},
            {"id": "KL_H5_1ML", "when": {"any_malefic_single": True}, "polarity": "caution",
             "plain": "What you arrived with is real, and it does not come out "
                      "smoothly."},
        ],
    },
    7: {
        "domain": "Partnership",
        "rules": [
            {"id": "KL_H7_JUP", "when": {"occupant": "Jupiter"}, "polarity": "support",
             "plain": "Partnership is a source of support for what you came to do."},
            {"id": "KL_H7_BEN", "when": {"any_benefic": True}, "polarity": "support",
             "plain": "Partnership works in your favour more often than not."},
            {"id": "KL_H7_RAH", "when": {"occupant": "Rahu"}, "polarity": "caution",
             "plain": "Partnership follows an unconventional course rather than "
                      "the expected one.",
             "confidence": "requires_confirmation"},
            {"id": "KL_H7_KET", "when": {"occupant": "Ketu"}, "polarity": "caution",
             "plain": "You hold something back inside partnership, even a close one.",
             "confidence": "requires_confirmation"},
            {"id": "KL_H7_MAL", "when": {"occupants": ["Sun", "Mars", "Saturn"]},
             "polarity": "caution",
             "plain": "Partnership carries friction that has to be worked rather "
                      "than waited out.",
             "confidence": "requires_confirmation"},
        ],
    },
    8: {
        "domain": "Longevity & Depth",
        "rules": [
            {"id": "KL_H8_BL", "when": {"lord_is_benefic_occupant": True},
             "polarity": "support",
             "plain": "You tend to recover steadily from disruption and difficult "
                      "transitions."},
            {"id": "KL_H8_BEN", "when": {"benefic_not_lord": True}, "polarity": "support",
             "plain": "You have more depth in reserve than is visible from outside."},
            {"id": "KL_H8_MAL", "when": {"any_malefic": True}, "polarity": "caution",
             "plain": "You carry something here that predates you."},
        ],
    },
    10: {
        "domain": "Success & Karma",
        "rules": [
            {"id": "KL_H10_BEN", "when": {"any_benefic": True}, "polarity": "support",
             "plain": "Results arrive through doing the work properly rather than "
                      "around it."},
            {"id": "KL_H10_MAL", "when": {"any_malefic": True}, "polarity": "caution",
             "plain": "You will get there, and the road will not be level."},
        ],
    },
}

EXTRACTED_HOUSES = tuple(sorted(HOUSE_DATA))

# The accepted module's own disclaimer on house 8, carried with the data because
# it is a publication constraint and not a comment.
HOUSE_DISCLAIMERS: Dict[int, str] = {
    8: "Longevity itself is not assessed by this module.",
}


# ─── karakRuleMatches · verbatim semantics ───────────────────────────────────

def rule_matches(rule: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Port of `karakRuleMatches`. Semantics preserved exactly.

    Load-bearing detail from the original, easy to lose: a rule whose `when`
    declares NOTHING matches nothing. The browser computes `declared` and returns
    `!!declared`, so an empty or unrecognised `when` is False, not True. A port
    that defaulted to True would fire every unmatched rule on every chart.
    """
    w = rule.get("when") or {}
    occ = ctx["occupants"]
    ben = ctx["benefic_occupants"]
    mal = ctx["malefic_occupants"]

    if w.get("any_malefic_single"):
        return len(mal) == 1
    if w.get("lord_is_benefic_occupant"):
        return ctx["lord"] in ben
    if w.get("benefic_not_lord"):
        return len(ben) > 0 and ctx["lord"] not in ben

    if w.get("any_benefic") and len(ben) == 0:
        return False
    if w.get("any_malefic") and len(mal) == 0:
        return False
    if w.get("malefic_count") is not None and len(mal) < w["malefic_count"]:
        return False
    if w.get("occupants") and not any(g in occ for g in w["occupants"]):
        return False
    if w.get("occupant") and w["occupant"] not in occ:
        return False

    declared = (w.get("any_benefic") or w.get("any_malefic")
                or w.get("malefic_count") is not None
                or w.get("occupants") or w.get("occupant"))
    return bool(declared)


def eval_house(house: int, occupants: Sequence[str], lord: str) -> Dict[str, Any]:
    """Port of `karakEvalRules` for one extracted house.

    Returns the fired rules and the context they fired against. **Emits nothing
    when nothing fires** — there is no negative fallback and none may be added.
    That absence is what closes D9-B13 by construction: the legacy
    `getSwamsaTalent` asserted "no signature" from table sparsity, and this
    authority simply says nothing.
    """
    if house not in HOUSE_DATA:
        raise KeyError(f"house {house} is not extracted; see module docstring")
    occ = [g for g in ORDER9 if g in occupants]
    ctx = {
        "occupants": occ,
        "benefic_occupants": [g for g in occ if g in BENEFICS],
        "malefic_occupants": [g for g in occ if g in MALEFICS],
        "lord": lord,
        "house": house,
    }
    entry = HOUSE_DATA[house]
    fired = [r for r in entry["rules"] if rule_matches(r, ctx)]
    return {
        "house": house,
        "domain": entry["domain"],
        "occupants": occ,
        "lord": lord,
        "fired": [{"id": r["id"], "polarity": r["polarity"], "plain": r["plain"],
                   "confidence": r.get("confidence", "direct")} for r in fired],
        "disclaimer": HOUSE_DISCLAIMERS.get(house),
        "authority": "accepted_karakamsha",
    }


# ─── karakSelectDevata · shape verbatim, comparator injected ─────────────────

class DevataSelection(dict):
    """Result of the accepted devata selection. A dict so it serialises freely."""


def select_devata(candidates: Sequence[str],
                  fallback_lord: str,
                  rank: Callable[[str], Optional[int]],
                  label: str) -> DevataSelection:
    """Port of `karakSelectDevata`. Ties are NEVER broken by order.

    `rank` returns a comparable integer for a graha, or None when that graha
    cannot be ranked. The D9 caller supplies certified D9 dignity; the browser
    supplied `getScore`, which D9 is ruled not to recreate.

    FIVE MODES:
      lord        no occupant, sign lord used
      sole        exactly one occupant — selected EVEN IF UNGRADED, because
                  there is nothing to compare it against and no comparison is
                  being made
      strongest   several occupants, all rankable, one uniquely highest
      co-indicator several occupants, all rankable, tied at the highest
      unrankable  several occupants and AT LEAST ONE cannot be ranked → NO
                  selection is made at all

    THE `unrankable` MODE IS A FAIL-CLOSED CORRECTION, and it replaces what
    D9-002 shipped. That revision excluded unrankable candidates from the
    comparison and declared a winner among the rest, falling back to calling
    them all co-indicators when none could be ranked. Both were wrong:

      · excluding an unknown and then naming a winner asserts that the excluded
        candidate would have lost, which is not known;
      · `co-indicator` is a POSITIVE finding under the accepted rule — several
        candidates genuinely tied at the highest dignity — and using it for
        "we could not compare these" publishes ignorance as a result.

    So a mixed or wholly unrankable multi-occupant house yields no deity. The
    caller reduces. That is a smaller report and a true one.
    """
    if not candidates:
        return DevataSelection(
            grahas=[fallback_lord], mode="lord", scores=[], unrankable=[],
            basis=[{"factor": f"{label} source",
                    "rule": "no occupant, sign lord used",
                    "graha": fallback_lord}])

    cands = list(candidates)
    if len(cands) == 1:
        only = cands[0]
        return DevataSelection(
            grahas=[only], mode="sole",
            scores=[{"graha": only, "rank": rank(only)}],
            unrankable=[] if rank(only) is not None else [only],
            basis=[{"factor": f"{label} source", "rule": "sole occupant",
                    "graha": only}])

    scored = [{"graha": g, "rank": rank(g)} for g in cands]
    unrankable = [s["graha"] for s in scored if s["rank"] is None]

    if unrankable:
        return DevataSelection(
            grahas=[], mode="unrankable", scores=scored,
            unrankable=unrankable,
            basis=[{"factor": f"{label} source",
                    "rule": ("one or more occupants carry no certified dignity, "
                             "so the occupants cannot be compared and no "
                             "selection is made"),
                    "graha": None}])

    top = max(s["rank"] for s in scored)
    winners = [s["graha"] for s in scored if s["rank"] == top]
    return DevataSelection(
        grahas=winners,
        mode="strongest" if len(winners) == 1 else "co-indicator",
        scores=scored, unrankable=[],
        basis=[{"factor": f"{label} source",
                "rule": (f"highest certified dignity among {len(cands)} occupants"
                         if len(winners) == 1
                         else "certified dignity tied at the highest band, "
                              "co-indicators returned"),
                "graha": None}])
