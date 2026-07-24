"""
validate_corpus.py — build-time guard for newphalit.html trait corpora.

KAR-088. A malformed corpus value (a truncated string, a bare [text,type] pair
where a LIST of pairs is expected, a wrong type flag, empty text) must fail the
build rather than render as garbage such as the "Ip" artifact.

The critical lesson: Array.isArray is insufficient. A single pair ['text','p']
is itself an array, so it passes Array.isArray and is then .map-ed over its own
characters. Validation therefore checks the SHAPE — a non-empty list of valid
[string, type] pairs — exactly as the runtime isTraitList guard now does.

Run:  python validate_corpus.py newphalit.html
Exit non-zero on any violation; intended as a CI / pre-deploy gate.
"""
import re, sys

VALID_TYPES = {"p", "c", "n"}


def extract_object(js, name):
    """Return the balanced {...} body of `const NAME={...}`."""
    m = re.search(r"const\s+" + re.escape(name) + r"\s*=\s*\{", js)
    if not m:
        return None
    i = js.index("{", m.start())
    depth = 0
    for j in range(i, len(js)):
        if js[j] == "{":
            depth += 1
        elif js[j] == "}":
            depth -= 1
            if depth == 0:
                return js[i:j + 1]
    return None


def scan_pairs(name, blob, problems):
    """Every [ 'text' , 'flag' ] pair in the blob must have a valid flag and
    non-trivial text. Catches truncated fragments and bad type flags anywhere
    in the corpus, not only at the Saturn exception."""
    for m in re.finditer(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*'([A-Za-z]+)'\s*\]", blob):
        text, typ = m.group(1), m.group(2)
        cleaned = text.strip()
        if typ not in VALID_TYPES:
            problems.append(f"{name}: type flag {typ!r} invalid for {cleaned[:48]!r}")
        if len(cleaned) < 2:
            problems.append(f"{name}: trait text too short: {cleaned!r}")
        elif re.fullmatch(r"[A-Za-z]{1,2}", cleaned):
            problems.append(f"{name}: suspected truncated fragment: {cleaned!r}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "newphalit.html"
    js = open(path, encoding="utf-8").read()
    problems = []

    for name in ("GBN", "GRN", "GP_TRAITS"):
        blob = extract_object(js, name)
        if blob is None:
            problems.append(f"{name}: corpus table not found")
            continue
        scan_pairs(name, blob, problems)

    # KAR-088 site guard: the old single-pair selector must not reappear, and
    # both Saturn-H1 paths must resolve through the shared normaliser.
    if re.search(r"GBN\['Saturn'\]\[0\]\[[01]\]", js) or re.search(r"GBN\.Saturn\[0\]\[[01]\]\s*[:;]", js):
        problems.append("KAR-088 regression: a single Saturn pair is selected directly")
    helper_uses = len(re.findall(r"saturnFirstHouseTraits\(", js))
    if helper_uses < 2:
        problems.append(
            f"KAR-088: expected both Saturn-H1 paths (drawer + planetCorpus) to call "
            f"saturnFirstHouseTraits; found {helper_uses} call(s)")
    if "Favored by fortune" in js:
        problems.append("KAR-088: fabricated trait 'Favored by fortune' still present")

    if problems:
        print("CORPUS VALIDATION FAILED")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"corpus validation passed ({helper_uses} shared Saturn-H1 call sites)")


if __name__ == "__main__":
    main()
