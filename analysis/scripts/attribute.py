#!/usr/bin/env python3
"""Estimate which podcast speech is Justin's, using his blog as a style
fingerprint, then count isms per predicted speaker.

This is a heuristic attribution, not a measurement. See validate() for the
independent check on whether the fingerprint carries any signal at all.
"""
import collections
import json
import math
import os
import re

from analyze import PATTERNS, find_boilerplate_grams, strip_scripted, WORD

BASE = os.path.dirname(os.path.abspath(__file__))
TS = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]$")

# Function words carry most stylometric signal within a register, but blog prose
# and unscripted speech are different registers, so they mostly encode
# "written vs spoken" here. Content words transfer better, so the fingerprint is
# restricted to them.
REGISTER = set("""a an the and or but if so to of in on at for with is are was
were be been being it its this that these those i you he she we they me him her
them my your his our their as by from not no do does did have has had can could
would should will just really very much more most too then than there here what
which who how why when where all some any one two out up down about into over
i'm it's that's don't you're we're there's they're isn't doesn't didn't can't
won't wouldn't couldn't shouldn't i've you've we've they've i'd you'd he'd
she'd we'd they'd i'll you'll he'll she'll we'll they'll let's who's""".split())


def load_turns():
    """Split each de-duplicated episode into >>-delimited turns."""
    idx = {r["id"]: r for r in json.load(open(os.path.join(BASE, "out", "index.json")))["videos"]}
    keep = {d["id"] for d in json.load(open(os.path.join(BASE, "corpus.json")))}
    episodes = []
    for vid in keep:
        rec = idx[vid]
        raw = open(os.path.join(BASE, "out", rec["file"]), encoding="utf-8").read()
        body = raw.split("-" * 72, 1)[1] if "-" * 72 in raw else raw
        text = " ".join(l for l in body.splitlines() if not TS.match(l.strip()))
        text = re.sub(r"\[(music|applause|laughter)\]", " ", text, flags=re.I)
        turns = [re.sub(r"\s+", " ", t).strip() for t in text.split(">>")]
        turns = [t for t in turns if t]
        episodes.append({"id": vid, "date": rec["date"], "turns": turns,
                         "marked": ">>" in text})
    episodes.sort(key=lambda e: e["date"])
    return episodes


def norm(text):
    """Curly apostrophes split contractions into junk tokens ("don", "isn")."""
    return text.replace("’", "'").replace("‘", "'")


def fingerprint(blog_text, podcast_text, min_count=3, alpha=0.5):
    """Log-odds of each content word in Justin's writing vs the whole podcast."""
    blog_text, podcast_text = norm(blog_text), norm(podcast_text)
    b = collections.Counter(w for w in WORD.findall(blog_text.lower())
                            if w not in REGISTER and len(w) > 2)
    p = collections.Counter(w for w in WORD.findall(podcast_text.lower())
                            if w not in REGISTER and len(w) > 2)
    nb, np_ = sum(b.values()), sum(p.values())
    vocab = {w for w, c in b.items() if c >= min_count}
    v = len(set(b) | set(p))
    return {
        w: math.log((b[w] + alpha) / (nb + alpha * v))
           - math.log((p[w] + alpha) / (np_ + alpha * v))
        for w in vocab
    }, b, nb


def score_turn(turn, fp):
    words = [w for w in WORD.findall(norm(turn).lower()) if w in fp]
    if len(words) < 4:
        return None                      # too short to score meaningfully
    return sum(fp[w] for w in words) / len(words)


def validate(turns_scored, threshold):
    """Independent check: hosts address each other by name, so a turn saying
    "Aaron" is usually NOT Aaron speaking. If the blog fingerprint carries real
    signal, predicted-Justin turns should mention Aaron MORE than the rest."""
    hi = [t for t, s in turns_scored if s >= threshold]
    lo = [t for t, s in turns_scored if s < threshold]

    def rate(turns, name):
        rx = re.compile(r"\b" + name + r"\b", re.I)
        w = sum(len(WORD.findall(t.lower())) for t in turns) or 1
        return 10000 * sum(len(rx.findall(t)) for t in turns) / w

    return {
        "predicted_justin_turns": len(hi),
        "other_turns": len(lo),
        "aaron_per10k_in_justin": rate(hi, "aaron"),
        "aaron_per10k_in_others": rate(lo, "aaron"),
        "justin_per10k_in_justin": rate(hi, "justin"),
        "justin_per10k_in_others": rate(lo, "justin"),
    }


