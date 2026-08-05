#!/usr/bin/env python3
"""Count recurring turns of phrase across the podcast corpus, by era."""
import collections
import csv
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def shingles(words, n=8):
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def find_boilerplate_grams(docs, n=8, min_share=0.30):
    """8-grams recited in >=30% of episodes belong to the scripted read.

    Matching whole sentences fails here: each episode's intro is a separate ASR
    pass, so the wording drifts. Shingles survive that drift."""
    seen = collections.Counter()
    for d in docs:
        words = WORD.findall(d["clean"].lower())
        seen.update(set(shingles(words, n)))
    cutoff = max(2, int(min_share * len(docs)))
    return {g for g, c in seen.items() if c >= cutoff}


def strip_scripted(text, boiler, n=8, frac=0.5):
    """Drop sentences that are mostly scripted shingles."""
    kept, removed = [], 0
    for s in sentences(text):
        w = WORD.findall(s.lower())
        sh = shingles(w, n)
        if sh and sum(g in boiler for g in sh) / len(sh) >= frac:
            removed += len(w)
            continue
        kept.append(s)
    return " ".join(kept), removed


# label -> regex. Case-insensitive, word-boundary anchored.
#
# Generic English scaffolding is deliberately EXCLUDED: "you know" (95.2/10k),
# "kind of / sort of" (51.3), "actually" (20.4), "a lot of" (20.0), "I mean"
# (16.8), "a little bit" (8.6) and "I don't know" (5.1). They are the corpus's
# most frequent phrases by a wide margin, but they are ordinary conversational
# filler rather than anything characteristic of this show, and on one linear
# scale they flatten every distinctive term to invisibility.
PATTERNS = [
    ("AI",                      r"\bai\b"),
    ("“and I was like”", r"\b(?:i|he|she|they|we)\s*(?:'m|'s|'re|was|were|am|is|are)\s+like\b"),
    ("SaaS",                    r"\b(?:saas|sas|sass)\b"),
    ("founder(s)",              r"\bfounders?\b"),
    ("basically",               r"\bbasically\b"),
    ("obviously",               r"\bobviously\b"),
    ("absolutely",              r"\babsolutely\b"),
    ("things like that",        r"\bthings like that\b"),
    ("literally",               r"\bliterally\b"),
    ("churn",                   r"\bchurn(?:ed|ing)?\b"),
    ("MVP",                     r"\bmvps?\b"),
    ("bootstrap(ped)",          r"\bboot ?strap(?:ped|ping)?\b"),
    ("product-market fit",      r"\bproduct[\s-]market fit\b"),
    ("ideal customer profile",  r"\b(?:icp|ideal customer profile)\b"),
    ("makes sense",             r"\bmakes sense\b"),
    ("technical debt",          r"\btech(?:nical)? debt\b"),
    ("honestly",                r"\bhonestly\b"),
    ("at the end of the day",   r"\bat the end of the day\b"),
    ("go to market",            r"\bgo[- ]to[- ]market\b"),
    ("tech stack",              r"\btech stack\b"),
    ("runway",                  r"\brunway\b"),
    ("edge case(s)",            r"\bedge case[sd]?\b"),
    ("north star",              r"\bnorth star\b"),
    ("greenfield",              r"\bgreen ?field\b"),
]


def eras(docs, k=3):
    """Split chronologically into k equal-sized buckets."""
    docs = sorted(docs, key=lambda d: d["date"])
    out, n = [], len(docs)
    for i in range(k):
        lo, hi = i * n // k, (i + 1) * n // k
        chunk = docs[lo:hi]
        out.append((f"{chunk[0]['date'][:7]} → {chunk[-1]['date'][:7]}", chunk))
    return out


def main():
    docs = json.load(open(os.path.join(BASE, "corpus.json")))
    boiler = find_boilerplate_grams(docs)

    scripted_words = 0
    for d in docs:
        d["spoken"], removed = strip_scripted(d["clean"], boiler)
        d["tokens"] = WORD.findall(d["spoken"].lower())
        scripted_words += removed

    total = sum(len(d["tokens"]) for d in docs)
    raw_total = total + scripted_words
    print(f"episodes: {len(docs)}")
    print(f"words: {raw_total:,} -> {total:,} spontaneous "
          f"({100 * scripted_words / raw_total:.1f}% scripted read removed)")

    groups = eras(docs)
    for name, chunk in groups:
        print(f"  era {name}: {len(chunk)} episodes, "
              f"{sum(len(d['tokens']) for d in chunk):,} words")

    rows = []
    for label, pat in PATTERNS:
        rx = re.compile(pat, re.I)
        rec = {"label": label, "pattern": pat, "total": 0}
        for name, chunk in groups:
            words = sum(len(d["tokens"]) for d in chunk)
            hits = sum(len(rx.findall(d["spoken"])) for d in chunk)
            rec[name] = (hits, 10000 * hits / words)
            rec["total"] += hits
        rec["rate"] = 10000 * rec["total"] / total
        rows.append(rec)

    rows.sort(key=lambda r: -r["rate"])
    names = [n for n, _ in groups]
    print(f"\n{'phrase':26s} {'total':>7s} {'per10k':>7s}  " +
          "  ".join(f"{n:>16s}" for n in names))
    for r in rows:
        cells = "  ".join(f"{r[n][0]:6d}/{r[n][1]:8.2f}" for n in names)
        print(f"{r['label']:26s} {r['total']:7d} {r['rate']:7.2f}  {cells}")

    with open(os.path.join(BASE, "isms_by_era.tsv"), "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["phrase", "regex", "total_occurrences", "rate_per_10k"] +
                   [f"{n} ({c})" for n, c in
                    zip(names, ["count/rate"] * len(names))])
        for r in rows:
            w.writerow([r["label"], r["pattern"], r["total"], f"{r['rate']:.3f}"] +
                       [f"{r[n][0]}/{r[n][1]:.3f}" for n in names])

    json.dump(
        {
            "episodes": len(docs),
            "words_total": total,
            "words_raw": raw_total,
            "scripted_pct": 100 * scripted_words / raw_total,
            "date_min": min(d["date"] for d in docs),
            "date_max": max(d["date"] for d in docs),
            "eras": [
                {"name": n,
                 "episodes": len(c),
                 "words": sum(len(d["tokens"]) for d in c)}
                for n, c in groups
            ],
            "rows": [
                {"label": r["label"], "total": r["total"], "rate": r["rate"],
                 "by_era": {n: {"count": r[n][0], "rate": r[n][1]} for n in names}}
                for r in rows
            ],
        },
        open(os.path.join(BASE, "isms.json"), "w"), indent=2,
    )


if __name__ == "__main__":
    main()
