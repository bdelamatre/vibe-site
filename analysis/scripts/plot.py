#!/usr/bin/env python3
"""Grouped horizontal bar chart of distinctive podcast 'isms', by era."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(BASE, "isms.json")))

# dataviz reference palette, categorical slots 1-3. Validated for the light
# surface: lightness band, chroma floor, CVD separation (worst adjacent pair
# ΔE 9.2) and normal-vision floor (27.6) all pass. Aqua sits below 3:1 contrast,
# so the relief rule applies — every bar carries a visible direct label.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

TOP_N = 15
rows = sorted(D["rows"], key=lambda r: -r["rate"])[:TOP_N]
eras = [e["name"] for e in D["eras"]]

plt.rcParams["font.family"] = ["DejaVu Sans"]
fig, ax = plt.subplots(figsize=(14.2, 13.4), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

vmax = max(r["by_era"][e]["rate"] for r in rows for e in eras)
group_h = 0.80
bar_h = group_h / 3

for gi, (era, color) in enumerate(zip(eras, SERIES)):
    ys, vals = [], []
    for ri, r in enumerate(rows):
        ys.append(-ri + (1 - gi) * bar_h)
        vals.append(r["by_era"][era]["rate"])
    # 2px surface gap between adjacent bars
    ax.barh(ys, vals, height=bar_h * 0.86, color=color, zorder=3,
            label=f"{era}   ({D['eras'][gi]['episodes']} eps, "
                  f"{D['eras'][gi]['words'] / 1000:.0f}k words)")
    for y, v in zip(ys, vals):
        # a zero has no bar to read; label it so the row is not silently blank
        ax.text(v + vmax * 0.012, y, f"{v:.2f}" if v else "0",
                va="center", ha="left", fontsize=11,
                color=INK2 if v else MUTED, zorder=4)

ax.set_yticks([-i for i in range(len(rows))])
ax.set_yticklabels([r["label"] for r in rows], fontsize=13, color=INK)
ax.set_ylim(-len(rows) + 0.45, 0.62)
ax.set_xlim(0, vmax * 1.12)
ax.xaxis.set_major_locator(MultipleLocator(2))
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
                borderpad=1.4)
for t in leg.get_texts():
    t.set_color(INK2)

fig.suptitle('"Isms" on the SaaS That App podcast, by era', x=0.012, y=0.984,
             ha="left", fontsize=25, color=INK)
sub = (
    f"{D['words_total'] / 1000:.0f}k words of spoken dialogue from "
    f"{D['episodes']} unique episodes, {D['date_min']} → {D['date_max']}. "
    f"YouTube auto-captions.\n"
    f"Re-uploads de-duplicated (117 videos → {D['episodes']} episodes); the "
    f"scripted intro/outro read ({D['scripted_pct']:.1f}% of words) removed.\n"
    f"Ordinary filler is excluded: “you know” (95.2), “kind of / sort of” "
    f"(51.3), “actually” (20.4),\n"
    f"“a lot of” (20.0) and “I mean” (16.8) all outrank everything below.  "
    f"Every occurrence counted."
)
fig.text(0.012, 0.955, sub, ha="left", va="top", fontsize=12.8, color=INK2,
         linespacing=1.5)
fig.text(0.012, 0.011,
         "bar labels = rate per 10k words  ·  captions carry no speaker labels, "
         "so hosts and guests are pooled  ·  raw counts and the full phrase "
         "list in isms_by_era.tsv",
         ha="left", fontsize=11, color=MUTED)

fig.subplots_adjust(left=0.163, right=0.985, top=0.868, bottom=0.072)
out = os.path.join(BASE, "saas-that-app-isms.png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
