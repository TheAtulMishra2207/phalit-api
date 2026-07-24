"""
karak_contract.py — Karakamsha narrative contract. Deliverable 2.

Save to E:\\phalit.ai\\karak_contract.py and upload to the repo root alongside
main.py. Flat layout, no package.

What this module owns:
  1. Strict request schema. `chart_brief` is no longer Dict[str, Any].
  2. Atoms-only prompt construction. Every string that can reach the prompt is
     validated: plain_meaning, action_seed, and nothing else. The user's name is
     not sent at all.

WHAT THIS DOES NOT DO, stated plainly because an earlier version of this file
overclaimed and QA was right to call it out:

  - It blocks KNOWN prohibited vocabulary and KNOWN overreach patterns. It does
    not prove that every clause the model writes is entailed by an atom. A
    plainly-worded sentence with no atom behind it will pass.
  - It does not enforce the sentence-count instruction.
  - It does not verify that the atoms came from the Phalit engine. Anything
    shaped like an atom and free of prohibited vocabulary is accepted as an
    established finding. That is a trust-boundary question, not a contract one,
    and it needs an architecture decision rather than another validator.
  3. stop_reason validation. A truncated report is never returned as finished.
  4. Terminology validator (KAR-053) with one bounded retry.
  5. Overreach validator. Superlatives, lifetime claims, literalness assertions
     and time horizons not present in the input are rejected. (KAR-001, KAR-005,
     KAR-049.)
  6. Section-tagged output so the basis manifest can be paired per section.

Deliberately NOT here: the interpretation corpus (KAR-015), remedy protocols
(KAR-020/021), practice guidance (KAR-025), dasha boundaries (KAR-034). Those
are engine and corpus work, not contract work.

Version compatibility: no pydantic validators are used, so this runs unchanged
on pydantic v1 and v2. Validation is explicit Python and therefore testable
without a running app.
"""

import re
import requests
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import HTTPException

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1800
TARGET_SECTIONS = ["desire", "mastery", "path"]
SECTION_TITLES = {
    "desire":  "What the soul came for",
    "mastery": "What it carries",
    "path":    "Where it is going",
}

# ═════════════════════════════════════════════════════════════════════════════
# 1. Controlled prohibited-term dictionaries (KAR-053)
# ═════════════════════════════════════════════════════════════════════════════
# Rule 2 of the system prompt forbids technical vocabulary. Until now nothing
# enforced it, and the model emitted "Where your Karakamsha energy lands".
# These lists are the enforcement. They are deliberately broad: the atoms
# contain none of these words, so a compliant response cannot trip them, and a
# false positive costs one cheap retry rather than shipping a contract breach.

_SANSKRIT_TECHNICAL = [
    "karakamsha", "karakansha", "atmakaraka", "amatyakaraka", "charakaraka",
    "swamsa", "swansha", "navamsha", "navamsa", "rashi", "raashi", "kundali",
    "kundli", "jyotisha", "jyotish", "lagna", "ascendant", "kendra", "trikona",
    "upachaya", "dusthana", "moolatrikona", "mulatrikona", "swakshetra",
    "graha", "grahas", "bhava", "nakshatra", "pada", "drishti", "varga",
    "amsha", "amsa", "dasha", "dasa", "mahadasha", "antardasha", "bhukti",
    "vimshottari", "gochara", "parashari", "parasari", "jaimini", "bphs",
    "ishta devata", "ishta", "devata", "yoga", "karaka", "ayanamsha",
    "vakri", "neecha", "uccha", "shastra", "sutra", "moksha", "sampradaya",
    "japa", "nama-japa", "tapas", "mantra", "puja", "pooja", "homa",
]

_GRAHA = [
    "sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn",
    "rahu", "ketu", "surya", "chandra", "mangala", "kuja", "budha",
    "brihaspati", "guru", "shukra", "shani", "sani",
]

_SIGN = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
    "mesha", "vrishabha", "mithuna", "karka", "simha", "kanya", "tula",
    "vrischika", "dhanu", "makara", "kumbha", "meena",
]

_DIGNITY = [
    "exalted", "exaltation", "debilitated", "debilitation", "own sign",
    "friendly sign", "enemy sign", "mitra rashi", "shatru rashi",
    "sama rashi", "dignity",
]

