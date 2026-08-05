#!/usr/bin/env python3
"""Stacked bars: estimated Justin share of each ism vs everyone else."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(BASE, "isms_by_speaker.json")))

# dataviz reference palette, categorical slots 1-2 (validated light mode:
# all checks pass, worst-pair CVD ΔE 24.7, both >= 3:1 on the surface)
JUSTIN, OTHERS = "#2a78d6", "#eb6834"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

TOP_N = 15
rows = sorted(D["rows"], key=lambda r: -r["total"])[:TOP_N]
share = D["assumed_justin_share"]

plt.rcParams["font.family"] = ["DejaVu Sans"]
fig, ax = plt.subplots(figsize=(14.0, 11.2), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ys = [-i for i in range(len(rows))]
j = [r["justin"] for r in rows]
o = [r["others"] for r in rows]
vmax = max(r["total"] for r in rows)
gap = vmax * 0.0022        # 2px surface gap between stacked segments

ax.barh(ys, j, height=0.6, color=JUSTIN, zorder=3,
        label=f"Justin (estimated)   {D['justin_words']:,} words")
ax.barh(ys, o, height=0.6, left=[x + gap for x in j], color=OTHERS, zorder=3,
        label=f"Everyone else   {D['others_words']:,} words")

for y, r in zip(ys, rows):
    pct = 100 * r["justin"] / r["total"] if r["total"] else 0
    if r["justin"] > vmax * 0.045:
        ax.text(r["justin"] / 2, y, f"{r['justin']}", va="center", ha="center",
                fontsize=11, color="white", zorder=5)
    if r["others"] > vmax * 0.045:
        ax.text(r["justin"] + r["others"] / 2, y, f"{r['others']}",
                va="center", ha="center", fontsize=11, color="white", zorder=5)
    ax.text(r["total"] + vmax * 0.012, y, f"{pct:.0f}% Justin",
            va="center", ha="left", fontsize=11.5,
            color=INK2 if pct >= 100 * share else MUTED, zorder=4)

# parity marker: Justin is 30% of all attributed words, so a bar whose blue
# segment exceeds 30% is one he over-uses relative to his share of the talking
for y, r in zip(ys, rows):
    ax.plot([r["total"] * share, r["total"] * share], [y - 0.3, y + 0.3],
            color=SURFACE, lw=1.6, zorder=6)

ax.set_yticks(ys)
ax.set_yticklabels([r["label"] for r in rows], fontsize=13, color=INK)
ax.set_ylim(-len(rows) + 0.45, 0.62)
ax.set_xlim(0, vmax * 1.20)
ax.xaxis.set_major_locator(MultipleLocator(100))
ax.tick_params(axis="x", colors=MUTED, labelsize=12, length=0)
ax.tick_params(axis="y", length=0)
ax.set_xlabel("occurrences (white tick marks the 30% parity point)",
              fontsize=13, color=INK2, labelpad=14)

ax.xaxis.grid(True, color=GRID, linewidth=1, zorder=0)
ax.set_axisbelow(True)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)
ax.spines["left"].set_color(AXIS)
ax.spines["left"].set_linewidth(1)

leg = ax.legend(loc="lower right", frameon=False, fontsize=12.5,
                labelspacing=0.8, handlelength=1.5, handleheight=1.1,
                borderpad=1.4)
for t in leg.get_texts():
    t.set_color(INK2)

fig.suptitle('"Isms" by speaker — estimated, not measured', x=0.012, y=0.983,
             ha="left", fontsize=25, color=INK)
sub = (
    f"Speech from {D['episodes_with_turns']} episodes with caption turn markers "
    f"({D['turns']:,} turns) sorted into “Justin” and “everyone else”\n"
    f"by lexical similarity to the {D['blog_words']:,} words on "
    f"justinedwards.me ({D['blog_posts']} posts). The captions contain no "
    f"speaker labels —\n"
    f"this is a guess. The {share:.0%} split is assumed, not discovered, so "
    f"segment sizes are set by that assumption;\n"
    f"only the share of each bar is informative. Validation: "
    f"{D['address_cue_lift']:.1f}× more “Aaron” mentions in predicted-Justin "
    f"turns — real but weak signal."
)
fig.text(0.012, 0.945, sub, ha="left", va="top", fontsize=12.4, color=INK2,
         linespacing=1.5)
fig.text(0.012, 0.011,
         "segment labels = raw occurrences  ·  blog prose and unscripted "
         "speech are different registers, so the fingerprint leans on topic "
         "words more than style  ·  isms_by_speaker.json",
         ha="left", fontsize=10.5, color=MUTED)

fig.subplots_adjust(left=0.163, right=0.985, top=0.836, bottom=0.082)
out = os.path.join(BASE, "saas-that-app-isms-by-speaker.png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
