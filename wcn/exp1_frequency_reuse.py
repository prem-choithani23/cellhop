# =============================================================================
# FILE        : wcn/exp1_frequency_reuse.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Experiment 1 - Frequency Reuse, Co-channel Interference and
#               Cell Splitting (handout: "frequency re-use and cell splitting").
# WHAT IT DOES: 1. (i, j) -> cluster size N and draws the hexagonal reuse map
#                  (same colour = same frequency group) for N = 12 (primary) and
#                  an overview of N = 3, 4, 7, 9, 12, 13.
#               2. Repeats the cluster M times, MEASURES the co-channel distance D
#                  between cell centres in the generated grid (cell area 5 km^2 ->
#                  R = 1.387 km) and compares with the theory D/R = sqrt(3N).
#               3. Channel arithmetic: 35 MHz / (2 x 200 kHz) duplex channels, and
#                  channels per cell for each N.
#               4. Cell splitting: halving the radius -> 4x cells, transmit power
#                  reduced by 10*n*log10(2) dB. Draws before/after maps.
#               5. Saves figures + CSV table + a dictionary of numbers for the report.
# LAST STEP   : wcn/hexgrid.py (geometry) and config/settings.py (EXP1 numbers).
# NEXT STEP   : wcn/exp2_trunking_gos.py takes the idea 'N cells share the channels'
#               and asks how many USERS each cell can serve for a blocking target.
# =============================================================================

import math                                   # math: sqrt, floor
import numpy as np                            # numpy: arrays
import matplotlib.pyplot as plt               # pyplot: drawing
from matplotlib.patches import Polygon        # Polygon: to draw one hexagon
from matplotlib import colormaps              # colormaps: pick distinct colours

from config import settings                   # all experiment parameters
from wcn import hexgrid as hg                 # hexagonal geometry helpers
from wcn import utils                         # saving helpers + palette

CMAP = colormaps["tab20"]                     # 20 well separated colours (>= max N we draw)


# ------------------------------------------------------------ channel arithmetic
def channel_budget(total_bw_hz, simplex_hz, n):
    """
    Duplex channels and channels per cell.
    A duplex (two-way) channel needs TWO simplex channels (forward + reverse link).
    """
    duplex_bw = 2.0 * simplex_hz                          # bandwidth of one duplex channel
    total_duplex = int(math.floor(total_bw_hz / duplex_bw))   # whole channels only
    per_cell = total_duplex // n                          # channels per cell (integer division)
    return total_duplex, per_cell


# --------------------------------------------------------------- simulation of D
def simulate_cochannel_distance(i, j, R_km, repeats_M):
    """
    Build a hexagonal grid containing at least `repeats_M` clusters, label the cells,
    and MEASURE the distance from the centre cell to its co-channel cells.
    Returns a dictionary with all grid information and the measured D values.
    """
    n = hg.cluster_size(i, j)                             # cluster size N
    # grid must hold M clusters AND at least the first tier of co-channel cells (hex distance i+j)
    radius = max(hg.disc_radius_for(repeats_M * n + n), i + j + 1)
    cells = hg.hex_disc(radius)                           # all cells of the patch
    labels = hg.assign_labels(cells, i, j)                # frequency group of every cell
    # measure: every other cell that has the SAME label as the centre cell (label 0)
    d_list = []                                           # measured distances in km
    for cell in cells:
        if labels[cell] == labels[(0, 0)] and cell != (0, 0):   # co-channel with the centre cell
            x, y = hg.axial_to_xy(*cell, R_km)            # position of the co-channel cell
            d_list.append(math.hypot(x, y))               # distance to the centre cell
    d_list.sort()                                         # nearest first
    first_tier = d_list[:6]                               # the six first-tier interferers
    d_sim = float(np.mean(first_tier))                    # simulated co-channel distance D
    return {"n": n, "radius": radius, "cells": cells, "labels": labels,
            "d_first_tier": first_tier, "d_sim_km": d_sim, "q_sim": d_sim / R_km}