# Deity names. The engine resolves these and the UI card displays them. The
# narrative receives only the plain archetype and must not name them.
_DEITY = [
    "shiva", "gauri", "skanda", "vishnu", "sambasiva", "lakshmi", "narayana",
    "durga", "ganapati", "ganesha", "agni", "varuna", "subrahmanya", "indra",
    "sachi", "brahma", "kala", "chitragupta", "rama", "krishna", "narasimha",
    "buddha", "vamana", "parashurama", "kurma", "varaha", "matsya",
]

_TERM_PATTERNS = [
    (re.compile(r"\b(" + "|".join(map(re.escape, _SANSKRIT_TECHNICAL)) + r")\b", re.I), "sanskrit_technical"),
    (re.compile(r"\b(" + "|".join(map(re.escape, _GRAHA)) + r")\b", re.I), "graha_name"),
    (re.compile(r"\b(" + "|".join(map(re.escape, _SIGN)) + r")\b", re.I), "sign_name"),
    (re.compile(r"\b(" + "|".join(map(re.escape, _DIGNITY)) + r")\b", re.I), "dignity_label"),
    (re.compile(r"\b(" + "|".join(map(re.escape, _DEITY)) + r")\b", re.I), "deity_name"),
    # house-number patterns
    (re.compile(r"\bhouse\s+of\b", re.I), "house_reference"),
    (re.compile(r"\bhouse\s+\d{1,2}\b", re.I), "house_reference"),
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+house\b", re.I), "house_reference"),
    (re.compile(r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|"
                r"ninth|tenth|eleventh|twelfth)\s+house\b", re.I), "house_reference"),
    (re.compile(r"\bH\d{1,2}\b"), "house_reference"),
    # chart mechanics named generically. "The planets governing your speech are
    # well-placed" carried no proper noun and slipped through the first draft.
    (re.compile(r"\bplanet(?:s|ary)?\b", re.I), "graha_name"),
    (re.compile(r"\bluminar(?:y|ies)\b", re.I), "graha_name"),
    (re.compile(r"\bconjunct(?:ion|ed)?\b", re.I), "graha_name"),
    (re.compile(r"\bretrograde\b", re.I), "graha_name"),
    (re.compile(r"\b(?:well|ill|poorly|badly)[\s-]placed\b", re.I), "dignity_label"),
    (re.compile(r"\bstrongly placed\b", re.I), "dignity_label"),
    (re.compile(r"\bchart\b", re.I), "divisional_chart"),
    # divisional chart terms
    (re.compile(r"\bD-?\d{1,2}\b"), "divisional_chart"),
    (re.compile(r"\bdivisional\s+chart\b", re.I), "divisional_chart"),
    (re.compile(r"\bbirth\s+chart\b", re.I), "divisional_chart"),
]

# ═════════════════════════════════════════════════════════════════════════════
# 2. Overreach dictionary (KAR-001 narrative half, KAR-005, KAR-049)
# ═════════════════════════════════════════════════════════════════════════════
# The deterministic layer is now bounded. These patterns are how the prose
# renderer was undoing that bound. "This is not metaphor" is the worst of them:
# it strips the interpretive qualification and asserts the reading as fact.

