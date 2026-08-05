# "Isms" analysis — SaaS That App podcast

![Isms on the SaaS That App podcast](saas-that-app-isms.png)

Counts of recurring turns of phrase across the podcast's spoken dialogue,
measured as **occurrences per 10,000 words** so the numbers stay comparable
across a corpus of uneven episode lengths. Split into three chronological eras
of roughly equal size (20/21/21 episodes), so the bars compare like with like.

- **62 unique episodes**, 2025-04-17 → 2026-07-28
- **508,541 words** of spontaneous speech analysed
- Full phrase list with regexes, raw counts and a per-era breakdown:
  [`isms_by_era.tsv`](isms_by_era.tsv) · machine-readable:
  [`isms.json`](isms.json)

## The estimated per-speaker split

![Isms by speaker, estimated](saas-that-app-isms-by-speaker.png)

[`isms_by_speaker.json`](isms_by_speaker.json) · built by
[`scripts/attribute.py`](scripts/attribute.py)

**This chart is a guess, and it is labelled as one.** There is no speaker
attribution in the captions (see below), so speech is sorted into "Justin" and
"everyone else" by lexical similarity to the 9,413 words Justin has published on
[justinedwards.me](https://justinedwards.me/) across 4 posts. Read the shares,
not the segment sizes.

How it works: episodes are split into `>>`-delimited turns (47 of the 62
episodes carry markers, giving 1,483 scoreable turns), a log-odds fingerprint is
built from Justin's blog against the podcast as background, each turn is scored,
and the highest-scoring turns are labelled Justin.

Three things limit it, and they all push the same way:

1. **The 30% split is assumed, not discovered.** Justin is one of two co-hosts
   sharing time with a guest, so the threshold is set to make him 30% of
   attributed words. Segment *sizes* therefore encode that assumption; only each
   bar's *share* carries information, and 30% is the parity point (marked on
   each bar).
2. **Blog prose and unscripted speech are different registers.** Function words
   carry most stylometric signal, but here they mostly encode "written vs
   spoken", so the fingerprint is restricted to content words — which makes it
   lean on *topic* more than *style*. Its top terms are things like `caching`,
   `elasticsearch`, `middleman`, `staging`. It finds infrastructure talk, and
   infers Justin from it.
3. **Validation says weak-but-real.** Hosts address each other by name, so a
   turn saying "Aaron" is usually *not* Aaron speaking. Predicted-Justin turns
   mention Aaron **1.95× more** than the rest — evidence of genuine signal,
   independent of the blog. But predicted-Justin turns also mention *Justin*
   more (6.75 vs 4.87 per 10k), which they should not if the split were clean.
   That pattern says the classifier is substantially separating **host banter
   from guest monologue**, with only a mild Justin-vs-Aaron tilt on top.

Treat the numbers as a hypothesis to check against a real diarization run, not
as a finding. `technical debt` at 63% Justin and `ideal customer profile` at 9%
are the kind of claims that would be first to fall.

## Why there is no *measured* per-speaker split

There is no speaker attribution in the source data, and no sound way to
reconstruct it from text:

- YouTube's caption tracks carry **no speaker labels** — no `Aaron:` / `Justin:`
  markers anywhere in the corpus.
- The `>>` markers are **caption-segment boundaries, not speaker turns**. In the
  2026-06-09 episode, Justin gets two consecutive `>>` turns during the intro,
  so attribution by alternation desynchronises immediately — and a single missed
  boundary silently inverts every label after it.
- Delta Systems' per-episode pages are **show notes, not transcripts**.

The one sound route is audio diarization — cluster the audio by voice, then map
clusters onto the caption timestamps, anchoring identity on the "And I'm Justin
Edwards" line that opens each episode. That is a real pipeline but needs
hardware this analysis did not have (4 CPUs, no GPU, ~41 hours of audio), so
**hosts and guests are pooled** in every number here.

## Which phrases are counted

Ordinary conversational filler is **deliberately excluded**. These are the
corpus's most frequent phrases by a wide margin, but they are generic English
rather than anything characteristic of this show, and on a single linear scale
they flatten every distinctive term to invisibility:

| Excluded | per 10k |
|---|---|
| you know | 95.21 |
| kind of / sort of | 51.26 |
| actually | 20.37 |
| a lot of | 19.96 |
| I mean | 16.79 |
| a little bit | 8.61 |
| I don't know | 5.11 |

## Method

Source text is the transcript set in [`../transcripts/`](../transcripts/), which
is YouTube's own caption data. Four corrections are applied before counting,
each of which materially changes the numbers:

1. **Shorts excluded.** The channel's 253 shorts are clips cut from the
   episodes; counting them would double-weight whichever passages got clipped.
2. **Re-uploads de-duplicated.** 55 of the 117 videos are second uploads of an
   episode already in the set — a different cut, transcribed by a separate ASR
   pass. Their 3-gram containment against their twin is 0.80–0.89, versus 0.07
   for unrelated episodes, which is how they were identified. The longest cut of
   each title is kept, leaving 62 episodes.
3. **Scripted read removed.** Every episode recites the same intro and sign-off.
   Left in, the show's own tagline would rank as its top "ism" in ~62 copies.
   Whole-sentence matching does not find these — each episode is a separate ASR
   pass, so the wording drifts — so detection works on 8-gram shingles appearing
   in ≥30% of episodes. This removes 0.6% of words.
4. **ASR spelling variants folded together.** "SaaS" is transcribed as `saas`,
   `sas` and `sass`; matching only the first would undercount it by ~60%.

## Caveats

- These are **auto-generated captions**, not a verified transcript. Proper nouns
  and technical terms are unreliable, and the counts inherit any systematic ASR
  bias — filler words in particular are transcribed inconsistently, so treat the
  absolute rates as approximate.
- **Hosts and guests are pooled** (see above). A term that looks like a house
  style may be coming from guests.
- The phrase list is **curated, not exhaustive** — it was drawn from ranked
  n-grams plus a tested list of business-jargon candidates. Terms that scored
  zero (`boil the ocean`, `burn rate`, `100%`, `scratch your own itch`) were
  dropped. Absence from the chart means "not measured or not found", not
  "never said".

## Reproducing

Scripts are in [`scripts/`](scripts/), run in this order:

| Script | Does |
|---|---|
| `clean.py` | yt-dlp VTT → de-duplicated plain-text transcripts |
| `manifest.py` | builds the transcript README and CSV index |
| `discover.py` | dedupes re-uploads, strips boilerplate, ranks n-grams |
| `mine.py` | ranks phrases with generic scaffolding suppressed |
| `analyze.py` | counts the curated phrase list → TSV + JSON |
| `plot.py` | renders the chart |

Captions were fetched with `yt-dlp --skip-download --write-subs
--write-auto-subs --sub-langs "en.*"`.
