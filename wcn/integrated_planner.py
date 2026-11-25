# =============================================================================
# FILE        : wcn/integrated_planner.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : The UNIQUE part of the project. It joins all five experiments into ONE
#               design study: "Which cluster size N should this 84-cell, 300-channel
#               network use, once capacity, interference, fading and hop-resilience are
#               considered together?"
# WHAT IT DOES: For every valid cluster size N = i^2 + ij + j^2 (3 ... 19) it computes
#               [Expt 1] reuse ratio D/R = sqrt(3N) and the co-channel SIR (6 first-tier interferers)
#                        - simple formula, worst-case-user formula, and a Monte-Carlo with
#                          random user positions;
#               [Expt 2] channels per cell C = floor(300/N), Erlang-B capacity at 1 % blocking,
#                        users per cell / per system;
#               [Expt 4] log-normal shadowing (sigma = 4 dB) and Rayleigh fading added to the SIR
#                        Monte-Carlo -> OUTAGE probability  P(SIR < threshold);
#               [Expt 3] frequency-diversity order = hop-band / coherence bandwidth;
#               [Expt 5] the cell's C channels ARE the hop set, so processing gain PG = 10 log10(C),
#                        tone-jammer hit probability 1/C and BER under jamming;
#               [Expt 1] cell-splitting what-if (x4 cells, -10 n log10 2 dB transmit power).
#               DECISION RULE: pick the cluster size with the MOST users whose outage <= target.
# LAST STEP   : exp1 ... exp5 each produced their results dictionaries (passed in as arguments).
# NEXT STEP   : wcn/report_builder.py turns all results + figures into the cumulative .docx report.
# HONESTY NOTE: The coupling 'hop set = cell channel allocation' and the 'outage-constrained
#               capacity' rule are modelling choices of THIS project (documented in the report),
#               not formulas from a textbook. The building blocks are all standard.
# =============================================================================

import math                                   # math: sqrt, floor, ceil
import numpy as np                            # numpy: Monte-Carlo arrays
import matplotlib.pyplot as plt               # pyplot: drawing

from config import settings                   # PLANNER + EXP2 parameters
from wcn import hexgrid as hg                 # cluster geometry
from wcn import exp2_trunking_gos as e2       # Erlang-B capacity
from wcn import exp5_fhss as e5               # jam BER theory
from wcn import utils                         # saving helpers


# ------------------------------------------------------------- SIR formulas
def sir_simple_db(q, n, i0=6):
    """Textbook approximation  S/I = (D/R)^n / i0  with i0 = 6 first-tier interferers (in dB)."""
    return 10.0 * math.log10(q ** n / i0)


def sir_worst_case_db(q, n):
    """
    Rappaport's worst case: mobile at the cell edge (distance R from its own base station);
    interferers at D-R (x2), D (x2), D+R (x2):   S/I = R^-n / [2(D-R)^-n + 2 D^-n + 2(D+R)^-n]
    With R = 1 and D = q this becomes the expression below.
    """
    denom = 2 * (q - 1) ** (-n) + 2 * q ** (-n) + 2 * (q + 1) ** (-n)
    return 10.0 * math.log10(1.0 / denom)


def sample_in_hexagon(m, rng):
    """m random points uniformly distributed inside a pointy-top hexagon of circumradius 1 (rejection sampling)."""
    pts = np.empty((0, 2))
    while pts.shape[0] < m:                               # keep drawing until enough points are accepted
        x = rng.uniform(-math.sqrt(3) / 2, math.sqrt(3) / 2, 2 * m)    # bounding box in x
        y = rng.uniform(-1.0, 1.0, 2 * m)                              # bounding box in y
        inside = np.abs(y) + np.abs(x) / math.sqrt(3) <= 1.0           # hexagon inequality
        pts = np.vstack([pts, np.column_stack([x[inside], y[inside]])])
    return pts[:m]


