#!/usr/bin/env python3
"""Grouped horizontal bar chart of podcast 'isms' by era."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(BASE, "isms.json")))

# dataviz reference palette, categorical slots 1-3 (validated: all checks pass,
# light surface; aqua is sub-3:1 so every bar carries a visible direct label)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

SHOW = [
    "you know", "kind of / sort of", "actually", "a lot of", "I mean", "AI",
    "“and I was like”", "SaaS", "a little bit", "founder(s)", "basically",
    "I don't know",
]

rows = {r["label"]: r for r in D["rows"]}
rows = [rows[l] for l in SHOW]
eras = [e["name"] for e in D["eras"]]

plt.rcParams["font.family"] = ["DejaVu Sans"]
fig, ax = plt.subplots(figsize=(14.2, 11.0), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

n = len(rows)
group_h = 0.78          # height of one phrase group
bar_h = group_h / 3

for gi, (era, color) in enumerate(zip(eras, SERIES)):
    ys, vals = [], []
    for ri, r in enumerate(rows):
        # top row at top: invert the y axis by negating position
        centre = -ri
        offset = (1 - gi) * bar_h          # series 1 above, series 3 below
        ys.append(centre + offset)
        vals.append(r["by_era"][era]["rate"])
    # 2px surface gap between adjacent bars -> shrink height slightly
    ax.barh(ys, vals, height=bar_h * 0.86, color=color, zorder=3,
            label=f"{era}   ({D['eras'][gi]['episodes']} eps, "
                  f"{D['eras'][gi]['words'] / 1000:.0f}k words)")
    for y, v in zip(ys, vals):
        ax.text(v + 0.9, y, f"{v:.2f}", va="center", ha="left",
                fontsize=11.5, color=INK2, zorder=4)

ax.set_yticks([-i for i in range(n)])
ax.set_yticklabels([r["label"] for r in rows], fontsize=13.5, color=INK)
ax.set_ylim(-n + 0.42, 0.62)

vmax = max(r["by_era"][e]["rate"] for r in rows for e in eras)
ax.set_xlim(0, vmax * 1.10)
ax.xaxis.set_major_locator(MultipleLocator(20))
ax.tick_params(axis="x", colors=MUTED, labelsize=12, length=0)
ax.tick_params(axis="y", length=0)
ax.set_xlabel("occurrences per 10,000 words of spontaneous speech",
              fontsize=13.5, color=INK2, labelpad=14)

ax.xaxis.grid(True, color=GRID, linewidth=1, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)
ax.spines["left"].set_color(AXIS)
ax.spines["left"].set_linewidth(1)

leg = ax.legend(loc="lower right", frameon=False, fontsize=12.5,
                labelspacing=0.85, handlelength=1.5, handleheight=1.1,
                borderpad=1.2)
for t in leg.get_texts():
    t.set_color(INK2)

fig.suptitle('"Isms" on the SaaS That App podcast, by era', x=0.012, y=0.983,
             ha="left", fontsize=25, color=INK)
sub = (
    f"{D['words_total'] / 1000:.0f}k words of spoken dialogue from "
    f"{D['episodes']} unique episodes, {D['date_min']} → {D['date_max']}.\n"
    f"YouTube auto-captions. Re-uploads de-duplicated (117 videos → "
    f"{D['episodes']} episodes); the scripted intro/outro read "
    f"({D['scripted_pct']:.1f}% of words) removed.\n"
    f"Every occurrence counted, including repeats within an episode."
)
fig.text(0.012, 0.938, sub, ha="left", va="top", fontsize=13.2, color=INK2,
         linespacing=1.5)
fig.text(0.012, 0.012,
         "bar labels = rate per 10k words  ·  full phrase list and raw counts "
         "in isms_by_era.tsv",
         ha="left", fontsize=11.5, color=MUTED)

fig.subplots_adjust(left=0.155, right=0.985, top=0.845, bottom=0.085)
out = os.path.join(BASE, "saas-that-app-isms.png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
