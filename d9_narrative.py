"""D9-002-CORR-03 · the EXTRACTIVE narrative contract for `/d9report`.

THE PROVIDER NO LONGER WRITES SENTENCES.

Until CORR-02 this module took free prose and scanned it against a growing
blacklist. Adversarial QA broke that model twice — a comma defeated the sentence
shapes, and alternate wording defeated the vocabulary families. Enumerating
prohibited language around an unbounded generator is the wrong containment model,
and a third dictionary would have failed the same way.

The contract is now EXTRACTIVE:

    server publishes approved atoms  ->  provider returns a composition plan
    ->  server renders the narrative from its own strings

The provider returns ordered atom ids and optional connector ids drawn from a
finite server-owned vocabulary. There is NO free-text field in the schema, so an
unknown key, a prose value, an unknown atom, an unknown connector, a duplicate or
a bad cardinality all fail closed. No provider-authored proposition can reach
publication, because the provider authors no propositions.

The provider keeps selection, ordering and synthesis structure, which is the part
it is genuinely good at. It loses assertion.

ONE SECTION still. The Integrated Soul Narrative is the only long-form output,
and it now synthesises atoms the structured report already published.
"""

import json
import re
from typing import Any, Dict, List, Optional

from d9_client_reading import (
    PublicationViolation,
    assert_publication_safe,
)

NARRATIVE_SECTION = "integrated_soul_narrative"
COMPOSITION_KEY = "composition"

MIN_ATOMS = 3
MAX_ATOMS = 8

# CORR-04 · QA-15. Atom count alone permitted a three-atom, two-domain
# composition — a dressed-up replay of one narrow part of the report rather than
# the "one genuinely integrative essay" the contract asks for. Diversity of
# substantive domain is the eligibility rule now, and atom count is only a floor.
MIN_SUBSTANTIVE_DOMAINS = 3

# ─── the finite server-owned connector vocabulary ────────────────────────────
#
# The provider chooses WHICH connective shape joins two atoms. It does not write
# the words. Every string below is server-authored and none carries a
# proposition of its own.

# CORR-04 · QA-14. CONNECTORS MUST BE SEMANTICALLY NEUTRAL.
#
# The provider stopped authoring facts in CORR-03 and then authored a RELATION
# between facts instead. `which_is_why` turned two unrelated certified atoms into
# "results arrive through doing the work properly … which is part of why some
# relationship indicators remain provisional." Neither atom says that, and no
# certified source says it. Causality is a proposition, and the provider is not
# permitted propositions.
#
# Removed: which_is_why (causal), underneath (hierarchical), carried_forward
# (derivational), in_practice (interpretive), at_the_same_time (implies
# simultaneity as significant), and_yet (contradictory).
#
# What remains is additive only. The provider may order and juxtapose. It may not
# decide that one finding explains, causes, underlies or contradicts another.

CONNECTORS: Dict[str, str] = {
    "none": "",
    "also": "There is also this: ",
    "alongside": "Alongside that, ",
    "another_part": "Another part of the same picture: ",
}

# Kept as an explicit record so a future edit re-adding one of these has to
# delete this list first, and a test asserts none of them is in CONNECTORS.
REMOVED_CAUSAL_CONNECTORS = ("which_is_why", "underneath", "carried_forward",
                             "in_practice", "at_the_same_time", "and_yet")

# CORR-05 · QA-18. The frames are owned by the seed layer and carry NO technical
# vocabulary. The previous opening began "the navamsha says…", which broke
# contract 6.1's zero-technical-terminology rule in the server's own words.
from d9_client_reading import SYNTHESIS_CLOSING as CLOSING  # noqa: E402
from d9_client_reading import SYNTHESIS_OPENING as OPENING  # noqa: E402


class NarrativeContractError(Exception):
    """The provider response does not satisfy the composition contract."""


