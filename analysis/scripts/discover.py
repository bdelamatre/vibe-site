#!/usr/bin/env python3
"""Explore the transcript corpus: dedupe re-uploads, strip scripted boilerplate,
then rank candidate 'isms' by frequency."""
import collections
import json
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "out"
BASE = os.path.dirname(os.path.abspath(__file__))

TS = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]$")
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def load():
    """Return [{id,title,date,duration_s,text}] for the long-form episodes."""
    idx = json.load(open(os.path.join(ROOT, "index.json")))["videos"]
    docs = []
    for rec in idx:
        path = os.path.join(ROOT, rec["file"])
        raw = open(path, encoding="utf-8").read()
        body = raw.split("-" * 72, 1)[1] if "-" * 72 in raw else raw
        lines = [l for l in body.splitlines() if not TS.match(l.strip())]
        text = " ".join(lines)
        text = text.replace(">>", " ")
        text = re.sub(r"\[(music|applause|laughter)\]", " ", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        h, m, s = (rec["duration"].split(":") + ["0", "0"])[:3]
        try:
            dur = int(h) * 3600 + int(m) * 60 + int(s)
        except ValueError:
            dur = 0
        docs.append(
            dict(id=rec["id"], title=rec["title"], date=rec["date"],
                 duration_s=dur, text=text)
        )
    return docs


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def dedupe(docs):
    """Same episode re-uploaded under one title -> keep the longest cut."""
    by = collections.defaultdict(list)
    for d in docs:
        by[norm_title(d["title"])].append(d)
    kept, dropped = [], []
    for _, group in by.items():
        group.sort(key=lambda d: (-d["duration_s"], d["id"]))
        kept.append(group[0])
        dropped.extend(group[1:])
    kept.sort(key=lambda d: d["date"])
    return kept, dropped


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def find_boilerplate(docs, min_share=0.4, min_words=6):
    """Sentences recited in a large share of episodes = scripted intro/outro."""
    seen = collections.Counter()
    for d in docs:
        uniq = set()
        for s in sentences(d["text"]):
            w = WORD.findall(s.lower())
            if len(w) >= min_words:
                uniq.add(" ".join(w))
        seen.update(uniq)
    n = len(docs)
    return {s for s, c in seen.items() if c >= min_share * n}


def strip_boilerplate(text, boiler):
    out = []
    for s in sentences(text):
        key = " ".join(WORD.findall(s.lower()))
        if key in boiler:
            continue
        out.append(s)
    return " ".join(out)


def ngrams(tokens, n):
    return (" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


if __name__ == "__main__":
    docs = load()
    kept, dropped = dedupe(docs)
    print(f"loaded {len(docs)} transcripts -> {len(kept)} unique episodes "
          f"({len(dropped)} re-uploads dropped)")
    for d in dropped[:10]:
        print(f"   dropped {d['id']}  {d['title'][:60]}")

    boiler = find_boilerplate(kept)
    print(f"\nscripted boilerplate sentences detected: {len(boiler)}")
    for s in sorted(boiler, key=len, reverse=True)[:8]:
        print(f"   - {s[:110]}")

    total_raw = total_clean = 0
    for d in kept:
        d["clean"] = strip_boilerplate(d["text"], boiler)
        d["tokens"] = WORD.findall(d["clean"].lower())
        total_raw += len(WORD.findall(d["text"].lower()))
        total_clean += len(d["tokens"])
    print(f"\nwords: {total_raw:,} raw -> {total_clean:,} after boilerplate removal "
          f"({100 * (total_raw - total_clean) / max(total_raw, 1):.1f}% scripted)")

    years = collections.Counter(d["date"][:4] for d in kept)
    print("episodes by year:", dict(sorted(years.items())))
    print("date range:", kept[0]["date"], "->", kept[-1]["date"])

    json.dump(
        [{k: d[k] for k in ("id", "title", "date", "duration_s", "clean")} for d in kept],
        open(os.path.join(BASE, "corpus.json"), "w"),
    )

    for n in (1, 2, 3, 4, 5):
        c = collections.Counter()
        for d in kept:
            c.update(ngrams(d["tokens"], n))
        print(f"\n=== top {n}-grams ===")
        for g, k in c.most_common(60 if n > 1 else 40):
            print(f"   {k:6d}  {g}")
