from tools import get_clause_parts, check_waiting_period, check_daycare

print("== cover clause parts ==")
for p in get_clause_parts("policy:3.1.1"):
    print(p["clause_id"], "page", p["page"])

print("\n== waiting period: planned cataract surgery ==")
w = check_waiting_period("planned cataract surgery")
print("listed:", w["listed"])
for m in w["matches"]:
    print(m["clause_id"], "page", m["page"], "months mentioned:", m["months_mentioned"])

print("\n== day care ==")
for q in ["cataract surgery", "heart bypass surgery"]:
    d = check_daycare(q)
    print(q, "->", d["status"], [m["clause_id"] for m in d["matches"]])