def main():
    blog = " ".join(json.load(open(os.path.join(BASE, "blog_text.json"))).values())
    episodes = load_turns()
    docs = json.load(open(os.path.join(BASE, "corpus.json")))
    boiler = find_boilerplate_grams(docs)

    marked = [e for e in episodes if e["marked"]]
    print(f"episodes: {len(episodes)} total, {len(marked)} with >> turn markers")

    # keep only unscripted turns
    turns = []
    for e in marked:
        for t in e["turns"]:
            spoken, _ = strip_scripted(t, boiler)
            spoken = spoken.strip()
            if spoken:
                turns.append(spoken)
    print(f"turns: {len(turns):,}")

    podcast_text = " ".join(turns)
    fp, bcount, nb = fingerprint(blog, podcast_text)
    print(f"fingerprint vocabulary: {len(fp)} content words "
          f"from {nb:,} blog content-word tokens")
    top = sorted(fp.items(), key=lambda kv: -kv[1])[:25]
    print("most Justin-distinctive words:",
          ", ".join(f"{w}" for w, _ in top))

    scored = [(t, score_turn(t, fp)) for t in turns]
    scored = [(t, s) for t, s in scored if s is not None]
    print(f"scoreable turns: {len(scored):,}")

    # Justin is one of two co-hosts sharing time with a guest; assume he speaks
    # ~30% of the words. The threshold is chosen to hit that share, so the split
    # is calibrated by assumption, not discovered.
    share = 0.30
    scored.sort(key=lambda ts: -ts[1])
    total_words = sum(len(WORD.findall(t.lower())) for t, _ in scored)
    acc, threshold = 0, scored[-1][1]
    for t, s in scored:
        acc += len(WORD.findall(t.lower()))
        if acc >= share * total_words:
            threshold = s
            break

    v = validate(scored, threshold)
    print("\n--- validation (independent of the blog) ---")
    print(f"  turns predicted Justin : {v['predicted_justin_turns']:,}")
    print(f"  turns predicted Others : {v['other_turns']:,}")
    print(f"  \"Aaron\" per 10k  — predicted-Justin {v['aaron_per10k_in_justin']:.2f}"
          f"  vs others {v['aaron_per10k_in_others']:.2f}")
    print(f"  \"Justin\" per 10k — predicted-Justin {v['justin_per10k_in_justin']:.2f}"
          f"  vs others {v['justin_per10k_in_others']:.2f}")
    lift = (v["aaron_per10k_in_justin"] / v["aaron_per10k_in_others"]
            if v["aaron_per10k_in_others"] else float("nan"))
    print(f"  -> address-cue lift: {lift:.2f}x  (>1 means the fingerprint has "
          f"some signal; ~1 means none)")

    jt = [t for t, s in scored if s >= threshold]
    ot = [t for t, s in scored if s < threshold]
    jw = sum(len(WORD.findall(t.lower())) for t in jt)
    ow = sum(len(WORD.findall(t.lower())) for t in ot)
    jtext, otext = " ".join(jt), " ".join(ot)

    rows = []
    for label, pat in PATTERNS:
        rx = re.compile(pat, re.I)
        cj, co = len(rx.findall(jtext)), len(rx.findall(otext))
        rows.append({
            "label": label, "justin": cj, "others": co, "total": cj + co,
            "justin_rate": 10000 * cj / jw, "others_rate": 10000 * co / ow,
        })
    rows.sort(key=lambda r: -r["total"])

    print(f"\nwords: Justin(pred) {jw:,}  Others {ow:,}")
    print(f"\n{'phrase':24s} {'Justin':>7s} {'Others':>7s}  {'J/10k':>7s} {'O/10k':>7s}")
    for r in rows:
        print(f"{r['label']:24s} {r['justin']:7d} {r['others']:7d}  "
              f"{r['justin_rate']:7.2f} {r['others_rate']:7.2f}")

    json.dump({
        "blog_words": len(WORD.findall(blog.lower())),
        "blog_posts": 4,
        "episodes_with_turns": len(marked),
        "episodes_total": len(episodes),
        "turns": len(scored),
        "assumed_justin_share": share,
        "justin_words": jw, "others_words": ow,
        "validation": v, "address_cue_lift": lift,
        "rows": rows,
    }, open(os.path.join(BASE, "isms_by_speaker.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
