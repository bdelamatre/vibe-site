#!/usr/bin/env python3
"""Convert yt-dlp VTT captions into de-duplicated plain-text transcripts."""
import html
import json
import os
import re
import sys
import textwrap

CUE = re.compile(
    r"(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})"
)
TAG = re.compile(r"<[^>]+>")


def parse_vtt(path):
    """Yield (start_seconds, text_line) with rolling-caption duplicates removed."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    out = []
    last = None
    start = None
    for line in lines:
        m = CUE.search(line)
        if m:
            h, mi, s = m.group(1).split(":")
            start = int(h) * 3600 + int(mi) * 60 + float(s)
            continue
        if start is None:
            continue  # header block
        text = html.unescape(TAG.sub("", line)).strip()
        if not text or text == last:
            continue
        # auto-captions repeat the previous line as the top of the next cue
        if out and text == out[-1][1]:
            continue
        out.append((start, text))
        last = text
    return out


def stamp(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def to_text(cues, interval=60):
    """Group cues into paragraphs, one timestamp marker per interval."""
    blocks = []
    buf = []
    mark = None
    for start, text in cues:
        if mark is None:
            mark = start
        buf.append(text)
        if start - mark >= interval:
            blocks.append((mark, " ".join(buf)))
            buf = []
            mark = None
    if buf:
        blocks.append((mark or 0, " ".join(buf)))

    parts = []
    for start, body in blocks:
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            continue
        parts.append(f"[{stamp(start)}]\n" + textwrap.fill(body, 88))
    return "\n\n".join(parts)


def slug(title, maxlen=60):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:maxlen].strip("-") or "untitled"


def pick(raw_dir, vid):
    """Prefer manual/primary `.en.vtt`, fall back to `.en-orig.vtt` or any en variant."""
    cands = [f for f in os.listdir(raw_dir) if f.startswith(vid + ".")]
    if not cands:
        return None
    for suffix in (".en.vtt", ".en-orig.vtt"):
        for c in cands:
            if c.endswith(suffix):
                return os.path.join(raw_dir, c)
    return os.path.join(raw_dir, sorted(cands)[0])


def main(kind, outroot):
    base = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(base, "raw", kind)
    outdir = os.path.join(outroot, kind)
    os.makedirs(outdir, exist_ok=True)

    meta = {}
    mpath = os.path.join(base, f"meta_{kind}.tsv")
    if os.path.exists(mpath):
        for line in open(mpath, encoding="utf-8"):
            line = line.rstrip("\n")
            # yt-dlp's --print-to-file emits a literal backslash-t, not a tab
            f = line.split("\t") if "\t" in line else line.split("\\t")
            if len(f) >= 4:
                meta[f[0]] = {
                    "upload_date": f[1],
                    "duration": f[2],
                    "title": f[3],
                }

    lists = json.load(open(os.path.join(base, "lists.json")))
    written, missing = [], []

    for vid, title, duration in lists[kind]:
        m = meta.get(vid, {})
        title = m.get("title") or title or vid
        src = pick(raw_dir, vid)
        if not src:
            missing.append((vid, title))
            continue
        cues = parse_vtt(src)
        if not cues:
            missing.append((vid, title))
            continue

        date = m.get("upload_date") or "00000000"
        date_fmt = (
            f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else "unknown"
        )
        dur = m.get("duration") or duration or ""
        try:
            dur = stamp(float(dur))
        except (TypeError, ValueError):
            dur = "unknown"

        name = f"{date}-{slug(title)}-{vid}.txt"
        header = (
            f"{title}\n"
            f"{'=' * len(title)}\n\n"
            f"Video ID:  {vid}\n"
            f"URL:       https://www.youtube.com/watch?v={vid}\n"
            f"Published: {date_fmt}\n"
            f"Duration:  {dur}\n"
            f"Source:    YouTube captions (auto-generated unless noted)\n\n"
            f"{'-' * 72}\n\n"
        )
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as fh:
            fh.write(header + to_text(cues) + "\n")
        written.append(
            {
                "id": vid,
                "title": title,
                "date": date_fmt,
                "duration": dur,
                "file": f"{kind}/{name}",
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
        )

    return written, missing


if __name__ == "__main__":
    outroot = sys.argv[1]
    index = {}
    for kind in sys.argv[2:] or ["videos"]:
        w, miss = main(kind, outroot)
        index[kind] = w
        print(f"{kind}: wrote {len(w)}, missing captions {len(miss)}")
        for vid, t in miss:
            print(f"  MISSING {vid}  {t}")
    json.dump(index, open(os.path.join(outroot, "index.json"), "w"), indent=2)
