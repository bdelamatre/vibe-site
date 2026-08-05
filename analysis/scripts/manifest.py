#!/usr/bin/env python3
"""Build README.md + transcripts.csv indexes from clean.py's index.json."""
import csv
import json
import os
import sys

root = sys.argv[1]
idx = json.load(open(os.path.join(root, "index.json")))

for kind in ("videos",):
    idx[kind].sort(key=lambda r: (r["date"], r["title"]), reverse=True)

with open(os.path.join(root, "transcripts.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["kind", "published", "duration", "title", "video_id", "url", "file"])
    for kind in ("videos",):
        for r in idx[kind]:
            w.writerow(
                [
                    kind[:-1],
                    r["date"],
                    r["duration"],
                    r["title"],
                    r["id"],
                    r["url"],
                    r["file"],
                ]
            )

nv = len(idx["videos"])


def table(rows):
    out = ["| Published | Duration | Title | Transcript |", "|---|---|---|---|"]
    for r in rows:
        title = r["title"].replace("|", "\\|")
        out.append(
            f"| {r['date']} | {r['duration']} | [{title}]({r['url']}) "
            f"| [`{os.path.basename(r['file'])}`]({r['file']}) |"
        )
    return "\n".join(out)


readme = f"""# SaaS That App — YouTube transcripts

Transcripts for every video on the
[SaaS That App by Delta Systems](https://www.youtube.com/@SaasThatAppPodcast)
YouTube channel, pulled from YouTube's own caption tracks with
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

- **{nv}** long-form videos → [`videos/`](videos/)
- Shorts are **not** included — they are clips cut from these episodes, so their
  words are already present here.
- Machine-readable index: [`transcripts.csv`](transcripts.csv),
  [`index.json`](index.json)

## Format

One `.txt` per video, named `YYYYMMDD-slug-videoid.txt`, with a short metadata
header followed by the transcript. Timestamps `[HH:MM:SS]` mark roughly every
60 seconds so passages can be located in the source video.

Captions are YouTube's auto-generated ones unless the channel uploaded a manual
track, so expect occasional mistranscribed names and terms, and no speaker
labels beyond the `>>` turn markers YouTube emits.

## Episodes

{table(idx['videos'])}

"""

open(os.path.join(root, "README.md"), "w").write(readme)
print(f"wrote README.md and transcripts.csv ({nv} videos)")
