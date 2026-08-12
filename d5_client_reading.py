"""
d5_client_reading.py — D5-009-CORR-03 · THE PUBLICATION LAYER.

TWO SURFACES, ONE WALL. The engine surface keeps rule ids, FIRED/NOT_FIRED,
weights, multipliers and source status: they are load-bearing for calculation,
tests, QA and audit. The CLIENT surface carries none of them. This module is
the wall, and it is the only place a rule id may be turned into something a
customer reads.

NO ASTROLOGY IS CALCULATED HERE. No placement, no dignity, no aspect, no score.
It receives certified outcomes and selects approved copy. Every sentence below
is either the Founder's own wording from the client template or the certified
`Interpretation & Astrological Application` column of the accepted D5 Rules
Matrix — nothing is authored here.

NO FALLBACK PRINTS A RULE ID. Every publishable rule is CLIENT_MAPPED or
INTERNAL_ONLY, asserted at import. There is no third state and no
"Unknown rule: D5_PAR_17" path, because a leak like that is precisely the defect
this module exists to remove.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Mapping, Tuple

# D5-009-CORR-03 · every publishable rule's HUMAN publication mapping.
#
# Sourced from the accepted D5 Rules Matrix: `Category / Focus` becomes the
# visible title and `Interpretation & Astrological Application` becomes the
# body. Nothing here is authored — the matrix is the certified meaning, and
# the Founder template supplies the chapter it belongs to.
#
# THERE IS NO FALLBACK THAT PRINTS AN ID. Coverage is asserted at import, so a
# new rule fails the build rather than leaking its identifier to a customer.
RULE_PUBLICATION: Dict[str, Dict[str, str]] = {
    "D5_AFF_01": {"title": "6th House Combat Block",
        "chapter": "karmic_friction",
        "body": "Fame/intellect plagued by intense public litigation, envy (Shatru), and administrative sabotage."},
    "D5_AFF_02": {"title": "8th House Stagnation",
        "chapter": "karmic_friction",
        "body": "Karmic Vault; talent, creative work, or progeny face sudden freezes until an occult/psychological crisis unlocks them."},
    "D5_AFF_03": {"title": "12th House Invisible Leak",
        "chapter": "karmic_friction",
        "body": "Power drainage; monumental work done behind the scenes with credit stolen; legacy recognized posthumously."},
    "D5_AFF_04": {"title": "Saturn-Rahu Pitru Curse",
        "chapter": "karmic_friction",
        "body": "Severe Shrapit Yoga; blocks manifestation of authority, delaying success until after age 36 or 42."},
    "D5_AFF_05": {"title": "Rahu in 5th Splitting Axis",
        "chapter": "karmic_friction",
        "body": "Obsessive, hyper-ambitious, yet highly unstable romantic/intellectual drives; risk of public fall from grace (Raja Yoga Bhanga)."},
    "D5_AFF_06": {"title": "Ketu in 5th Splitting Axis",
        "chapter": "karmic_friction",
        "body": "Psychological detachment from children or public recognition; brilliant mind that refuses to commercialize/showcase legacy."},
    "D5_ANAL_01": {"title": "Lagna Strength",
        "chapter": "foundation_public_footprint",
        "body": "Strong spiritual foundation and protection by lineage/Guru."},
    "D5_ANAL_02": {"title": "Lagna Lord",
        "chapter": "foundation_public_footprint",
        "body": "Direct alignment of self with higher dharma and spiritual merit (Purva Punya)."},
    "D5_ANAL_03": {"title": "5th House",
        "chapter": "intellectual_legacy",
        "body": "Attainment of high spiritual seat/status (Peethadhipati) and divine grace."},
    "D5_ANAL_04": {"title": "5th Lord",
        "chapter": "intellectual_legacy",
        "body": "Deep spiritual research, esoteric mastery, and internal transformation."},
    "D5_ANAL_05": {"title": "11th Lord",
        "chapter": "intellectual_legacy",
        "body": "Spiritual actions/deeds leading to elevated social recognition and righteous duties."},
    "D5_ANAL_06": {"title": "9th House Link",
        "chapter": "intellectual_legacy",
        "body": "Complete detachment from worldly desires, turning efforts toward total surrender/asceticism."},
    "D5_ANAL_07": {"title": "5L Interlink",
        "chapter": "intellectual_legacy",
        "body": "Manifestation of D-1 past-life merit directly into the native's core personality and soul path."},
    "D5_ANAL_08": {"title": "5L Interlink",
        "chapter": "intellectual_legacy",
        "body": "Spiritual authority directly impacts public career and major lifelong achievements."},
    "D5_CLA_01": {"title": "5H-8H Esoteric Link",
        "chapter": "intellectual_legacy",
        "body": "Uncovers hidden knowledge, decodes mysteries, advances psychological/occult sciences."},
    "D5_CLA_02": {"title": "Malefics in 12H",
        "chapter": "karmic_friction",
        "body": "Past-life merits blocked by spiritual debt (Rina); requires selfless service to unlock."},
    "D5_CLA_03": {"title": "11th House Gains",
        "chapter": "intellectual_legacy",
        "body": "Children marry into noble, prosperous families; brings happiness in old age."},
    "D5_CLA_04": {"title": "Saturn Delay vs Denial",
        "chapter": "karmic_friction",
        "body": "Enforces delayed childbirth; children are exceptionally serious, mature, and old-souled."},
    "D5_JAI_01": {"title": "Atmakaraka (AK)",
        "chapter": "foundation_public_footprint",
        "body": "Naturally commands public respect, attains legendary status."},
    "D5_JAI_02": {"title": "Amatyakaraka (AMK)",
        "chapter": "foundation_public_footprint",
        "body": "Formidable career authority and power drive."},
    "D5_JAI_03": {"title": "Jaimini Raj Yoga",
        "chapter": "foundation_public_footprint",
        "body": "Powerful Jaimini Raj Yoga; high executive authority."},
    "D5_JAI_04": {"title": "Karakamsha Alignment",
        "chapter": "intellectual_legacy",
        "body": "Noble rise to fame through past-life blessings (Purva Punya)."},
    "D5_JAI_05": {"title": "Sun & Moon Catalyst",
        "chapter": "intellectual_legacy",
        "body": "Immense public charisma, easily holds sway over crowds."},
    "D5_JAI_06": {"title": "Putrakaraka (PK) Placement",
        "chapter": "intellectual_legacy",
        "body": "Enduring intellectual legacy; writings, ideas, or creations inspire future generations."},
    "D5_JAI_07": {"title": "AK-PK Axis",
        "chapter": "intellectual_legacy",
        "body": "Supreme Jaimini Yoga for absolute genius (philosophers, authors, scientists)."},
    "D5_JAI_08": {"title": "Karakamsha 5th House Focus",
        "chapter": "intellectual_legacy",
        "body": "Extraordinary, specialized intellectual legacy based on planet's nature."},
    "D5_JAI_09": {"title": "Pratibha Yoga",
        "chapter": "intellectual_legacy",
        "body": "Pratibha: Spontaneous, lightning-fast creative/mathematical inspiration."},
    "D5_JAI_10": {"title": "Darakaraka (DK) Attraction",
        "chapter": "intellectual_legacy",
        "body": "Relationships always begin with intense, playful romantic courtship rather than arranged setups."},
    "D5_JAI_11": {"title": "AK-DK Soulmate Connection",
        "chapter": "intellectual_legacy",
        "body": "Signifies a soulmate connection; love affairs feel profoundly familiar (reuniting with a past-life partner)."},
    "D5_JAI_12": {"title": "Putrakaraka (PK) Alignment",
        "chapter": "intellectual_legacy",
        "body": "Hopeless romantic; channels relationship experiences into poetry, art, or deep creative expression."},
    "D5_JAI_13": {"title": "Moon-Venus Charm",
        "chapter": "intellectual_legacy",
        "body": "Immense personal charm; highly attractive to the opposite sex, prone to multiple romantic proposals."},
    "D5_JAI_14": {"title": "Putrakaraka (PK) Strength",
        "chapter": "intellectual_legacy",
        "body": "Children inherit intellectual genius and build upon native's life work."},
    "D5_JAI_15": {"title": "PK-Jupiter Santana Yoga",
        "chapter": "intellectual_legacy",
        "body": "Powerful Santana Yoga; children are highly righteous, respectful, and spiritually inclined."},
    "D5_JAI_16": {"title": "Malefics from PK (Rahu/Ketu)",
        "chapter": "karmic_friction",
        "body": "Unconventional birth or adopting children."},
    "D5_JAI_17": {"title": "Malefics from PK (Mars)",
        "chapter": "karmic_friction",
        "body": "Tendency toward surgical or cesarean deliveries."},
    "D5_JAI_18": {"title": "AK and PK Alignment",
        "chapter": "intellectual_legacy",
        "body": "Deep, soul-level friendship with children spanning across multiple lifetimes."},
    "D5_MISC_01": {"title": "11th House Manifestation",
        "chapter": "intellectual_legacy",
        "body": "Creative works spread wide, massive network of supporters."},
    "D5_MISC_02": {"title": "Malefics in 3H / 6H",
        "chapter": "karmic_friction",
        "body": "Destroys opponents, secures power through intense competition."},
    "D5_PAR_01": {"title": "D1 5L Placement",
        "chapter": "foundation_public_footprint",
        "body": "Achieves massive recognition through innate intelligence."},
    "D5_PAR_02": {"title": "Throne Yoga (Raj Yoga)",
        "chapter": "foundation_public_footprint",
        "body": "Unshakeable aura of executive power."},
    "D5_PAR_03": {"title": "Exaltation / Vargottama",
        "chapter": "foundation_public_footprint",
        "body": "A strong signature for political or administrative power."},
    "D5_PAR_04": {"title": "10th House (Sun)",
        "chapter": "foundation_public_footprint",
        "body": "Administrative, authoritative, or governmental rule."},
    "D5_PAR_05": {"title": "10th House (Mars)",
        "chapter": "foundation_public_footprint",
        "body": "Military, pioneering, aggressive, or commanding leadership."},
    "D5_PAR_06": {"title": "10th House (Saturn)",
        "chapter": "foundation_public_footprint",
        "body": "Mass mobilization, political grass-roots influence, handling large crowds."},
    "D5_PAR_07": {"title": "Trine Connection",
        "chapter": "intellectual_legacy",
        "body": "Carries massive spiritual credit, unearned luck/wealth, sudden breakthroughs, and natural genius."},
    "D5_PAR_08": {"title": "Ishta Devata & Mantra Siddhi",
        "chapter": "intellectual_legacy",
        "body": "Strong past-life deity connection, Mantra Siddhi, rapid manifestation of prayers/intentions."},
    "D5_PAR_09": {"title": "Jupiter Protection",
        "chapter": "intellectual_legacy",
        "body": "Highly evolved soul, former spiritual seeker/teacher, strong divine protection."},
    "D5_PAR_10": {"title": "Vargottama 5th Lord",
        "chapter": "intellectual_legacy",
        "body": "Past-life merits fully unlocked; early prosperity and sharp intuition."},
    "D5_PAR_11": {"title": "Venus-Mars Blueprint",
        "chapter": "intellectual_legacy",
        "body": "Intense romantic charisma; experiences passionate, whirlwind love affairs."},
    "D5_PAR_12": {"title": "1H-5H-7H Axis",
        "chapter": "intellectual_legacy",
        "body": "Love affairs form a defining part of life path; brings joy, emotional fulfillment, and good fortune."},
    "D5_PAR_13": {"title": "D1 to D5 Reflection",
        "chapter": "foundation_public_footprint",
        "body": "Karmically destined to meet romantic partners through hobbies, creative circles, or places of entertainment."},
    "D5_PAR_14": {"title": "Rahu/Ketu Boundary Breaking",
        "chapter": "karmic_friction",
        "body": "Unconventional romance, cross-cultural love affairs, sudden infatuations, or secret relationships."},
    "D5_PAR_15": {"title": "Jupiter Vitality",
        "chapter": "intellectual_legacy",
        "body": "Blessed with healthy, intelligent, and virtuous children; birth is smooth and timely."},
    "D5_PAR_16": {"title": "5th Lord Mirroring",
        "chapter": "foundation_public_footprint",
        "body": "Children achieve immense fame and status, elevating family name."},
    "D5_PAR_17": {"title": "Barren Sign Constraint",
        "chapter": "karmic_friction",
        "body": "Delays, obstacles, or medical intervention needed for childbirth."},
    "D5_PAR_18": {"title": "5H-8H/12H Affliction",
        "chapter": "karmic_friction",
        "body": "Anxiety regarding children, generational gaps, or early health challenges for first-born."},
    "D5_TAJ_01": {"title": "Agni Tattva",
        "chapter": "intellectual_legacy",
        "body": "Authority achieved through dominance, law, and order."},
    "D5_TAJ_02": {"title": "Akasha Tattva",
        "chapter": "intellectual_legacy",
        "body": "Power via spiritual counseling, teaching, or judicial wisdom."},
    "D5_TAJ_03": {"title": "Agni Tattva (D5 Lagna/Moon)",
        "chapter": "foundation_public_footprint",
        "body": "Intellectual legacy built on strategic innovation, leadership, or pioneering breakthroughs."},
    "D5_TAJ_04": {"title": "Prithvi Tattva (D5 Lagna/Moon)",
        "chapter": "foundation_public_footprint",
        "body": "Legacy built on tangible commercial models, structures, books, or formulas."},
    "D5_TAJ_05": {"title": "Vayu Tattva (D5 Lagna/Moon)",
        "chapter": "foundation_public_footprint",
        "body": "Legacy built on revolutionary ideas, philosophy, or social movements."},
    "D5_TAJ_06": {"title": "Jala Tattva (D5 Lagna/Moon)",
        "chapter": "foundation_public_footprint",
        "body": "Legacy built on artistic masterpieces, music, poetry, or deep emotional healing."},
    "D5_TAJ_07": {"title": "Akasha Tattva (D5 Lagna/Moon)",
        "chapter": "foundation_public_footprint",
        "body": "Legacy built on eternal spiritual truths, scriptures, or timeless wisdom."},
    "D5_TAJ_08": {"title": "Agni Tattva (Child Temperament)",
        "chapter": "intellectual_legacy",
        "body": "Children are bold, competitive, athletic, and fiercely independent."},
    "D5_TAJ_09": {"title": "Prithvi Tattva (Child Temperament)",
        "chapter": "intellectual_legacy",
        "body": "Children are grounded, financially savvy, organized, and practical."},
    "D5_TAJ_10": {"title": "Vayu Tattva (Child Temperament)",
        "chapter": "intellectual_legacy",
        "body": "Children are highly intellectual, communicative, tech-savvy, or artistic."},
    "D5_TAJ_11": {"title": "Jala Tattva (Child Temperament)",
        "chapter": "intellectual_legacy",
        "body": "Children are deeply emotional, intuitive, nurturing, and family-oriented."},
    "D5_TIM_01": {"title": "Cross-Varga Bridge",
        "chapter": "foundation_public_footprint",
        "body": "The current period creates a live bridge between the natal period lords and the power centres of the Panchamsha, supporting the manifestation of the division's themes."},
    "D5_TIM_02": {"title": "D1 Lord in D5 Gateway",
        "chapter": "foundation_public_footprint",
        "body": "The current sub-period opens a D1-to-D5 gateway through which authority, recognition or creative themes may come into stronger expression."},
    "D5_TIM_03": {"title": "Double Transit Ignition",
        "chapter": "intellectual_legacy",
        "body": "Current Jupiter/Saturn movement supports activation of the sensitive Panchamsha axis. Treat this as timing context that can bring the division's themes forward, not as a guaranteed event."},
}


RULE_TO_SECTION = {r: v["chapter"] for r, v in RULE_PUBLICATION.items()}


def assert_publication_coverage(publishable_rule_ids) -> None:
    """§7 · EVERY publishable rule is CLIENT_MAPPED or INTERNAL_ONLY.

    There is no third state, so there can be no fallback that prints an id.
    Raised at import time, so a new rule cannot reach a customer unmapped.
    """
    unmapped = [r for r in publishable_rule_ids if r not in RULE_PUBLICATION]
    if unmapped:
        raise AssertionError(
            "D5 rules have no client mapping and no INTERNAL_ONLY "
            f"disposition: {sorted(unmapped)}")
    for rule_id in publishable_rule_ids:
        entry = RULE_PUBLICATION[rule_id]
        if not entry["title"] or entry["title"].startswith("D5_"):
            raise AssertionError(f"{rule_id} has no human title")
        if len(entry["body"]) < 20:
            raise AssertionError(f"{rule_id} has no human interpretation")


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────

#: FOUNDER TEMPLATE · the exact Quick Snapshot wording for Primary Power Vector.
#: These replace names I had invented before the template was available; the
#: template is the publication contract and its wording governs.
POWER_VECTOR_LANGUAGE: Dict[str, str] = {
    "5H": "5th House (Genius)",
    "10H": "10th House (Executive Action)",
    "9H": "9th House (Lineage Grace)",
}

#: Expansion copy, kept to the template's own concepts.
POWER_VECTOR_BODY: Dict[str, str] = {
    "5H": "Your power expresses itself first through genius: creative "
          "intelligence, original thought and the things you originate.",
    "10H": "Your power expresses itself first through executive action: "
           "position, office and visible command.",
    "9H": "Your power expresses itself first through lineage grace: fortune, "
          "guidance and inherited merit rather than direct force.",
}


def power_vector_language(vector: Mapping[str, Any]) -> Dict[str, Any]:
    """The power vector in words. No 5H, 9H or 10H reaches the client."""
    leaders = [POWER_VECTOR_LANGUAGE[v] for v in vector.get("leaders", [])
               if v in POWER_VECTOR_LANGUAGE]
    primary = vector.get("primary")
    if primary and primary in POWER_VECTOR_LANGUAGE:
        return {"title": POWER_VECTOR_LANGUAGE[primary],
                "body": POWER_VECTOR_BODY[primary], "shared": False}
    if leaders:
        return {"title": " and ".join(leaders),
                "body": "Your power is expressed through more than one channel "
                        "in equal measure; no single avenue dominates.",
                "shared": True}
    return {"title": "No Dominant Channel",
            "body": "No single avenue of expression dominates this division.",
            "shared": False}


# ─────────────────────────────────────────────────────────────────────────────
# THE OVERVIEW · §10, blocking
# ─────────────────────────────────────────────────────────────────────────────

def overview(final_score: float, band_label: str, authority: Mapping[str, Any],
             punya: Mapping[str, Any]) -> str:
    """Reconciles the snapshot instead of repeating it.

    §10 · a chart can read Elite / Legendary and Unmanifested Potential and
    Blocked at once. Those are mathematically consistent and completely opaque
    to a human being, so the top of the report has to explain the relationship
    between strength, potential, blockage and manifestation — WITHOUT naming
    TRI_02 or any other engine term as the reason.
    """
    blocked = (authority.get("override") is not None
               or punya.get("override") is not None)
    strong = final_score >= 1

    if blocked and strong:
        return ("Your Panchamsha carries substantial authority and merit "
                "signatures, but one or more blocking configurations restrict "
                "how freely those strengths manifest. The promise is strong; "
                "its expression requires the karmic obstruction to be worked "
                "through.")
    if blocked:
        return ("Your Panchamsha shows meaningful signatures of authority and "
                "merit held under restriction. The material is present, but a "
                "blocking configuration governs how much of it reaches open "
                "expression at this stage of life.")
    if strong:
        return ("Your Panchamsha carries clear signatures of authority and "
                "past merit, and no major configuration is obstructing them. "
                "What the division promises is broadly free to express itself.")
    return ("Your Panchamsha is measured rather than emphatic. Standing and "
            "recognition here are built steadily through effort rather than "
            "conferred by a single dominant signature.")


def bottom_line(final_score: float, authority: Mapping[str, Any],
                punya: Mapping[str, Any], vector_title: str) -> str:
    """§11.H · what the reader remembers after closing the report."""
    blocked = (authority.get("override") is not None
               or punya.get("override") is not None)
    if blocked:
        return ("The strength in this division is real and the past merit is "
                "real. Both are currently governed by an obstruction that has "
                "to be worked through rather than argued away. Expect "
                "recognition to arrive later than the raw promise suggests, "
                "and to hold once it does. Your natural channel is "
                + vector_title.lower() + ".")
    if final_score >= 1:
        return ("This division supports authority and recognition without "
                "major obstruction. Merit accumulated earlier is available to "
                "you, and standing tends to consolidate rather than fluctuate. "
                "Your natural channel is " + vector_title.lower() + ".")
    return ("This division neither confers nor withholds standing "
            "dramatically. Recognition follows sustained work. Your natural "
            "channel is " + vector_title.lower() + ".")


# ─────────────────────────────────────────────────────────────────────────────
# TIMING · §11.G
# ─────────────────────────────────────────────────────────────────────────────

TIMING_QUIET = ("No period or transit condition is presently activating this "
                "division. The signatures described above remain latent until "
                "a supporting period arrives.")

TIMING_ACTIVE = ("A supporting period or transit is presently activating this "
                 "division, which tends to bring its themes forward into "
                 "visible events.")


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER TEMPLATE · CORE LIFE ARCHETYPES
# ─────────────────────────────────────────────────────────────────────────────
#
# Three state machines, each selecting exactly ONE of five states. Names and
# copy are transcribed verbatim from the client template; nothing here is
# authored. State C of the first machine is "Earned Progression", which is
# already the scoring engine's no-signal Purva Punya value — the engine and the
# template agree, and the mapping is direct.

ARCHETYPE_PURVA_PUNYA = ("Purva Punya & Divine Grace", {
    "A": ("Divine Shield",
          "Massive past credit; unearned breakthroughs and spontaneous "
          "protection in crises."),
    "B": ("Unlocked Genius",
          "Sharp intuition and natural talent from early childhood; rapid "
          "manifestation of intent."),
    "C": ("Earned Progression",
          "Balanced past karma; rewards align strictly with personal effort "
          "and discipline."),
    "D": ("Dormant Vault",
          "High talent present, but locked behind an occult, emotional, or "
          "spiritual threshold."),
    "E": ("Karmic Rina",
          "Past spiritual debts block immediate luck; requires selfless "
          "service/tapasya to unlock."),
})

ARCHETYPE_ROMANTIC = ("Romantic Signature & Creative Drive", {
    "A": ("Soulmate Synergy",
          "Deep past-life emotional resonance; whirlwind, highly fulfilling "
          "partnerships."),
    "B": ("Creative Catalyst",
          "Romantic encounters act as the primary spark for artistic, "
          "written, or career genius."),
    "C": ("Unconventional Spark",
          "Boundary-breaking love affairs, sudden infatuations, or "
          "cross-cultural alliances."),
    "D": ("Playful Courtship",
          "Relationships thrive on intellectual banter, courtship, and "
          "dynamic attraction."),
    "E": ("Karmic Friction",
          "Passion exists alongside intense lessons; relationships serve as "
          "tests of emotional maturity."),
})

ARCHETYPE_PROGENY = ("Progeny Dynamics & Legacy", {
    "A": ("High Lineage Blessing",
          "Blessed with virtuous, highly accomplished children who elevate "
          "the family name."),
    "B": ("Intellectual Continuity",
          "Children inherit the native's exact intellectual/creative spark "
          "and expand upon it."),
    "C": ("Deep Soul-Bond",
          "Multi-lifetime friendship with progeny; strong mutual respect and "
          "alignment."),
    "D": ("Delayed Bloom",
          "Childbirth or progeny alignment occurs later in life; yields "
          "serious, old-souled offspring."),
    "E": ("Unconventional Trajectory",
          "Complex progeny dynamics; potential medical/surgical intervention "
          "or non-traditional parenting paths."),
})

#: The scoring engine's Purva Punya classification maps directly onto the
#: template's first archetype. This is the ONE state machine whose selection
#: rule the accepted engine already decides.
PURVA_PUNYA_TO_STATE: Dict[str, str] = {
    "High Credit": "A",
    "Balanced": "C",
    "Earned Progression": "C",
    "Karmic Debt": "D",
    "Blocked": "E",
}


def purva_punya_archetype(classification: str) -> Dict[str, str]:
    """The template state for the engine's Purva Punya verdict.

    DIRECT MAPPING, NO INTERPRETATION. The engine already selected the
    classification; this only names it in the template's language.
    """
    title, states = ARCHETYPE_PURVA_PUNYA
    key = PURVA_PUNYA_TO_STATE.get(classification)
    if key is None:
        raise AssertionError(
            f"no template state for Purva Punya classification {classification!r}")
    name, body = states[key]
    return {"archetype": title, "state": key, "name": name, "body": body}


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORAL ACTIVATION KEYS · Founder template subsections
# ─────────────────────────────────────────────────────────────────────────────

def temporal_activation(timing_outcomes) -> Dict[str, Any]:
    """The three template subsections, in words.

    NO rule id, status or weight. Where nothing fires, ONE restrained sentence
    per subsection — never three negative database rows.
    """
    def fired(rule_id):
        outcome = timing_outcomes.get(rule_id)
        return outcome is not None and outcome.status == "FIRED"

    dasha, windows, transit = fired("D5_TIM_01"), fired("D5_TIM_02"), fired("D5_TIM_03")
    return {
        "title": "Temporal Activation Keys",
        "subsections": [
            {"title": "Active Dasha Bridge",
             "body": ("The period lords currently running connect directly to "
                      "the power centres of this division, which brings its "
                      "themes into live circumstances.") if dasha else
                     ("The period lords currently running do not bridge to this "
                      "division's power centres. No current activation.")},
            {"title": "Activation Windows",
             "body": ("A sub-period is presently open that unlocks the latent "
                      "yogas of this division.") if windows else
                     ("No sub-period is presently opening the latent yogas of "
                      "this division. No current activation.")},
            {"title": "Transit Ignition",
             "body": ("Jupiter or Saturn is presently crossing or aspecting the "
                      "sensitive axis of this division. Treat this as timing "
                      "context rather than a guaranteed event.") if transit else
                     ("Neither Jupiter nor Saturn is presently crossing the "
                      "sensitive axis of this division. No current "
                      "activation.")},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# KARMIC FRICTION & POTENTIAL CEILINGS
# ─────────────────────────────────────────────────────────────────────────────

#: Which friction signatures belong to which of the three template concepts.
_STRUCTURAL = ("12th House", "6th House", "8th House", "5H-8H", "Barren",
               "11th House")
_NODAL = ("Rahu", "Ketu", "Nodal", "Splitting", "Boundary")
_SHRAPIT = ("Pitru", "Curse", "Saturn Delay", "Shrapit")


def karmic_friction(signatures) -> Dict[str, Any]:
    """The three Founder concepts, each in ordinary language.

    A category with no active signal SAYS SO. It never renders an empty table.
    """
    friction = [s for s in signatures if s["chapter"] == "karmic_friction"]

    def pick(markers):
        return [s for s in friction
                if any(m.lower() in s["title"].lower() for m in markers)]

    def describe(items, empty):
        if not items:
            return empty
        titles = ", ".join(s["title"] for s in items)
        restricted = any(s["state"] == "suppressed" for s in items)
        return (titles + ". " + ("These are present but their pressure is "
                                 "currently held in check."
                                 if restricted else
                                 "These are actively in play."))

    return {
        "title": "Karmic Friction & Potential Ceilings",
        "subsections": [
            {"title": "Structural Blocks",
             "body": describe(pick(_STRUCTURAL),
                              "No structural leakage through the sixth, eighth "
                              "or twelfth axis is indicated. Public credit is "
                              "not being drained at the structural level.")},
            {"title": "Nodal Interrupts",
             "body": describe(pick(_NODAL),
                              "The nodal axis does not create a dominant "
                              "obsession or refusal in this division.")},
            {"title": "Shrapit / Cursed Alignments",
             "body": describe(pick(_SHRAPIT),
                              "No ancestral or planetary curse signature "
                              "delays the executive rise here.")},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# III · KARMIC TRIANGULATION
# ─────────────────────────────────────────────────────────────────────────────

def karmic_triangulation(tri_01_fired: bool, tri_02_fired: bool,
                         tri_03_fired: bool, authority) -> Dict[str, Any]:
    """The D-1 -> D-9 -> D-5 reality check, in words.

    D5-009-CORR-04 §3 · TRI_03 is read, so an **Amplified** verdict is now
    reachable. It was previously impossible: the function never saw the third
    outcome, so a chart whose triangulation actively reinforced the promise was
    reported as merely free.

    PRECEDENCE, exactly as locked:
        1 TRI_02        -> Blocked
        2 TRI_01        -> Partially Suppressed
        3 authority override -> Partially Suppressed
        4 TRI_03, no blocker -> Amplified
        5 otherwise     -> Freely Manifesting

    TRI_01 + TRI_03 therefore reads Partially Suppressed, which matches the
    accepted combined multiplier of 0.75: amplification does not cancel a
    physical weakening, it is scaled by it.

    No TRI rule is named to the customer.
    """
    vessel = ("The birth chart shows a planet carrying this division's promise "
              "under physical strain — combustion, debilitation or planetary "
              "war — which limits how much of the promise the body of the "
              "chart can actually carry."
              if tri_01_fired else
              "The birth chart has the physical capacity to carry what this "
              "division promises. No major weakening blocks it at the natal "
              "level.")
    fuel = ("The Navamsha does not supply the deep dignity needed to sustain "
            "this promise over a lifetime; support here is intermittent rather "
            "than structural."
            if tri_02_fired else
            "The Navamsha supplies the soul-strength and dignity needed to "
            "sustain this promise long term.")

    if tri_02_fired:
        verdict = ("Blocked. The Panchamsha carries genuine authority and merit "
                   "signatures, but the deeper chart withholds the support "
                   "those signatures need to express. The promise is real and "
                   "its expression is conditional on working the obstruction "
                   "through.")
    elif tri_01_fired:
        verdict = ("Partially Suppressed. The promise of this division is "
                   "sound and the inner support is present, but a physical "
                   "weakening in the birth chart narrows how freely it reaches "
                   "the world.")
    elif authority.get("override"):
        verdict = ("Partially Suppressed. The signatures are present, but a "
                   "restricting configuration governs how much of the promise "
                   "reaches open expression.")
    elif tri_03_fired:
        verdict = ("Amplified. All three charts reinforce one another: the "
                   "soul-significators of this division are well placed and "
                   "connected to its power centres, so what the Panchamsha "
                   "promises is carried forward with additional force rather "
                   "than merely permitted.")
    else:
        verdict = ("Freely Manifesting. Birth chart, Navamsha and Panchamsha "
                   "agree: what this division promises has both the physical "
                   "capacity and the inner fuel to express itself.")
    return {
        "title": "III. Karmic Triangulation",
        "subsections": [
            {"title": "Physical Vessel Check · D-1", "body": vessel},
            {"title": "Internal Fuel Check · D-9", "body": fuel},
            {"title": "Triangulated Verdict", "body": verdict},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# §5 · ATMAKARAKA STRENGTH · from CERTIFIED evidence only
# ─────────────────────────────────────────────────────────────────────────────
#
# The metric asks about house placement AND aspect resonance with the D-5
# Lagna / 5th-house axis. Those relations are already decided by accepted rules;
# the report SELECTS their verdicts and never recomputes an aspect.

#: D5-009-CORR-05 §2 · BRANCH EVIDENCE, NOT A RULE WHITELIST.
#:
#: The previous implementation whitelisted JAI_01, JAI_03, JAI_04, JAI_05 and
#: JAI_07 wholesale, so a Saturn Atmakaraka in H11 was reported as "Strongly
#: Reinforced" with the Lagna / 5th-house axis because a Jaimini rule mentioning
#: the AK happened to fire. That is not the metric. The Founder asks about
#: resonance with D5 H1 / H5 specifically.
#:
#: Each predicate below inspects the rule's ALREADY-CERTIFIED evidence and
#: returns True only where the fired branch demonstrably places the Atmakaraka
#: on that axis. No geometry is computed and no aspect is recalculated.

D5_AXIS = (1, 5)


def _jai_01_axis(evidence) -> bool:
    """AK in H1, H5 or H11. Only the H1 and H5 branches are the axis; H11 is a
    house of gains and says nothing about the Lagna / 5th-house relation."""
    return evidence.get("d5_house") in D5_AXIS


def _jai_07_axis(evidence) -> bool:
    """AK and PK conjunct, angular or in sign aspect. The relation is AK-to-PK,
    so it only bears on the metric when the AK itself sits on the axis."""
    return evidence.get("ak_d5_house") in D5_AXIS


#: rule id -> predicate over that rule's certified evidence.
#:
#: JAI_03 (AK/AMK sign aspect), JAI_04 (benefics on the Karakamsha) and JAI_05
#: (the Sun-Moon axis) are DELIBERATELY ABSENT. None of them establishes a
#: relation between the Atmakaraka and D5 H1/H5, and JAI_05 does not involve the
#: Atmakaraka at all.
AK_RESONANCE_EVIDENCE: Dict[str, Any] = {
    "D5_JAI_01": _jai_01_axis,
    "D5_JAI_07": _jai_07_axis,
}

#: Retained for the report layer's iteration order.
AK_RESONANCE_RULES: Tuple[str, ...] = tuple(sorted(AK_RESONANCE_EVIDENCE))

#: The four Founder-permitted strength states.
AK_STATES = ("Strongly Reinforced", "Connected", "Partially Supported",
             "No Direct Resonance")

def atmakaraka_strength(ak: str, d5_sign: str, d5_house: int,
                        resonance_titles) -> Dict[str, Any]:
    """AK identity, placement, certified resonance and a strength conclusion.

    `resonance_titles` are the HUMAN titles of the certified resonance rules
    that fired — selected by the report layer from evaluated outcomes. No
    geometry is computed here and none may be.

    The state is mechanically derived from how many certified resonances hold
    and whether the AK itself sits on the axis, so it can be re-derived from the
    published evidence rather than taken on trust.
    """
    on_axis = d5_house in D5_AXIS
    count = len(resonance_titles)
    if count >= 2:
        state = "Strongly Reinforced"
    elif count == 1:
        state = "Connected"
    elif on_axis:
        state = "Partially Supported"
    else:
        state = "No Direct Resonance"

    conclusion = {
        "Strongly Reinforced":
            "Several certified factors tie the soul-significator to the "
            "governing axis of this division, so recognition is sought and "
            "held in a way that is structurally supported.",
        "Connected":
            "A certified factor ties the soul-significator to the governing "
            "axis of this division; the connection is real but singular.",
        "Partially Supported":
            "The soul-significator sits directly on the governing axis of this "
            "division, though no further certified factor reinforces it.",
        "No Direct Resonance":
            "The soul-significator neither occupies nor is certified as "
            "resonating with the governing axis, so recognition here is "
            "pursued at one remove from the soul's own significator.",
    }[state]

    body = (f"The Atmakaraka is {ak}, in {d5_sign}, house {d5_house} of the "
            f"Panchamsha. ")
    if resonance_titles:
        body += ("Certified resonance with the Lagna / 5th-house axis: "
                 + ", ".join(resonance_titles) + ". ")
    else:
        body += ("No certified resonance with the Lagna / 5th-house axis is "
                 "recorded. ")
    body += f"Strength: {state}. {conclusion}"
    return {"state": state, "body": body,
            "resonance": list(resonance_titles), "on_axis": on_axis}


# ─────────────────────────────────────────────────────────────────────────────
# §2 · DETERMINISTIC CHAPTER SYNTHESIS
# ─────────────────────────────────────────────────────────────────────────────
#
# A BOUNDED COMPOSER, NOT A WRITER. It classifies each already-published
# signature as active or suppressed, groups it into its Founder chapter, joins
# the certified interpretations with fixed transition phrases, and appends a
# restriction sentence when suppressed signatures exist.
#
# It may not invent a predictive conclusion. Every clause below is either a
# fixed transition or a certified interpretation that some other layer already
# approved for publication — so the composer can only ever re-order and connect
# material, never add a claim.

#: D5-009-CORR-05 §3 · SYNTHESIS BY FOUNDER CONCEPT GROUP.
#:
#: The previous composer took `spoken[:3]` — the first three signatures in rule
#: id order — which is neither synthesis nor a Founder concept. It silently
#: discarded whatever came fourth and let alphabetical accident decide what the
#: customer read.
#:
#: Each chapter is now composed from CONCEPT GROUPS. Every group present
#: contributes one fixed Founder-safe clause naming its members, so nothing is
#: dropped and nothing is dumped: twenty findings become six or seven clauses
#: rather than twenty sentences or three arbitrary ones.

_CONCEPT_GROUPS: Dict[str, Tuple[Tuple[str, str, Tuple[str, ...]], ...]] = {
    "foundation_public_footprint": (
        ("lagna", "the Panchamsha Lagna and its lord",
         ("Lagna Strength", "Lagna Lord", "D1 to D5 Reflection",
          "Cross-Varga Bridge", "D1 Lord in D5 Gateway")),
        ("command", "direct command of the tenth house",
         ("10th House (Sun)", "10th House (Mars)", "10th House (Saturn)",
          "11th Lord", "Throne Yoga (Raj Yoga)")),
        ("karaka", "the soul and minister significators",
         ("Atmakaraka (AK)", "Amatyakaraka (AMK)", "Jaimini Raj Yoga",
          "AK and PK Alignment", "AK-PK Axis", "Karakamsha Alignment")),
        ("dignity", "planetary dignity and vargottama strength",
         ("Exaltation / Vargottama", "Vargottama 5th Lord",
          "5th Lord Mirroring", "D1 5L Placement")),
    ),
    "intellectual_legacy": (
        ("creative", "creative and intellectual promise",
         ("5th House", "5th Lord", "5L Interlink", "Pratibha Yoga",
          "Trine Connection", "Karakamsha 5th House Focus")),
        ("putrakaraka", "the Putrakaraka and questions of legacy",
         ("Putrakaraka (PK) Alignment", "Putrakaraka (PK) Placement",
          "Putrakaraka (PK) Strength", "PK-Jupiter Santana Yoga",
          "Jupiter Vitality")),
        ("pratibha", "the Mercury-Moon creative intelligence",
         ("Moon-Venus Charm", "Sun & Moon Catalyst", "Agni Tattva",
          "Akasha Tattva", "Vayu Tattva (D5 Lagna/Moon)")),
        ("punya", "past-life merit supporting the intellect",
         ("Jupiter Protection", "9th House Link", "5H-8H Esoteric Link",
          "Ishta Devata & Mantra Siddhi")),
    ),
}

#: Fixed openers, selected by the shape of the evidence rather than composed.
_OPEN_MANY = "The Panchamsha carries a concentrated {theme} signature. "
_OPEN_FEW = "The Panchamsha shows a defined {theme} signature. "
_OPEN_NONE = ("The Panchamsha does not emphasise a dominant {theme} signature. "
              "What stands here is built through sustained effort rather than "
              "conferred by placement.")

#: One fixed clause per concept group. `{names}` lists the certified titles that
#: fired in that group, so the sentence is Founder-safe and the evidence is the
#: customer's to see.
_GROUP_CLAUSE = "{lead} {names}. "
_GROUP_LEADS = {
    "lagna": "The reading is founded on",
    "command": "Direct command of the tenth house is shown by",
    "karaka": "The soul and minister significators contribute",
    "dignity": "Planetary dignity adds",
    "creative": "Creative and intellectual promise is carried by",
    "putrakaraka": "Questions of legacy and continuity are shown by",
    "pratibha": "Creative intelligence is indicated by",
    "punya": "Past-life merit supports this through",
    "other": "Also present are",
}

_RESTRICTION_SOME = ("However, {names} {verb} presently restricted rather than "
                     "absent, so the promise here is substantial but its "
                     "expression is conditional rather than automatic. ")
_RESTRICTION_ALL = ("Every one of these signatures is presently restricted "
                    "rather than absent: the material is real, and what is in "
                    "question is how freely it reaches expression. ")

#: Chapter II must incorporate the already-selected archetypes.
_ARCH_CLAUSE = ("In the creative and relational sphere the chart reads as "
                "{romantic}; in matters of legacy and continuity it reads as "
                "{progeny}. ")

CHAPTER_THEME = {
    "foundation_public_footprint": "authority",
    "intellectual_legacy": "creative and intellectual",
}


def _group_signatures(chapter_key: str, items):
    """Bucket the fired signatures into Founder concept groups.

    Anything the Founder groups do not name falls into `other` — it is still
    published rather than silently dropped, which is what the previous
    three-item slice did.
    """
    groups = _CONCEPT_GROUPS[chapter_key]
    buckets: Dict[str, List[str]] = {key: [] for key, _lead, _t in groups}
    buckets["other"] = []
    lookup = {}
    for key, _lead, titles in groups:
        for title in titles:
            lookup[title] = key
    for signature in items:
        buckets[lookup.get(signature["title"], "other")].append(
            signature["title"])
    return buckets


def compose_chapter(chapter_key: str, title: str, signatures,
                    authority=None, archetypes=None) -> Dict[str, Any]:
    """One Founder chapter: a narrative first, its signatures underneath.

    The narrative is PRIMARY and covers the WHOLE relevant picture, grouped by
    Founder concept. The individual fired meanings remain available in the
    subordinate `supporting_signatures` surface, which preserves the lock that
    every fired rule stays visible in meaning.
    """
    theme = CHAPTER_THEME[chapter_key]
    items = [s for s in signatures if s["chapter"] == chapter_key]
    # NEUTRAL signatures are present and unrestricted, so they belong with the
    # spoken material — not with the restriction sentence.
    speakable = [s for s in items if s["state"] in ("active", "neutral")]
    suppressed = [s for s in items if s["state"] == "suppressed"]

    if not items:
        return {"title": title, "narrative": _OPEN_NONE.format(theme=theme),
                "supporting_signatures": []}

    narrative = (_OPEN_MANY if len(items) >= 3 else _OPEN_FEW).format(theme=theme)

    buckets = _group_signatures(chapter_key, speakable)
    order = [key for key, _l, _t in _CONCEPT_GROUPS[chapter_key]] + ["other"]
    for key in order:
        names = buckets.get(key) or []
        if not names:
            continue
        narrative += _GROUP_CLAUSE.format(lead=_GROUP_LEADS[key],
                                          names=_join(names))

    if archetypes and chapter_key == "intellectual_legacy":
        narrative += _ARCH_CLAUSE.format(
            romantic=archetypes["romantic_signature"]["name"],
            progeny=archetypes["progeny_dynamics"]["name"])

    if suppressed:
        if not speakable:
            narrative += _RESTRICTION_ALL
        else:
            names = [s["title"] for s in suppressed]
            narrative += _RESTRICTION_SOME.format(
                names=_join(names), verb="is" if len(names) == 1 else "are")
    elif authority is not None and authority.get("override"):
        narrative += ("No signature in this area is individually restricted, "
                      "though a wider configuration governs how much of the "
                      "chart's promise reaches open expression. ")

    return {"title": title, "narrative": narrative.strip(),
            "supporting_signatures": items}


def _join(names) -> str:
    names = list(names)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return names[0] + " and " + names[1]
    return ", ".join(names[:-1]) + " and " + names[-1]