_OVERREACH_PATTERNS = [
    (re.compile(r"\bnot (?:a )?metaphor\b", re.I), "literalness_assertion"),
    (re.compile(r"\bliterally\b", re.I), "literalness_assertion"),
    (re.compile(r"\bthis is real\b", re.I), "literalness_assertion"),
    (re.compile(r"\b(?:past|previous|prior) lives?\b", re.I), "past_life_claim"),
    (re.compile(r"\blifetimes?\b", re.I), "past_life_claim"),
    (re.compile(r"\breincarnat", re.I), "past_life_claim"),
    (re.compile(r"\b(?:most|more) (?:powerful|potent|significant|important)\b", re.I), "superlative"),
    (re.compile(r"\bexceptional(?:ly)?\b", re.I), "superlative"),
    (re.compile(r"\bextraordinar(?:y|ily)\b", re.I), "superlative"),
    (re.compile(r"\brar(?:e|est|ely seen)\b", re.I), "superlative"),
    (re.compile(r"\bfull power\b", re.I), "superlative"),
    (re.compile(r"\bmagnetic(?:ally)?\b", re.I), "superlative"),
    (re.compile(r"\bnear-?certain\b", re.I), "certainty_claim"),
    (re.compile(r"\bguarantee(?:d|s)?\b", re.I), "certainty_claim"),
    (re.compile(r"\bwill definitely\b", re.I), "certainty_claim"),
    (re.compile(r"\bis assured\b", re.I), "certainty_claim"),
    (re.compile(r"\bdecades?\b", re.I), "time_horizon"),
    (re.compile(r"\byears? (?:ahead|to come)\b", re.I), "time_horizon"),
    (re.compile(r"\b(?:rest|remainder) of your life\b", re.I), "time_horizon"),
    (re.compile(r"\bfor the next \w+ years?\b", re.I), "time_horizon"),
    (re.compile(r"\b(?:have|has) earned\b", re.I), "proven_claim"),
    # Theological assertion. The atoms contain no devotional content, so any
    # of this is the model supplying its own. "Your soul reaches its highest
    # expression not in a temple" and "all-pervading grace" were both this.
    (re.compile(r"\b(?:temple|shrine|altar|worship|ritual|prayer|deity|deities|"
                r"divine|sacred|holy|blessed|blessing|grace|salvation|liberation|"
                r"enlightenment|awakening|devotion|devotional|karmic)\b", re.I), "theological_assertion"),
    (re.compile(r"\bhighest (?:expression|form|purpose|calling)\b", re.I), "superlative"),
    (re.compile(r"\bdeepest (?:ache|longing|need|truth)\b", re.I), "superlative"),
    (re.compile(r"\bproven\b", re.I), "proven_claim"),
]


