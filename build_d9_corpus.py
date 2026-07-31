"""Build the D9 corpus tables from D9-corpus-FINAL.xlsx.

TWO EXTRACTOR TRAPS ARE DESIGNED AGAINST HERE, both found the hard way:

  1. Sheet "3 Vargottama" carries a FOOTNOTE in column A below a blank row. A
     first-column-non-empty parse ingests it as a 92nd entry with empty prose.
  2. row_id UNDERSCORES the space in "Own Sign" (RASHI-Sun-Own_Sign) while the
     dignity_label column does not. Building a lookup by joining
     RASHI-{graha}-{dignity_label} SILENTLY drops tier 2 for all nine grahas.

So the tables are keyed off the AUTHORITATIVE graha and dignity_label COLUMNS,
never off row_id, and completeness is asserted rather than hoped for.
"""
import json, sys, openpyxl

GRAHAS = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
TIERS  = ["Exalted","Moolatrikona","Own Sign","Friend","Neutral","Enemy","Debilitated"]
DIRECTIONS = ["stronger","held","weaker"]

def build(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    dig, shift, varg = {}, {}, None

    for r in wb["1 Dignity"].iter_rows(min_row=2, values_only=True):
        graha, label, prose = r[1], r[3], r[5]
        if not graha or not label:          # blank row or footnote
            continue
        dig.setdefault(str(graha), {})[str(label)] = str(prose)

    for r in wb["2 Shift"].iter_rows(min_row=2, values_only=True):
        graha, direction, prose = r[1], r[2], r[4]
        if not graha or not direction:
            continue
        shift.setdefault(str(graha), {})[str(direction)] = str(prose)

    for r in wb["3 Vargottama"].iter_rows(min_row=2, values_only=True):
        if r[0] == "VARGOTTAMA":
            varg = str(r[2])

    problems = []
    for g in GRAHAS:
        for t in TIERS:
            if t not in dig.get(g, {}):
                problems.append(f"dignity missing {g}/{t}")
        for d in DIRECTIONS:
            if d not in shift.get(g, {}):
                problems.append(f"shift missing {g}/{d}")
    extra_g = sorted(set(dig) - set(GRAHAS)) + sorted(set(shift) - set(GRAHAS))
    if extra_g: problems.append(f"unexpected grahas: {extra_g}")
    for g, m in dig.items():
        for t in m:
            if t not in TIERS: problems.append(f"unexpected tier {g}/{t}")
    if varg is None: problems.append("vargottama row absent")
    for g, m in dig.items():
        for t, p in m.items():
            if "{sign}" not in p: problems.append(f"dignity {g}/{t} has no {{sign}}")
    if problems:
        raise SystemExit("CORPUS BUILD REFUSED:\n  " + "\n  ".join(problems))

    n = sum(len(v) for v in dig.values()) + sum(len(v) for v in shift.values()) + 1
    return dig, shift, varg, n

if __name__ == "__main__":
    dig, shift, varg, n = build(sys.argv[1])
    print("dignity %d x %d, shift %d x %d, vargottama 1, total %d"
          % (len(dig), len(TIERS), len(shift), len(DIRECTIONS), n))
    js = []
    js.append("// D9 corpus, generated from D9-corpus-FINAL.xlsx by build_d9_corpus.py.")
    js.append("// Keyed off the graha and dignity_label COLUMNS, never off row_id: the")
    js.append("// row_id underscores the space in 'Own Sign', so a join-built key drops")
    js.append("// tier 2 for all nine grahas, silently.")
    js.append("const D9_RASHI_CORPUS = Object.freeze(%s);"
              % json.dumps(dig, ensure_ascii=False, indent=2, sort_keys=True))
    js.append("const VARGA_SHIFT_CORPUS = Object.freeze(%s);"
              % json.dumps(shift, ensure_ascii=False, indent=2, sort_keys=True))
    js.append("const VARGOTTAMA_NOTE = %s;" % json.dumps(varg, ensure_ascii=False))
    js.append("")
    js.append("// Runtime completeness guard. A silently short table is the defect this")
    js.append("// whole ticket exists to stop, so absence fails loudly at load.")
    js.append("(function d9CorpusGuard(){")
    js.append("  const G=%s;" % json.dumps(GRAHAS))
    js.append("  const T=%s;" % json.dumps(TIERS))
    js.append("  const D=%s;" % json.dumps(DIRECTIONS))
    js.append("  const miss=[];")
    js.append("  G.forEach(g=>{T.forEach(t=>{if(!(D9_RASHI_CORPUS[g]||{})[t])miss.push('D9_RASHI_CORPUS.'+g+'.'+t);});")
    js.append("               D.forEach(d=>{if(!(VARGA_SHIFT_CORPUS[g]||{})[d])miss.push('VARGA_SHIFT_CORPUS.'+g+'.'+d);});});")
    js.append("  if(!VARGOTTAMA_NOTE)miss.push('VARGOTTAMA_NOTE');")
    js.append("  if(miss.length)throw new Error('D9 corpus incomplete: '+miss.join(', '));")
    js.append("})();")
    open("d9_corpus_block.js","w").write("\n".join(js) + "\n")
    print("wrote d9_corpus_block.js")
