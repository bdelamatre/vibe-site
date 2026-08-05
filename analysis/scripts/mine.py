#!/usr/bin/env python3
"""Rank recurring phrases, suppressing generic English scaffolding."""
import collections
import json

from analyze import find_boilerplate_grams, strip_scripted, WORD

STOP = set("""a an the and or but if so to of in on at for with is are was were be
been being it its this that these those i you he she we they me him her them my
your his our their as by from not no do does did have has had can could would
should will just really very much more most too then than there here what which
who how why when where all some any one two out up down about into over
know like get got go going went say said think thing things time way people
well yeah okay ok right now even also still because want need make made take
see look come came give given put lell us am s t re ve ll m d o""".split())

docs = json.load(open("corpus.json"))
boiler = find_boilerplate_grams(docs)

counts = collections.Counter()
for d in docs:
    spoken, _ = strip_scripted(d["clean"], boiler)
    w = WORD.findall(spoken.lower())
    for n in (2, 3, 4):
        for i in range(len(w) - n + 1):
            g = w[i:i + n]
            content = [x for x in g if x not in STOP]
            if not content:
                continue
            if g[0] in STOP and g[-1] in STOP:
                continue          # phrase must start or end on a content word
            counts[" ".join(g)] += 1

print(f"{'count':>6}  phrase")
shown = 0
for g, k in counts.most_common(3000):
    if k < 45 or shown >= 75:
        break
    print(f"{k:6d}  {g}")
    shown += 1
