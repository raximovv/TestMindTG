"""TestMind scoring core — a faithful Python port of the website's logic.

Data (the 50 items, the archetypes, trait texts) is generated from the live site
into bot_content.json, so the bot never drifts from the web result. The scoring
functions mirror scoreAnswers / archetypeKeyOf in test.html exactly; xcheck.py
proves that on thousands of random inputs.
"""
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_DIR, "bot_content.json"), encoding="utf-8") as f:
    _D = json.load(f)

ITEMS = _D["items"]            # [{d, r, t, h?}] x50
ARCHETYPES = _D["archetypes"]  # keyed "X|Y" -> {name, slug, famName, color, lines, strength, watch, figure}
BY_SLUG = {a["slug"]: a for a in ARCHETYPES.values()}  # deep-link payload -> archetype
TRAITS = _D["traits"]
POLES = _D["poles"]
TEXTS = _D["texts"]
TRAIT_ORDER = _D["trait_order"]   # ['ES','E','O','A','C']
DISCLAIMER = _D["disclaimer"]

# The 5-point Uzbek scale, matching the site's LABELS.
LABELS = ["Qoʻshilmayman", "Biroz qoʻshilmayman", "Betarafman",
          "Biroz qoʻshilaman", "Qoʻshilaman"]


def score_answers(answers):
    """answers: list of 50 ints in 1..5 (0 = unanswered). Returns {ES,E,O,A,C} means."""
    sums = {"N": 0, "E": 0, "O": 0, "A": 0, "C": 0}
    counts = {"N": 0, "E": 0, "O": 0, "A": 0, "C": 0}
    for i, it in enumerate(ITEMS):
        v = answers[i]
        if not v:
            continue
        if it.get("r"):
            v = 6 - v
        sums[it["d"]] += v
        counts[it["d"]] += 1

    def m(d):
        return sums[d] / counts[d] if counts[d] else 0

    # ES is inverted Neuroticism; with no N answers it stays 0 (matches the site).
    return {
        "ES": (6 - m("N")) if counts["N"] else 0,
        "E": m("E"), "O": m("O"), "A": m("A"), "C": m("C"),
    }


def archetype_key_of(s):
    """Top two traits -> canonical 'X|Y' key, with the same stable tie-break as the site."""
    ranked = sorted(TRAIT_ORDER, key=lambda t: (-s[t], TRAIT_ORDER.index(t)))
    pair = sorted(ranked[:2], key=lambda t: TRAIT_ORDER.index(t))
    return pair[0] + "|" + pair[1]


def archetype_of(s):
    return ARCHETYPES[archetype_key_of(s)]


def level_of(mean):
    if mean <= 2.4:
        return "Past"
    if mean >= 3.6:
        return "Yuqori"
    return "Oʻrta"
