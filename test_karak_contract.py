"""
test_karak_contract.py — Deliverable 2 contract tests.

Save to E:\\phalit.ai\\test_karak_contract.py and upload to the repo root.

Runs two ways:
    python test_karak_contract.py      # no pytest needed
    pytest test_karak_contract.py -q

No network. The model call is stubbed, so this suite is safe to run in CI and
costs nothing. Every assertion here is about the contract, not the astrology.
"""

import sys
import karak_contract as kc
from fastapi import HTTPException

# ── fixtures ────────────────────────────────────────────────────────────────

VALID_ATOMS = [
    {"id": "AK_IDENTITY", "section": "desire", "polarity": "neutral",
     "plain_meaning": "What you came here to master is not what you are already good at.",
     "action_seed": "Name the one pursuit you have restarted more than twice."},
    {"id": "KA_SIGN_CORE", "section": "desire", "polarity": "neutral",
     "plain_meaning": "You draw steadiness from tending living things that grow on their own schedule."},
    {"id": "AK_CONJ_NONE", "section": "mastery", "polarity": "neutral",
     "plain_meaning": "No second influence is blended into your core drive."},
    {"id": "MOKSHA_GATE", "section": "path", "polarity": "neutral",
     "plain_meaning": "Nothing here is handed to you and nothing here obstructs you."},
]

VALID_BRIEF = {"schema": "karakamsha.v2", "interpretations": VALID_ATOMS,
               "sections": ["desire", "mastery", "path"]}

# The payload the frontend used to send before the atom architecture existed.
LEGACY_BRIEF = {
    "atmakaraka": "Mars", "ak_degree": "24.40", "ak_d1_sign": "Libra",
    "karakamsha_sign": "Taurus", "soul_fulfillment": "Indirect",
    "ka_core": "Happiness through four-legged animals.",
    "kl_house_summary": {"H1": {"lord": "Venus", "occupants": ["Rahu"]}},
    "ishta_devata": "Vishnu", "moksha_status": "Reached Through Practice",
}

GOOD_RESPONSE = """[[desire]]
What you came here to master is not the thing you are already good at, and that gap is the point. You draw steadiness from tending things that grow on their own schedule rather than yours. The work will not move faster because you want it to.

[[mastery]]
No second influence is blended into your core drive, so it expresses plainly. That is not the same as being alone in it.

[[path]]
Nothing is handed to you here and nothing obstructs you either. What you build is what you get."""

_calls = []


def _stub(text, stop_reason="end_turn"):
    def fake(api_key, system, user):
        _calls.append({"system": system, "user": user})
        t = text(len(_calls)) if callable(text) else text
        return {"text": t, "stop_reason": stop_reason}
    return fake


def _reset():
    _calls.clear()


# ── 1. schema strictness ────────────────────────────────────────────────────

def test_legacy_payload_is_rejected():
    """The old raw-astrology brief must not be accepted at all."""
    try:
        kc.validate_brief(LEGACY_BRIEF)
    except HTTPException as e:
        assert e.status_code == 422
        assert "karakamsha.v2" in str(e.detail)
        return
    raise AssertionError("legacy brief was accepted")


def test_untyped_dict_is_rejected():
    for bad in [None, [], "brief", 7]:
        try:
            kc.validate_brief(bad)
            raise AssertionError(f"accepted {bad!r}")
        except HTTPException as e:
            assert e.status_code == 422


def test_empty_interpretations_rejected():
    try:
        kc.validate_brief({"schema": "karakamsha.v2", "interpretations": []})
        raise AssertionError("accepted empty atom list")
    except HTTPException as e:
        assert e.status_code == 422


def test_bad_section_and_polarity_rejected():
    for mutate, word in [
        (lambda a: a.update(section="career"), "section"),
        (lambda a: a.update(polarity="very good"), "polarity"),
        (lambda a: a.update(plain_meaning=""), "plain_meaning"),
        (lambda a: a.pop("id"), "id"),
    ]:
        atoms = [dict(VALID_ATOMS[0])]
        mutate(atoms[0])
        try:
            kc.validate_brief({"schema": "karakamsha.v2", "interpretations": atoms})
            raise AssertionError(f"accepted bad {word}")
        except HTTPException as e:
            assert e.status_code == 422 and word in str(e.detail)