def sir_outage_mc(i, j, n, sigma_db, thresholds_db, m, rng):
    """
    Monte-Carlo of the downlink SIR for a user at a random position in the centre cell.
    Interferers = base stations of the six first-tier co-channel cells (omni, equal power).
    Returns outage probabilities for every threshold, with
        (a) path loss + log-normal shadowing                -> 'large-scale outage' (design metric)
        (b) path loss + shadowing + independent Rayleigh    -> 'with fast fading'
    """
    user = sample_in_hexagon(m, rng)                                       # user positions (R = 1)
    bs = np.array(hg.first_tier_cochannel(i, j, 1.0))                      # (6, 2) interferer positions
    d0 = np.maximum(np.hypot(user[:, 0], user[:, 1]), 0.05)                # distance to own base station
    dk = np.maximum(np.hypot(user[:, None, 0] - bs[None, :, 0],
                             user[:, None, 1] - bs[None, :, 1]), 0.05)     # (m, 6) distances to interferers
    sh = 10.0 ** (rng.normal(0, sigma_db, (m, 7)) / 10.0)                  # 7 independent shadowing gains
    s_ls = d0 ** (-n) * sh[:, 0]                                           # wanted power (path loss + shadow)
    i_ls = (dk ** (-n) * sh[:, 1:]).sum(axis=1)                            # total interference power
    sir_ls = 10 * np.log10(s_ls / i_ls)                                    # SIR (dB), large-scale only
    ray = rng.exponential(1.0, (m, 7))                                     # Rayleigh power gains |h|^2 ~ Exp(1)
    sir_ff = 10 * np.log10((s_ls * ray[:, 0]) / ((dk ** (-n) * sh[:, 1:] * ray[:, 1:]).sum(axis=1)))
    return {"outage_ls": {t: float(np.mean(sir_ls < t)) for t in thresholds_db},
            "outage_ff": {t: float(np.mean(sir_ff < t)) for t in thresholds_db},
            "median_sir_db": float(np.median(sir_ls)), "p10_sir_db": float(np.percentile(sir_ls, 10))}


# ------------------------------------------------------------------ the study
def evaluate(cfg, cfg2, bc_hz, rng):
    """Build the full design-space table: one row per cluster size."""
    rows = []
    thr_all = sorted(set(cfg["sensitivity_thresholds_db"]) | {cfg["sir_threshold_db"]})
    for (n_clu, i, j) in hg.valid_cluster_sizes(3, cfg["cluster_candidates_max_n"]):
        base = e2.design_row(n_clu, cfg2)                                  # Expt 2 numbers (capacity)
        q = math.sqrt(3 * n_clu)                                           # Expt 1: D/R
        c = base["channels_per_cell"]
        hop_band = c * settings.EXP1["simplex_channel_hz"]                  # C hop channels x 200 kHz (one direction)
        row = dict(base)
        row.update({"i": i, "j": j, "q": q, "hop_band_hz": hop_band,
                    "diversity_order": max(1, int(hop_band // bc_hz)),    # independent fading sub-bands
                    "pg_db": 10 * math.log10(c) if c > 0 else 0.0,         # Expt 5: processing gain
                    "jam_hit_prob": 1.0 / c,                               # single-tone jammer hit probability
                    "jam_ber": float(e5.ber_fhss_jam(cfg["ebn0_db"], c, 1, cfg["jsr_db"], True)),
                    "sir": {}})
        for n in cfg["pathloss_exps"]:                                     # n = 3 and n = 4
            mc = sir_outage_mc(i, j, n, cfg["shadow_sigma_db"], thr_all, cfg["mc_samples"], rng)
            row["sir"][str(n)] = {"simple_db": sir_simple_db(q, n), "worst_db": sir_worst_case_db(q, n), **mc}
        rows.append(row)
    return rows


def pick_best(rows, n_exp, thr, target):
    """Most users among the cluster sizes whose large-scale outage <= target; None if nothing qualifies."""
    ok = [r for r in rows if r["sir"][str(n_exp)]["outage_ls"][thr] <= target]
    return max(ok, key=lambda r: r["users_system"]) if ok else None


def decisions(rows, cfg):
    """Recommended N for every (path-loss exponent, threshold) pair = the sensitivity table."""
    table = []
    for n in cfg["pathloss_exps"]:
        for thr in sorted(set(cfg["sensitivity_thresholds_db"]) | {cfg["sir_threshold_db"]}):
            best = pick_best(rows, n, thr, cfg["outage_target"])
            table.append({"n": n, "threshold_db": thr,
                          "N": best["N"] if best else None,
                          "users_system": best["users_system"] if best else None,
                          "outage": best["sir"][str(n)]["outage_ls"][thr] if best else None})
    return table


def splitting_whatif(best, cfg2, factor):
    """Cell splitting on the chosen design: same N and channels per cell, factor^2 more cells."""
    if best is None:
        return None
    return {"N": best["N"], "cells_before": cfg2["n_cells"], "cells_after": cfg2["n_cells"] * factor ** 2,
            "users_before": best["users_system"], "users_after": best["users_system"] * factor ** 2,
            "power_reduction_db": {str(n): 10 * n * math.log10(factor) for n in settings.EXP1["split_pathloss_exp"]}}


# ------------------------------------------------------------------- plotting
def plot_capacity_vs_sir(rows, cfg, name):
    """Top: users of the whole system per N. Bottom: SIR of the cell-edge user per N versus the threshold."""
    ns = [r["N"] for r in rows]; x = np.arange(len(ns))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1]})
    b = a1.bar(x, [r["users_system"] / 1000 for r in rows], color=utils.PALETTE[0], width=0.6)
    a1.bar_label(b, fmt="%.0f k", padding=2, fontsize=8)
    a1.set_ylabel("System users (thousands)\nat Pb = 1 %"); a1.set_title("Capacity falls with N ...")
    for k, n in enumerate(cfg["pathloss_exps"]):                       # one line per path-loss exponent
        a2.plot(x, [r["sir"][str(n)]["worst_db"] for r in rows], "o-", color=utils.PALETTE[k],
                label=f"worst-case edge user, n = {n:g}")
    a2.axhline(cfg["sir_threshold_db"], color=utils.INK, linestyle="--", label=f"required SIR = {cfg['sir_threshold_db']:g} dB")
    a2.set_xticks(x); a2.set_xticklabels([str(n) for n in ns]); a2.set_xlabel("Cluster size N")
    a2.set_ylabel("Co-channel SIR (dB)"); a2.set_title("... while the interference margin grows with N"); a2.legend(fontsize=8)
    return utils.save_fig(fig, name)