def find_violations(text: str) -> List[Dict[str, str]]:
    """Return every prohibited-term and overreach hit in `text`.

    Pure function. No I/O, no model call. Contract tests call it directly.
    """
    out: List[Dict[str, str]] = []
    seen = set()
    for pattern, kind in _TERM_PATTERNS + _OVERREACH_PATTERNS:
        for m in pattern.finditer(text or ""):
            key = (kind, m.group(0).lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": kind, "term": m.group(0)})
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 3. Strict request schema
# ═════════════════════════════════════════════════════════════════════════════

class KarakAtomIn(BaseModel):
    """Wire shape of one interpretive atom. Typed so OpenAPI advertises the
    real contract and FastAPI rejects malformed payloads at binding time.
    No aliases and no validators, so this behaves identically on pydantic
    v1 and v2. Semantic checks still happen in validate_brief."""
    id: str
    section: str
    plain_meaning: str
    polarity: str
    action_seed: Optional[str] = None
    timing: bool = False
    confidence: Optional[str] = None


class KarakBriefIn(BaseModel):
    schema_version: Optional[str] = None
    interpretations: List[KarakAtomIn] = []
    sections: Optional[List[str]] = None


class KarakInterpretation(BaseModel):
    id: str
    section: str
    plain_meaning: str
    polarity: str
    action_seed: Optional[str] = None
    timing: bool = False
    confidence: str = "direct"


class KarakBrief(BaseModel):
    schema_version: str = "karakamsha.v2"
    interpretations: List[KarakInterpretation] = []
    sections: List[str] = []


class KarakReportRequest(BaseModel):
    name: str
    chart_brief: KarakBriefIn


_ALLOWED_POLARITY = {"support", "caution", "neutral"}
_ALLOWED_CONFIDENCE = {"direct", "derived", "ambiguous", "requires_confirmation"}
MAX_SEED_CHARS = 200
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MAX_ATOMS = 40
MAX_ATOM_CHARS = 400


def _as_dict(obj: Any) -> Dict[str, Any]:
    """Accept either the typed envelope or a plain dict, so validate_brief is
    callable directly from tests without constructing pydantic models."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return {}


def _validate_action_seed(seed: Any, index: int, atom_id: str) -> Optional[str]:
    """KAR-054. action_seed was accepted unchecked and interpolated verbatim
    into the prompt, which made the module's own "no code path can send
    technical material" claim false. It now passes the same gate as
    plain_meaning, plus type, length and control-character checks.
    """
    if seed is None:
        return None
    if not isinstance(seed, str):
        raise HTTPException(
            status_code=422,
            detail=f"interpretations[{index}] ({atom_id}).action_seed must be a string or null, "
                   f"got {type(seed).__name__}.",
        )
    seed = seed.strip()
    if not seed:
        return None
    if len(seed) > MAX_SEED_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"interpretations[{index}] ({atom_id}).action_seed exceeds {MAX_SEED_CHARS} characters.",
        )
    if "\n" in seed or "\r" in seed or _CONTROL_CHARS.search(seed):
        raise HTTPException(
            status_code=422,
            detail=f"interpretations[{index}] ({atom_id}).action_seed must be a single line "
                   f"with no control characters.",
        )
    leaks = find_violations(seed)
    if leaks:
        raise HTTPException(
            status_code=422,
            detail=f"interpretations[{index}] ({atom_id}).action_seed contains disallowed "
                   f"vocabulary: {', '.join(v['term'] for v in leaks[:6])}",
        )
    return seed


def validate_brief(raw: Any) -> KarakBrief:
    """Reject anything that is not a well-formed atom payload.

    Every string that can reach the prompt is validated here. There is exactly
    one string interpolated into the prompt that does not originate in an atom,
    and that is the fixed English of build_user_prompt itself.
    """
    raw = _as_dict(raw)
    if not raw:
        raise HTTPException(status_code=422, detail="chart_brief must be an object.")

    schema = raw.get("schema_version") or raw.get("schema") or ""
    if not str(schema).startswith("karakamsha.v2"):
        raise HTTPException(
            status_code=422,
            detail="chart_brief schema_version must be karakamsha.v2. Received: "
                   f"{schema or 'none'}. The frontend engine must be v2.3.0 or later.",
        )

    atoms_raw = raw.get("interpretations")
    if not isinstance(atoms_raw, list) or not atoms_raw:
        raise HTTPException(
            status_code=422,
            detail="chart_brief.interpretations must be a non-empty list of interpretive atoms.",
        )
    if len(atoms_raw) > MAX_ATOMS:
        raise HTTPException(
            status_code=422,
            detail=f"chart_brief.interpretations exceeds {MAX_ATOMS} atoms.",
        )

    atoms: List[KarakInterpretation] = []
    for i, a in enumerate(atoms_raw):
        a = _as_dict(a)
        if not a:
            raise HTTPException(status_code=422, detail=f"interpretations[{i}] must be an object.")
        aid = a.get("id")
        section = a.get("section")
        plain = a.get("plain_meaning")
        polarity = a.get("polarity")
        confidence = a.get("confidence") or "direct"
        if not aid or not isinstance(aid, str):
            raise HTTPException(status_code=422, detail=f"interpretations[{i}].id missing.")
        if section not in TARGET_SECTIONS:
            raise HTTPException(
                status_code=422,
                detail=f"interpretations[{i}].section must be one of {TARGET_SECTIONS}, got {section!r}.",
            )
        if not plain or not isinstance(plain, str) or not plain.strip():
            raise HTTPException(status_code=422, detail=f"interpretations[{i}].plain_meaning is empty.")
        if len(plain) > MAX_ATOM_CHARS:
            raise HTTPException(
                status_code=422,
                detail=f"interpretations[{i}].plain_meaning exceeds {MAX_ATOM_CHARS} characters.",
            )
        if polarity not in _ALLOWED_POLARITY:
            raise HTTPException(
                status_code=422,
                detail=f"interpretations[{i}].polarity must be one of {sorted(_ALLOWED_POLARITY)}.",
            )
        if confidence not in _ALLOWED_CONFIDENCE:
            raise HTTPException(
                status_code=422,
                detail=f"interpretations[{i}].confidence must be one of {sorted(_ALLOWED_CONFIDENCE)}.",
            )
        # An atom carrying jargon would defeat the whole architecture, so the
        # INPUT is validated with the same dictionaries as the output.
        leaks = [v for v in find_violations(plain) if v["kind"] != "past_life_claim"]
        if leaks:
            raise HTTPException(
                status_code=422,
                detail=f"interpretations[{i}] ({aid}) contains technical vocabulary that must not "
                       f"reach the model: {', '.join(v['term'] for v in leaks[:6])}",
            )
        seed = _validate_action_seed(a.get("action_seed"), i, aid)
        atoms.append(KarakInterpretation(
            id=aid, section=section, plain_meaning=plain.strip(),
            polarity=polarity, action_seed=seed,
            timing=bool(a.get("timing", False)), confidence=confidence,
        ))

    # KAR-056. The system prompt demands exactly three sections, so the input
    # must supply all three. The client-supplied `sections` array is ignored
    # entirely; presence is derived from the atoms themselves.
    present = sorted({x.section for x in atoms})
    missing = [s for s in TARGET_SECTIONS if s not in present]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="chart_brief.interpretations must cover all three sections. "
                   f"Missing: {', '.join(missing)}.",
        )

    return KarakBrief(schema_version="karakamsha.v2", interpretations=atoms,
                      sections=list(TARGET_SECTIONS))


# ═════════════════════════════════════════════════════════════════════════════
# 4. Prompt construction — atoms only
# ═════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the prose layer of a Jyotisha analysis system. The astrological work is already complete. It was done deterministically before you were called, and you cannot see it.

You receive interpretive statements that have already been derived from the chart. Your only job is to render them as connected, readable prose for the person they describe.

ABSOLUTE RULES

1. You may only express what the supplied statements say. You may join them, order them within their section, and find the thread between them. You may not add a finding that is not in them. If the statements do not mention a life domain, a relationship, a career, a health matter or a spiritual practice, you do not mention it either.

2. Use no technical vocabulary of any kind. No planet names. No sign names. No house numbers or house references. No chart names. No deity names. No Sanskrit terms. Not one. The reader has the technical detail elsewhere on the page; your section is the plain-language reading and nothing else.

3. Claim nothing about past lives, previous incarnations, or accumulated lifetimes. Where a statement speaks of something inherited or carried, render it as a disposition the person already has, not as a history you are asserting.

4. Never assert that a reading is literal, real, or not a metaphor. You are describing a symbolic system. Do not editorialise about its status.

5. No superlatives about the chart. Nothing is exceptional, rare, most powerful, extraordinary, or operating at full power. You have no comparison set. You are reading one chart with no access to any other.

6. Where a timing statement is supplied, say exactly what it says and stop. Do not extend it to a longer horizon than it names, do not rank it, and do not derive tactical instructions from it. If no timing statement is supplied, write nothing about timing at all.

7. Second person throughout. Direct, adult, unsentimental. No flattery, no reassurance, no motivational register, no rhetorical questions. Do not open with a summary of what you are about to say.

8. No bullet points, no headings inside a section, no lists. Connected prose.

OUTPUT FORMAT

Exactly three sections, each preceded by its marker alone on a line:

[[desire]]
[[mastery]]
[[path]]

Four to five sentences per section. If a section has few supplied statements, write fewer sentences rather than padding. Emit nothing before the first marker and nothing after the third section."""


def build_user_prompt(brief: KarakBrief) -> str:
    """Build the model input from atoms alone.

    KAR-055. The user's name used to be interpolated here. It was an
    uncontrolled channel: a name of "Mars" injected technical vocabulary, and a
    multi-line name injected a new instruction. The report is written in the
    second person and never needed the name, so it is not sent at all. This is
    a removal rather than a sanitisation, because there is nothing to sanitise
    for. The name still appears in the UI, which does not go through a model.
    """
    lines = [
        "Write the three sections for this person.",
        "",
        "These are the findings. Every one of them is already established. "
        "Render them; do not extend them.",
        "",
    ]
    for sec in TARGET_SECTIONS:
        atoms = [a for a in brief.interpretations if a.section == sec]
        if not atoms:
            continue
        lines.append(f"[[{sec}]] — {SECTION_TITLES[sec]}")
        for a in atoms:
            tag = {"support": "(supporting)", "caution": "(requires attention)",
                   "neutral": "(descriptive)"}[a.polarity]
            lines.append(f"  - {a.plain_meaning} {tag}")
            # KAR-059. Evidentiary uncertainty is not the same as caution
            # polarity. An atom the engine could not confirm must be hedged in
            # the prose, not stated as established.
            if a.confidence == "requires_confirmation":
                lines.append("    this one is a single indication only: hedge it, "
                             "write it as something suggested rather than established")
            if a.action_seed:
                lines.append(f"    practical thread: {a.action_seed}")
        lines.append("")
    if not any(a.timing for a in brief.interpretations):
        lines.append("No timing finding was supplied. Write nothing about timing, "
                     "seasons, windows or what to do now versus later.")
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# 5. Response parsing and completion handling
# ═════════════════════════════════════════════════════════════════════════════

_MARKER = re.compile(r"^\s*\[\[(desire|mastery|path)\]\]\s*$", re.M)


def parse_sections(text: str) -> Dict[str, str]:
    parts: Dict[str, str] = {}
    marks = list(_MARKER.finditer(text or ""))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end].strip()
        if body:
            parts[m.group(1)] = body
    return parts