def test_jargon_in_an_atom_is_rejected_at_the_door():
    """An atom carrying technical vocabulary would defeat the architecture."""
    for leak in ["Your Atmakaraka is strong.",
                 "Mars gives you drive.",
                 "The 3rd house is activated.",
                 "Venus is exalted here.",
                 "Your Navamsha shows this."]:
        atoms = [dict(VALID_ATOMS[0], plain_meaning=leak)]
        try:
            kc.validate_brief({"schema": "karakamsha.v2", "interpretations": atoms})
            raise AssertionError(f"accepted atom containing: {leak}")
        except HTTPException as e:
            assert e.status_code == 422


def test_atom_count_and_length_bounded():
    big = [dict(VALID_ATOMS[0], id=f"A{i}") for i in range(kc.MAX_ATOMS + 1)]
    try:
        kc.validate_brief({"schema": "karakamsha.v2", "interpretations": big})
        raise AssertionError("accepted oversized atom list")
    except HTTPException as e:
        assert e.status_code == 422

    long_atom = [dict(VALID_ATOMS[0], plain_meaning="a " * (kc.MAX_ATOM_CHARS))]
    try:
        kc.validate_brief({"schema": "karakamsha.v2", "interpretations": long_atom})
        raise AssertionError("accepted oversized atom")
    except HTTPException as e:
        assert e.status_code == 422


# ── 2. the central claim: nothing unsupported can reach the model ───────────

def test_prompt_contains_no_technical_vocabulary():
    """This is the test the whole deliverable exists for."""
    brief = kc.validate_brief(VALID_BRIEF)
    prompt = kc.build_user_prompt("Atul", brief)
    violations = kc.find_violations(prompt)
    assert not violations, f"prompt leaked: {violations}"


def test_prompt_contains_no_legacy_field_even_if_sent():
    """Legacy keys alongside valid atoms are dropped, not forwarded."""
    mixed = dict(VALID_BRIEF)
    mixed.update(LEGACY_BRIEF)
    mixed["schema"] = "karakamsha.v2"
    mixed["interpretations"] = VALID_ATOMS
    brief = kc.validate_brief(mixed)
    prompt = kc.build_user_prompt("Atul", brief)
    for legacy_value in ["Mars", "Libra", "Taurus", "Venus", "Rahu", "Vishnu",
                         "24.40", "four-legged", "H1"]:
        assert legacy_value not in prompt, f"legacy value {legacy_value!r} reached the prompt"


def test_prompt_contains_only_supplied_meanings():
    brief = kc.validate_brief(VALID_BRIEF)
    prompt = kc.build_user_prompt("Atul", brief)
    for a in VALID_ATOMS:
        assert a["plain_meaning"] in prompt
    assert prompt.count("- ") == len(VALID_ATOMS)


def test_absent_timing_is_stated_explicitly():
    brief = kc.validate_brief(VALID_BRIEF)
    prompt = kc.build_user_prompt("Atul", brief)
    assert "No timing finding was supplied" in prompt


# ── 3. output validator (KAR-053 and overreach) ─────────────────────────────