# -------------------------------------------------------------------- plotting
def _draw_cells(ax, cells, labels, R, n, lw=0.8):
    """Draw each cell as a coloured hexagon with its frequency-group number inside."""
    for cell in cells:
        x, y = hg.axial_to_xy(*cell, R)                   # centre of this cell
        colour = CMAP(labels[cell] % 20)                  # colour by frequency group
        ax.add_patch(Polygon(hg.hex_vertices(x, y, R), closed=True, facecolor=colour,
                             edgecolor="white", linewidth=lw, alpha=0.9))   # filled hexagon
        ax.text(x, y, str(labels[cell] + 1), ha="center", va="center",
                fontsize=8 if n > 9 else 9, color="#111111")                # group number


def plot_reuse_map(sim, R_km, i, j, name):
    """Large map: reference cluster outlined, co-channel cells ringed, D drawn with an arrow."""
    n = sim["n"]; cells = sim["cells"]; labels = sim["labels"]
    fig, ax = plt.subplots(figsize=(9, 8))                # one big axis
    _draw_cells(ax, cells, labels, R_km, n)               # all hexagons
    # outline the reference cluster (N cells, one of each group) with thick black borders
    for cell in hg.reference_cluster(cells, labels, R_km):
        x, y = hg.axial_to_xy(*cell, R_km)
        ax.add_patch(Polygon(hg.hex_vertices(x, y, R_km), closed=True, fill=False,
                             edgecolor="black", linewidth=2.4))
    # ring the six first-tier co-channel cells with dashed circles
    for (x, y) in hg.first_tier_cochannel(i, j, R_km):
        ax.add_patch(plt.Circle((x, y), 0.62 * R_km, fill=False, edgecolor="black",
                                linestyle="--", linewidth=1.2))
    # draw the reuse distance D from the centre cell to the first co-channel cell
    x1, y1 = hg.first_tier_cochannel(i, j, R_km)[0]
    ax.annotate("", xy=(x1, y1), xytext=(0, 0),
                arrowprops=dict(arrowstyle="<->", color=utils.PALETTE[4], lw=2.4))
    ax.text(x1 / 2, y1 / 2 + 0.35 * R_km,
            f"D = {sim['d_first_tier'][0]:.2f} km\nD/R = {sim['q_sim']:.2f}",
            color=utils.PALETTE[4], fontsize=11, fontweight="bold", ha="center",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")   # keep hexagons undistorted
    ax.set_title(f"Frequency reuse map: (i, j) = ({i}, {j}) -> N = {n}\n"
                 f"same number/colour = same frequencies; bold outline = one cluster; "
                 f"dashed rings = 6 co-channel cells")
    return utils.save_fig(fig, name)


def plot_overview(R_km, pairs, repeats_M, name):
    """2 x 3 panel of small reuse maps, one per (i, j) pair."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 8.6))     # 6 small axes
    for ax, (i, j) in zip(axes.ravel(), pairs):
        sim = simulate_cochannel_distance(i, j, 1.0, repeats_M)   # unit radius is enough for a picture
        _draw_cells(ax, sim["cells"], sim["labels"], 1.0, sim["n"], lw=0.5)
        for cell in hg.reference_cluster(sim["cells"], sim["labels"], 1.0):   # outline one cluster
            x, y = hg.axial_to_xy(*cell, 1.0)
            ax.add_patch(Polygon(hg.hex_vertices(x, y, 1.0), closed=True, fill=False,
                                 edgecolor="black", linewidth=1.6))
        ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
        ax.set_title(f"N = {sim['n']}  (i={i}, j={j})   D/R = {math.sqrt(3 * sim['n']):.2f}")
    fig.suptitle("Cluster sizes from N = i^2 + ij + j^2", fontweight="bold")
    return utils.save_fig(fig, name)


def plot_channels_and_q(rows, name):
    """Bar chart of channels per cell and line chart of D/R against N."""
    ns = [r["N"] for r in rows]                           # cluster sizes on the x-axis
    fig, ax1 = plt.subplots(figsize=(8, 4.6))
    bars = ax1.bar([str(n) for n in ns], [r["channels_per_cell"] for r in rows],
                   color=utils.PALETTE[0], width=0.55)    # channels per cell as bars
    ax1.bar_label(bars, padding=2, fontsize=9)            # numbers on the bars
    ax1.set_xlabel("Cluster size N"); ax1.set_ylabel("Duplex channels per cell")
    ax1.set_title("Smaller N -> more channels per cell, but a smaller reuse ratio D/R")
    ax2 = ax1.twinx()                                     # second y-axis is for a DIFFERENT chart element
    ax2.plot([str(n) for n in ns], [r["q_theory"] for r in rows], "o-", color=utils.PALETTE[1])
    ax2.set_ylabel("Co-channel reuse ratio D/R", color=utils.PALETTE[1])
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    return utils.save_fig(fig, name)


def cell_splitting(R_km, factor, exps):
    """
    Cell splitting: new radius R' = R / factor.
    * number of cells in the same area grows by factor^2
    * Received power  Pr ~ Pt * R^-n  must stay equal at the new cell edge, so
      Pt' = Pt * (R'/R)^n  -> reduction of 10*n*log10(factor) dB.
    """
    result = {"R_old_km": R_km, "R_new_km": R_km / factor, "cell_multiplier": factor ** 2,
              "power_reduction_db": {}}
    for n in exps:                                        # compute for each path-loss exponent
        result["power_reduction_db"][str(n)] = 10.0 * n * math.log10(factor)
    return result


def _macro_cell_of(x, y, R):
    """Which macro hexagon (axial coords) contains the point (x, y)? Uses cube-coordinate rounding."""
    b = y / (1.5 * R)                                     # fractional axial coordinate b
    a = x / (hg.SQRT3 * R) - b / 2.0                      # fractional axial coordinate a
    cx, cz = a, b                                         # cube coords: x = a, z = b, y = -x - z
    cy = -cx - cz
    rx, ry, rz = round(cx), round(cy), round(cz)          # round each cube coordinate
    dx, dy, dz = abs(rx - cx), abs(ry - cy), abs(rz - cz) # rounding errors
    if dx > dy and dx > dz:   rx = -ry - rz               # fix the coordinate with the largest error
    elif dy > dz:             ry = -rx - rz
    else:                     rz = -rx - ry
    return int(rx), int(rz)                               # back to axial (a, b)


def plot_cell_splitting(R_km, factor, name):
    """
    Before / after map of cell splitting.
    Left : a patch of 7 macro cells (radius R).
    Right: the same patch re-covered by small cells of radius R/factor. A small cell is kept if
           its centre lies inside the old footprint, so the count is ~ factor^2 x 7.
    Returns (path, number_of_small_cells).
    """
    macro = hg.hex_disc(1)                                # 7 macro cells = centre + 6 neighbours
    r_small = R_km / factor                               # radius of the new small cells
    small = [c for c in hg.hex_disc(8)                    # candidate small cells
             # shrink the test point by 0.1 % towards the origin so points lying exactly on an outer
             # edge are treated the same way on every side (keeps the picture symmetric)
             if hg.hex_distance(*_macro_cell_of(0.999 * hg.axial_to_xy(*c, r_small)[0],
                                                0.999 * hg.axial_to_xy(*c, r_small)[1], R_km)) <= 1]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    for ax, cells, radius, colour, title in (
            (axes[0], macro, R_km, "#cfe0f5", f"Before: {len(macro)} cells, R = {R_km:.2f} km"),
            (axes[1], small, r_small, utils.PALETTE[0], f"After: R' = {r_small:.2f} km -> ideal {factor ** 2 * len(macro)} cells\n"
            f"({len(small)} drawn: hexagons cannot tile the old edge exactly)")):
        for cell in cells:                                # draw every hexagon
            x, y = hg.axial_to_xy(*cell, radius)
            ax.add_patch(Polygon(hg.hex_vertices(x, y, radius), closed=True, facecolor=colour,
                                 edgecolor="white", linewidth=1.0))
        ax.set_aspect("equal"); ax.set_xlim(-2.9 * R_km, 2.9 * R_km); ax.set_ylim(-2.9 * R_km, 2.9 * R_km)
        ax.axis("off"); ax.set_title(title)
    fig.suptitle(f"Cell splitting (factor {factor}): area per cell / {factor ** 2}  =>  {factor ** 2}x more cells over the same area", fontweight="bold")
    return utils.save_fig(fig, name), len(small)


# ------------------------------------------------------------------ main entry
def run(cfg=None):
    """Run the whole of Experiment 1 and return a dictionary of results for the report."""
    cfg = cfg or settings.EXP1                            # default: values from settings.py
    utils.apply_style()                                   # consistent chart look
    R_km = hg.cell_radius_from_area(cfg["cell_area_km2"]) # R from the 5 km^2 cell area
    rows = []                                             # lab table rows
    for (i, j) in cfg["ij_pairs"]:                        # loop over every (i, j) of the handout
        sim = simulate_cochannel_distance(i, j, R_km, cfg["repeats_M"])   # measure D
        n = sim["n"]
        total_dup, per_cell = channel_budget(cfg["total_bandwidth_hz"], cfg["simplex_channel_hz"], n)
        rows.append({"i": i, "j": j, "N": n,
                     "total_duplex_channels": total_dup, "channels_per_cell": per_cell,
                     "D_theory_km": math.sqrt(3 * n) * R_km, "q_theory": math.sqrt(3 * n),
                     "D_sim_km": sim["d_sim_km"], "q_sim": sim["q_sim"],
                     "q_calc_from_N": math.sqrt(3 * n)})  # 'Calculated q' column of the lab table
    # ---------------- figures
    pi, pj = cfg["primary_ij"]                            # primary pair (2, 2) -> N = 12
    sim_main = simulate_cochannel_distance(pi, pj, R_km, cfg["repeats_M"])
    fig_map = plot_reuse_map(sim_main, R_km, pi, pj, "exp1_reuse_map_N12")
    fig_ov = plot_overview(R_km, cfg["ij_pairs"], cfg["repeats_M"], "exp1_cluster_overview")
    fig_ch = plot_channels_and_q(rows, "exp1_channels_and_reuse_ratio")
    split = cell_splitting(R_km, cfg["split_factor"], cfg["split_pathloss_exp"])
    fig_sp, n_small = plot_cell_splitting(R_km, cfg["split_factor"], "exp1_cell_splitting")
    split["drawn_cells_before"], split["drawn_cells_after"] = 7, n_small   # counts shown in the figure
    # ---------------- table
    utils.save_table(
        [[r["i"], r["j"], r["N"], r["total_duplex_channels"], r["channels_per_cell"],
          round(r["D_theory_km"], 3), round(r["q_calc_from_N"], 3),
          round(r["D_sim_km"], 3), round(r["q_sim"], 3)] for r in rows],
        ["i", "j", "N", "Total duplex channels", "Channels per cell",
         "Theoretical D (km)", "Calculated q = sqrt(3N)", "Simulated D (km)", "Simulated q"],
        "exp1_lab_table")
    return {"R_km": R_km, "cell_area_km2": cfg["cell_area_km2"], "rows": rows, "splitting": split,
            "figures": [fig_map, fig_ov, fig_ch, fig_sp],
            "total_duplex_channels": rows[0]["total_duplex_channels"]}


if __name__ == "__main__":                                # allows: python -m wcn.exp1_frequency_reuse
    out = run()
    for r in out["rows"]:
        print(r)