def parse_provider_output(raw: str) -> List[Dict[str, Optional[str]]]:
    """Parse the composition plan. Fail closed at every step.

    A free-text field anywhere in the response is itself a violation, not
    something to be scanned — its presence means the provider is answering a
    contract this module does not offer.
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise NarrativeContractError(f"provider output is not JSON: {exc}")
    if not isinstance(payload, dict):
        raise NarrativeContractError("provider output is not an object")
    if set(payload) != {COMPOSITION_KEY}:
        raise NarrativeContractError(
            f"expected exactly {{{COMPOSITION_KEY!r}}}, got {sorted(payload)}")

    plan = payload[COMPOSITION_KEY]
    if not isinstance(plan, list):
        raise NarrativeContractError("composition is not a list")

    out: List[Dict[str, Optional[str]]] = []
    for i, entry in enumerate(plan):
        if not isinstance(entry, dict):
            raise NarrativeContractError(f"composition[{i}] is not an object")
        extra = set(entry) - {"atom", "connector"}
        if extra:
            raise NarrativeContractError(
                f"composition[{i}] carries unexpected keys {sorted(extra)}; "
                f"there is no free-text field in this contract")
        atom = entry.get("atom")
        if not isinstance(atom, str) or not atom:
            raise NarrativeContractError(f"composition[{i}].atom is not an id")
        connector = entry.get("connector")
        if connector is not None and not isinstance(connector, str):
            raise NarrativeContractError(
                f"composition[{i}].connector is not an id")
        out.append({"atom": atom, "connector": connector})
    return out


def validate_composition(plan: List[Dict[str, Optional[str]]],
                         pool: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """Cardinality, membership, uniqueness and connector vocabulary."""
    if not (MIN_ATOMS <= len(plan) <= MAX_ATOMS):
        raise NarrativeContractError(
            f"composition must select between {MIN_ATOMS} and {MAX_ATOMS} "
            f"atoms, got {len(plan)}")

    known = set(pool["atom_ids"])
    substantive_of = {a["id"]: a.get("substantive", True) for a in pool["atoms"]}
    domain_of = {a["id"]: a["domain"] for a in pool["atoms"]}
    seen = set()
    for i, entry in enumerate(plan):
        atom = entry["atom"]
        if atom not in known:
            # This is the case that matters most: a withheld provisional
            # partnership finding is NOT in the pool, so a provider that tries
            # to reference one lands here.
            raise NarrativeContractError(
                f"composition[{i}] references unknown atom {atom!r}")
        if atom in seen:
            raise NarrativeContractError(f"atom {atom!r} selected more than once")
        seen.add(atom)
        connector = entry["connector"]
        if connector is not None and connector not in CONNECTORS:
            raise NarrativeContractError(
                f"composition[{i}] uses unknown connector {connector!r}")

    # Domain diversity, counted over SUBSTANTIVE atoms only. The provisional
    # notice is a disclosure about what is absent and cannot make its domain
    # count toward a synthesis.
    domains = {domain_of[e["atom"]] for e in plan if substantive_of[e["atom"]]}
    if len(domains) < MIN_SUBSTANTIVE_DOMAINS:
        raise NarrativeContractError(
            f"composition draws on {len(domains)} substantive domain(s); a "
            f"synthesis must span at least {MIN_SUBSTANTIVE_DOMAINS}")
    return plan


def render_narrative(plan: List[Dict[str, Optional[str]]],
                     pool: Dict[str, Any]) -> str:
    """Build the narrative from SERVER strings only.

    Nothing the provider sent appears in the output. It chose the order and the
    connective shape; every word here was authored server-side and already
    published in the structured report.
    """
    by_id = {a["id"]: a for a in pool["atoms"]}
    parts = [OPENING]
    for i, entry in enumerate(plan):
        text = by_id[entry["atom"]]["text"]
        connector = CONNECTORS.get(entry["connector"] or "none", "")
        if i == 0 or not connector:
            parts.append(text + " ")
        else:
            lead = text[0].lower() + text[1:] if text[:1].isupper() else text
            parts.append(connector + lead + " ")
    parts.append(CLOSING)
    return "".join(parts).strip()


def build_narrative(raw: str, pool: Dict[str, Any]) -> Dict[str, str]:
    """Parse, validate, render, then scan the SERVER's own output.

    The final scan is defence in depth rather than the containment mechanism. It
    cannot catch a provider assertion, because there are none; it catches a
    future edit that lets an unsafe string into the atom pool.
    """
    plan = parse_provider_output(raw)
    validate_composition(plan, pool)
    text = render_narrative(plan, pool)
    sections = {NARRATIVE_SECTION: text}
    assert_publication_safe(sections)
    return sections


def build_provider_instruction(pool: Dict[str, Any]) -> str:
    """The system prompt. Names the schema and the closed vocabularies.

    The prohibitions that dominated earlier revisions are largely gone, and not
    because they stopped mattering — because the schema no longer has anywhere to
    put a prohibited claim. An instruction is a request; a contract without a
    free-text field is a guarantee.
    """
    schema = json.dumps(
        {COMPOSITION_KEY: [{"atom": "<atom id>", "connector": "<connector id or null>"}]},
        indent=2)
    domains = pool.get("substantive_domains") or []
    n = len(domains)
    if n <= MIN_SUBSTANTIVE_DOMAINS:
        spread = (f"Exactly {n} substantive domains are available, so your "
                  f"composition must contain AT LEAST ONE ATOM FROM EACH OF "
                  f"THEM. Missing any one is a discarded response.")
    else:
        spread = (f"{n} substantive domains are available. Your composition must "
                  f"draw on AT LEAST {MIN_SUBSTANTIVE_DOMAINS} DISTINCT ones.")

    return f"""You are composing the closing synthesis of a reading.