def _call_model(api_key: str, system: str, user: str) -> Dict[str, Any]:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": MAX_TOKENS, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=60,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream model error {response.status_code}.",
        )
    data = response.json()
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    return {"text": text, "stop_reason": data.get("stop_reason")}


def generate(name: str, raw_brief: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """Validate, render, validate again, retry once, or fail loudly."""
    brief = validate_brief(raw_brief)
    # `name` is accepted for signature stability with main.py and is
    # deliberately not forwarded to the model. See build_user_prompt.
    user = build_user_prompt(brief)

    attempts: List[Dict[str, Any]] = []
    system = SYSTEM_PROMPT

    for attempt in (1, 2):
        result = _call_model(api_key, system, user)
        stop = result["stop_reason"]

        # Truncation is never returned as a finished report.
        if stop == "max_tokens":
            attempts.append({"attempt": attempt, "failure": "max_tokens"})
            raise HTTPException(
                status_code=502,
                detail="The report exceeded its length ceiling and was cut off. "
                       "Nothing partial is returned.",
            )
        if stop != "end_turn":
            attempts.append({"attempt": attempt, "failure": f"stop_reason={stop}"})
            raise HTTPException(
                status_code=502,
                detail=f"The report did not complete normally (stop_reason={stop}).",
            )

        sections = parse_sections(result["text"])
        # KAR-056. All three markers are required regardless of what the client
        # sent. Output completeness is not derived from the request.
        missing = [s for s in TARGET_SECTIONS if s not in sections]
        violations = find_violations(result["text"])

        if not missing and not violations:
            # `report` is built in the "### Title" shape that the existing
            # frontend _renderReportSections() parses, with the [[markers]]
            # stripped. No frontend change is required to display this.
            report = "\n\n".join(
                f"### {SECTION_TITLES[s]}\n{sections[s]}" for s in TARGET_SECTIONS
            )
            return {
                "report": report,
                "sections": [
                    {
                        "id": s,
                        "title": SECTION_TITLES[s],
                        "text": sections[s],
                        "atom_ids": [a.id for a in brief.interpretations if a.section == s],
                    }
                    for s in TARGET_SECTIONS
                ],
                "complete": True,
                "stop_reason": stop,
                "attempts": attempt,
                "validation": {"violations": [], "missing_sections": []},
            }

        attempts.append({
            "attempt": attempt,
            "violations": violations,
            "missing_sections": missing,
        })

        if attempt == 2:
            break

        # Bounded retry: the violations are named back to the model once.
        notes = []
        if violations:
            notes.append(
                "Your previous response used forbidden vocabulary: "
                + ", ".join(sorted({v["term"] for v in violations}))
                + ". Rewrite so that none of these words or anything like them appears. "
                  "Rule 2 and rules 3 to 6 are absolute."
            )
        if missing:
            notes.append(
                "Your previous response was missing these section markers: "
                + ", ".join("[[" + m + "]]" for m in missing)
                + ". Emit every marker on its own line."
            )
        system = SYSTEM_PROMPT + "\n\nCORRECTION\n" + "\n".join(notes)

    # detail stays a plain string: the existing frontend error handler does
    # `new Error(data.detail)`, and a dict would surface as "[object Object]".
    # The structured form goes to the server log where it is actually useful.
    last = attempts[-1]
    terms = sorted({v["term"] for v in last.get("violations", [])})
    missing = last.get("missing_sections", [])
    print("[karakreport] contract failure after 2 attempts: "
          f"violations={last.get('violations', [])} missing_sections={missing}",
          flush=True)
    bits = ["The report did not meet its content contract and was not returned."]
    if terms:
        bits.append("Disallowed terms: " + ", ".join(terms[:8]) + ".")
    if missing:
        bits.append("Missing sections: " + ", ".join(missing) + ".")
    raise HTTPException(status_code=422, detail=" ".join(bits))
