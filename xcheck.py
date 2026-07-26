"""Proves the Python scoring matches the website's JS exactly.

_extract.js writes xcheck.json: random answer sets, each with the archetype key
the REAL site JS computed. This replays them through the Python port and asserts
every one matches. Run after regenerating bot_content.json.
"""
import json
import sys

import testmind_core as core

cases = json.load(open("xcheck.json", encoding="utf-8"))
bad = 0
for c in cases:
    s = core.score_answers(c["a"])
    if core.archetype_key_of(s) != c["key"]:
        bad += 1

print(f"{len(cases)} random answer sets checked")
if bad:
    print(f"MISMATCHES: {bad}")
    sys.exit(1)
print("PERFECT — Python archetype == site JS archetype on every case")
