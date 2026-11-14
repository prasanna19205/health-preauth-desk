import sys

from tools import search_corpus, search_modifiers

sys.stdout.reconfigure(encoding="utf-8")

# Step 1: the obvious search. This is what a single retrieval pass returns.
cover = search_corpus("planned cataract surgery, policy 11 months old",
                      section_type="cover", k=3)

# Step 2: a second search built from what step 1 revealed ("cataract"),
# looking for provisions that MODIFY the cover clause.
mods = search_modifiers("cataract waiting period", k=3)

print("=== COVER CLAUSES ===")
for r in cover:
    print(f"{r['clause_id']} | page {r['page']} | score {r['score']}")
    print(r["text"][:300].replace("\n", " "))
    print()

print("=== MODIFIER CLAUSES (waiting period / exclusion / sublimit) ===")
for r in mods:
    print(f"{r['clause_id']} | {r['section_type']} | page {r['page']} | score {r['score']}")
    print(r["text"][:300].replace("\n", " "))
    print()