You do NOT write sentences. Every sentence has already been written. Your job is
to choose which of the supplied statements belong in the closing synthesis, in
what order, and how each should be joined to the one before it.

Return ONLY a JSON object with exactly this shape:

{schema}

Rules:
1. `atom` must be an id from the supplied atom list. Nothing else is accepted.
2. `connector` must be an id from the supplied connector list, or null.
3. Select between {MIN_ATOMS} and {MAX_ATOMS} atoms. No atom twice.
4. DOMAIN SPREAD IS REQUIRED, AND IT IS THE RULE MOST RESPONSES GET WRONG.
   Every atom carries a `domain` and a `substantive` flag.
   {spread}
   Atoms with `substantive: false` DO NOT COUNT toward that minimum. They are
   optional disclosures and may only be added to a composition that already
   satisfies the requirement on its own. A composition of three atoms drawn
   from two substantive domains plus one disclosure is discarded.
5. Order them so the synthesis reads as one thought rather than a list. Put what
   frames the person first and what they can act on last.
6. There is no field for your own words. Do not add one. A response containing
   any other key is discarded.
7. Some findings are deliberately absent from the atom list. Do not refer to
   anything that is not there.
8. Return raw JSON. No markdown fence, no preamble, no commentary."""


def build_provider_user_prompt(pool: Dict[str, Any],
                               name: Optional[str] = None) -> str:
    who = f" for {name}" if name else ""
    domains = pool.get("substantive_domains") or []
    return (
        f"ATOMS{who} — the complete set of statements available. Nothing else exists:\n"
        + json.dumps(pool["atoms"], indent=1)
        + "\n\nCONNECTOR IDS:\n"
        + json.dumps(sorted(CONNECTORS), indent=1)
        # D9-004-LIVE-CORR-01 · state the requirement in the payload as well as
        # the instruction. The validator enforced a three-domain spread that the
        # prompt never mentioned, so a perfectly reasonable composition was
        # rejected and the reader got "the closing reflection is not available".
        # The validator was right and the prompt was incomplete.
        + f"\n\nREQUIRED SUBSTANTIVE DOMAINS: {json.dumps(domains)}\n"
        + (f"All {len(domains)} are required — one atom from each, minimum.\n"
           if len(domains) <= MIN_SUBSTANTIVE_DOMAINS
           else f"At least {MIN_SUBSTANTIVE_DOMAINS} distinct ones are required.\n")
        + f"\nReturn the JSON object with the single {COMPOSITION_KEY!r} key."
    )