def plot_design_space(rows, cfg, name):
    """Scatter: x = outage probability, y = system users. Feasible zone = left of the target line."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    thr = cfg["sir_threshold_db"]
    for ax, n in zip(axes, cfg["pathloss_exps"]):
        ox = [r["sir"][str(n)]["outage_ls"][thr] * 100 for r in rows]
        oy = [r["users_system"] / 1000 for r in rows]
        ax.axvspan(0, cfg["outage_target"] * 100, color=utils.PALETTE[2], alpha=0.12, label="feasible (outage <= target)")
        ax.plot(ox, oy, "-", color=utils.MUTED, linewidth=1)
        for r, xx, yy in zip(rows, ox, oy):
            ok = xx <= cfg["outage_target"] * 100
            ax.plot(xx, yy, "o", color=utils.PALETTE[2] if ok else utils.PALETTE[4], markersize=8, markeredgecolor="white")
            ax.annotate(f"N={r['N']}", (xx, yy), textcoords="offset points", xytext=(6, 4), fontsize=8)
        ax.set_xscale("symlog", linthresh=0.1); ax.set_xlim(0, 100)
        ax.set_xlabel(f"Outage probability P(SIR < {thr:g} dB)  [%]"); ax.set_title(f"Path-loss exponent n = {n:g}")
    axes[0].set_ylabel("System users (thousands)"); axes[0].legend(loc="center right", fontsize=8)
    fig.suptitle("Design space: capacity vs interference outage (green = feasible)", fontweight="bold")
    return utils.save_fig(fig, name)


def plot_outage_sensitivity(rows, cfg, name):
    """Outage against N for several SIR thresholds, one panel per path-loss exponent."""
    ns = [r["N"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, n in zip(axes, cfg["pathloss_exps"]):
        for k, thr in enumerate(sorted(set(cfg["sensitivity_thresholds_db"]) | {cfg["sir_threshold_db"]})):
            ax.plot(ns, [max(r["sir"][str(n)]["outage_ls"][thr] * 100, 1e-3) for r in rows], "o-",
                    color=utils.PALETTE[k], label=f"threshold {thr:g} dB")
        ax.axhline(cfg["outage_target"] * 100, color=utils.INK, linestyle="--", linewidth=1)
        ax.set_yscale("log"); ax.set_xlabel("Cluster size N"); ax.set_title(f"n = {n:g}")
    axes[0].set_ylabel("Outage (%)  [shadowing, sigma = 4 dB]"); axes[0].legend(fontsize=8)
    fig.suptitle("Outage vs cluster size for different SIR requirements (dashed = 10 % target)", fontweight="bold")
    return utils.save_fig(fig, name)


def plot_hopping(rows, cfg, name):
    """Processing gain and jam BER when the hop set equals the cell's channel allocation."""
    ns = [str(r["N"]) for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    b = axes[0].bar(ns, [r["pg_db"] for r in rows], color=utils.PALETTE[3], width=0.6)
    axes[0].bar_label(b, fmt="%.1f", padding=2, fontsize=8)
    axes[0].set_xlabel("Cluster size N"); axes[0].set_ylabel("Processing gain (dB)")
    axes[0].set_title("PG = 10 log10(C), C = channels per cell")
    axes[1].semilogy(ns, [r["jam_ber"] for r in rows], "o-", color=utils.PALETTE[4])
    axes[1].set_xlabel("Cluster size N"); axes[1].set_ylabel(f"BER under tone jammer (Eb/N0 = {cfg['ebn0_db']:g} dB)")
    axes[1].set_title(f"Jam resilience (JSR = {cfg['jsr_db']:g} dB, theory)")
    return utils.save_fig(fig, name)


def plot_splitting(split, name):
    """Before/after bars for the recommended design."""
    fig, ax = plt.subplots(figsize=(6, 4.2))
    b = ax.bar(["Before", "After splitting\n(R -> R/2)"], [split["users_before"] / 1000, split["users_after"] / 1000],
               color=[utils.PALETTE[0], utils.PALETTE[2]], width=0.5)
    ax.bar_label(b, fmt="%.0f k", padding=2)
    ax.set_ylabel("System users (thousands)")
    ax.set_title(f"Cell splitting on the N = {split['N']} design: {split['cells_before']} -> {split['cells_after']} cells")
    return utils.save_fig(fig, name)


# ------------------------------------------------------------------ main entry
def run(exp3_result, cfg=None, fast=False):
    """Run the integrated study; `exp3_result` supplies the coherence bandwidth."""
    cfg = dict(cfg or settings.PLANNER)
    if fast:
        cfg["mc_samples"] //= 10
    cfg2 = settings.EXP2
    utils.apply_style()
    rng = np.random.default_rng(settings.RANDOM_SEED + 99)
    bc = exp3_result["partB"]["bc_50_hz"]
    rows = evaluate(cfg, cfg2, bc, rng)
    dec = decisions(rows, cfg)
    n_main = cfg["pathloss_exps"][0]
    best = pick_best(rows, n_main, cfg["sir_threshold_db"], cfg["outage_target"])
    split = splitting_whatif(best, cfg2, settings.EXP1["split_factor"])
    figs = [plot_capacity_vs_sir(rows, cfg, "planner_capacity_vs_sir"),
            plot_design_space(rows, cfg, "planner_design_space"),
            plot_outage_sensitivity(rows, cfg, "planner_outage_sensitivity"),
            plot_hopping(rows, cfg, "planner_hopping_resilience")]
    if split:
        figs.append(plot_splitting(split, "planner_cell_splitting_gain"))
    thr = cfg["sir_threshold_db"]
    utils.save_table(
        [[r["N"], f"({r['i']},{r['j']})", r["channels_per_cell"], round(r["q"], 2), r["users_system"]] +
         [round(r["sir"][str(n)]["worst_db"], 1) for n in cfg["pathloss_exps"]] +
         [round(r["sir"][str(n)]["outage_ls"][thr] * 100, 2) for n in cfg["pathloss_exps"]] +
         [round(r["pg_db"], 1), r["diversity_order"], f"{r['jam_ber']:.3e}"] for r in rows],
        ["N", "(i,j)", "Channels/cell C", "D/R"] + ["System users"] +
        [f"Worst-case SIR n={n:g} (dB)" for n in cfg["pathloss_exps"]] +
        [f"Outage n={n:g} (%)" for n in cfg["pathloss_exps"]] + ["PG (dB)", "Diversity order", "Jam BER"],
        "planner_design_table")
    utils.save_table([[d["n"], d["threshold_db"], d["N"], d["users_system"], None if d["outage"] is None else round(d["outage"] * 100, 2)] for d in dec],
                     ["n", "SIR threshold (dB)", "Recommended N", "System users", "Outage (%)"], "planner_decisions")
    return {"rows": rows, "decisions": dec, "best": best, "splitting": split, "figures": figs, "config": cfg, "bc_hz": bc}


if __name__ == "__main__":
    from wcn import exp3_multipath as e3
    out = run(e3.run(), fast=True)
    for r in out["rows"]:
        print(r["N"], r["channels_per_cell"], r["users_system"], {n: (round(v["worst_db"], 1), round(v["outage_ls"][9.0], 3), round(v["outage_ff"][9.0], 3)) for n, v in r["sir"].items()},
              round(r["pg_db"], 1), r["diversity_order"], f"{r['jam_ber']:.3e}")
    print(out["decisions"])