def test_validator_catches_the_reported_violations():
    """Every phrase QA quoted must be caught."""
    cases = [
        ("Where your Karakamsha energy lands in your birth chart", "sanskrit_technical"),
        ("it activates the house of communication", "house_reference"),
        ("The planets governing your speech are well-placed", "graha_name"),
        ("The planets governing your speech are well-placed", "dignity_label"),
        ("a striking concentration of energy in the house of deep resources", "house_reference"),
        ("the most powerful alignment your chart can offer", "divisional_chart"),
        ("Your soul reaches its highest expression not in a temple", "superlative"),
        ("You carry lifetimes of skill", "past_life_claim"),
        ("This is not metaphor.", "literalness_assertion"),
        ("one of the most powerful alignments your chart can offer", "superlative"),
        ("outward presence is magnetically strong", "superlative"),
        ("anchor the decades ahead", "time_horizon"),
        ("Your soul has earned real expertise", "proven_claim"),
        ("Mercury is exalted in Virgo", "graha_name"),
        ("Task completion is near-certain", "certainty_claim"),
    ]
    for text, expected_kind in cases:
        kinds = {v["kind"] for v in kc.find_violations(text)}
        assert expected_kind in kinds, f"{text!r} -> {kinds}, expected {expected_kind}"


def test_validator_passes_clean_prose():
    assert not kc.find_violations(GOOD_RESPONSE), kc.find_violations(GOOD_RESPONSE)


# ── 4. completion handling ──────────────────────────────────────────────────

def test_truncated_response_is_never_returned():
    _reset()
    kc._call_model = _stub(GOOD_RESPONSE, stop_reason="max_tokens")
    try:
        kc.generate("Atul", VALID_BRIEF, "key")
        raise AssertionError("truncated report was returned")
    except HTTPException as e:
        assert e.status_code == 502 and "cut off" in str(e.detail)


def test_missing_section_marker_fails():
    _reset()
    kc._call_model = _stub("[[desire]]\nOnly one section here.")
    try:
        kc.generate("Atul", VALID_BRIEF, "key")
        raise AssertionError("incomplete section set was returned")
    except HTTPException as e:
        assert e.status_code == 422
        assert "mastery" in str(e.detail) or "path" in str(e.detail)


def test_violating_response_retries_once_then_succeeds():
    _reset()
    dirty = GOOD_RESPONSE.replace("What you came here", "Your Karakamsha shows what you came here")
    kc._call_model = _stub(lambda n: dirty if n == 1 else GOOD_RESPONSE)
    out = kc.generate("Atul", VALID_BRIEF, "key")
    assert out["complete"] is True
    assert out["attempts"] == 2
    assert len(_calls) == 2
    assert "forbidden vocabulary" in _calls[1]["system"]
    assert "Karakamsha" in _calls[1]["system"]


def test_violating_response_twice_is_rejected():
    _reset()
    dirty = GOOD_RESPONSE.replace("What you came here", "Your Atmakaraka shows what you came here")
    kc._call_model = _stub(dirty)
    try:
        kc.generate("Atul", VALID_BRIEF, "key")
        raise AssertionError("a violating report was returned")
    except HTTPException as e:
        assert e.status_code == 422
        assert isinstance(e.detail, str), "detail must be a string for the frontend error handler"
        assert "Atmakaraka" in e.detail
    assert len(_calls) == 2


def test_success_shape_pairs_sections_to_atom_ids():
    _reset()
    kc._call_model = _stub(GOOD_RESPONSE)
    out = kc.generate("Atul", VALID_BRIEF, "key")
    assert out["complete"] is True and out["stop_reason"] == "end_turn"
    ids = {s["id"] for s in out["sections"]}
    assert ids == {"desire", "mastery", "path"}
    desire = next(s for s in out["sections"] if s["id"] == "desire")
    assert desire["atom_ids"] == ["AK_IDENTITY", "KA_SIGN_CORE"]
    assert all(s["text"] for s in out["sections"])


def test_report_field_is_frontend_renderable_and_marker_free():
    _reset()
    kc._call_model = _stub(GOOD_RESPONSE)
    out = kc.generate("Atul", VALID_BRIEF, "key")
    assert "[[" not in out["report"], "raw section markers leaked into report"
    assert out["report"].count("### ") == 3
    for title in kc.SECTION_TITLES.values():
        assert f"### {title}" in out["report"]
    assert not kc.find_violations(out["report"])


# ── runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    real = kc._call_model
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        kc._call_model = real
        try:
            fn()
            print(f"  pass  {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
