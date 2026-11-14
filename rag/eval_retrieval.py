import json
import sys
sys.stdout.reconfigure(encoding="utf-8")

from tools import search_corpus, search_modifiers

with open("eval_retrieval.json", encoding="utf-8") as f:
    cases = json.load(f)

K = 5
hits, rows = 0, []
for c in cases:
    if c.get("mode") == "modifiers":
        res = search_modifiers(c["query"], k=K)
    else:
        res = search_corpus(c["query"], section_type=c.get("section_type"), k=K)
    ids = [r["clause_id"] for r in res]
    ranks = [ids.index(e) + 1 for e in c["expected"] if e in ids]
    ok = bool(ranks)
    hits += ok
    rows.append({"id": c["id"], "pass": ok, "rank": min(ranks) if ranks else None,
                 "expected": c["expected"], "got": ids})
    print(f"{'PASS' if ok else 'FAIL'}  #{c['id']:>2}  rank={min(ranks) if ranks else '-'}  {c['query']}")
    if not ok:
        print("        expected:", c["expected"], "\n        got:     ", ids)

print(f"\nhit@{K}: {hits}/{len(cases)} = {hits / len(cases):.0%}")
with open("data/eval_results.json", "w", encoding="utf-8") as f:
    json.dump({"k": K, "hit_rate": hits / len(cases), "rows": rows}, f, indent=2)