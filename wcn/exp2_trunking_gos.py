# =============================================================================
# FILE        : wcn/exp2_trunking_gos.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Experiment 2 - Trunking and Grade of Service (GoS) fundamentals.
#               Uses the Erlang-B formula (blocked-calls-cleared, M/M/C/C queue).
# WHAT IT DOES: Problem of the handout: 84 cells, 300 voice channels, 0.04 Erlang/user,
#               blocking Pb = 1 %.  For cluster size N = 4, 12 and 13 it computes
#                 * channels per cell        C = floor(300 / N)
#                 * max offered traffic/cell A  such that  ErlangB(A, C) = 1 %
#                 * traffic actually carried per cell  A * (1 - Pb)
#                 * users per cell   = A / 0.04   and users in the whole system (84 cells)
#               It ALSO validates the formula with an independent event-driven
#               Monte-Carlo simulation of Poisson calls, and draws the figures.
# LAST STEP   : exp1 showed that a cluster of N cells splits the spectrum N ways.
# NEXT STEP   : wcn/integrated_planner.py re-uses erlang_b() and capacity_at_gos() to
#               compare ALL valid cluster sizes together with interference and hopping.
# KEY FORMULA : Erlang-B  B(A, C) = (A^C / C!) / sum_{k=0..C} (A^k / k!)
#               computed with the stable recursion  B(A,0)=1 ;
#               B(A,k) = A*B(A,k-1) / (k + A*B(A,k-1)).
# =============================================================================

import heapq                                  # heapq: priority queue for call departure times
import math                                   # math: floor
import numpy as np                            # numpy: random numbers + arrays
import matplotlib.pyplot as plt               # pyplot: drawing

from config import settings                   # parameters of Experiment 2
from wcn import utils                         # saving helpers + palette


# ---------------------------------------------------------------- Erlang-B core
def erlang_b(a, c):
    """Blocking probability for offered traffic `a` (Erlang) on `c` channels (recursion form)."""
    b = 1.0                                   # B(A, 0) = 1: with zero channels every call is blocked
    for k in range(1, int(c) + 1):            # add channels one by one
        b = a * b / (k + a * b)               # Erlang-B recursion (numerically stable, no factorials)
    return b


def capacity_at_gos(c, pb, tol=1e-10):
    """
    Largest offered traffic A (Erlang) that `c` channels can carry with blocking <= pb.
    Erlang-B increases monotonically with A, so a bisection search is enough.
    """
    lo, hi = 0.0, float(c) * 3.0 + 10.0       # A is certainly between 0 and a little above 3*C
    while hi - lo > tol:                      # halve the interval until it is tiny
        mid = 0.5 * (lo + hi)                 # middle point
        if erlang_b(mid, c) > pb:             # too much blocking -> A must be smaller
            hi = mid
        else:                                 # blocking acceptable -> A can be larger
            lo = mid
    return lo


def design_row(n, cfg):
    """All Experiment-2 numbers for one cluster size N."""
    c = cfg["total_channels"] // n                         # channels per cell (whole channels only)
    a = capacity_at_gos(c, cfg["blocking_prob"])           # max OFFERED traffic per cell at Pb
    carried = a * (1.0 - cfg["blocking_prob"])             # traffic actually CARRIED = A (1 - Pb)
    users_cell = int(math.floor(a / cfg["traffic_per_user_erl"]))   # users one cell can support
    return {"N": n, "channels_per_cell": c, "unused_channels": cfg["total_channels"] - c * n,
            "offered_erl_per_cell": a, "carried_erl_per_cell": carried,
            "trunking_efficiency": carried / c,               # carried Erlang per channel (utilisation)
            "users_per_cell": users_cell,
            "users_system": users_cell * cfg["n_cells"],       # all 84 cells
            "carried_erl_system": carried * cfg["n_cells"],
            "full_clusters_in_area": cfg["n_cells"] / n}       # shows when 84 is not a multiple of N


# --------------------------------------------------------- Monte-Carlo validation
def simulate_blocking(a, c, n_calls, rng):
    """
    Event-driven simulation of blocked-calls-cleared:
    * calls arrive as a Poisson process with rate lambda = A (mean holding time = 1)
    * each admitted call holds one channel for an Exp(1) time
    * a call that finds all C channels busy is BLOCKED and lost (not retried)
    Returns the measured fraction of blocked calls.
    """
    inter = rng.exponential(1.0 / a, size=n_calls)         # exponential inter-arrival times
    arrivals = np.cumsum(inter)                            # absolute arrival instants
    holds = rng.exponential(1.0, size=n_calls)             # holding time of each call
    busy = []                                              # min-heap of departure times of calls in progress
    blocked = 0                                            # counter of lost calls
    for t, h in zip(arrivals, holds):                      # process calls in time order
        while busy and busy[0] <= t:                       # free every channel whose call has ended
            heapq.heappop(busy)
        if len(busy) >= c:                                 # all channels occupied -> call blocked
            blocked += 1
        else:                                              # otherwise take a channel until t + h
            heapq.heappush(busy, t + h)
    return blocked / n_calls                               # measured blocking probability


# ------------------------------------------------------------------- plotting
def plot_blocking_curves(rows, pb, name):
    """Blocking probability against offered traffic for each channel count, with the 1 % line."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for k, r in enumerate(rows):                           # one curve per cluster size
        c = r["channels_per_cell"]
        a_grid = np.linspace(0.5, r["offered_erl_per_cell"] * 1.6, 200)   # offered-traffic axis
        ax.plot(a_grid, [erlang_b(a, c) for a in a_grid], color=utils.PALETTE[k],
                label=f"N = {r['N']}  (C = {c} channels)")              # Erlang-B curve
        ax.plot(r["offered_erl_per_cell"], pb, "o", color=utils.PALETTE[k], markersize=7,
                markeredgecolor="white")                    # marker at the design point
    ax.axhline(pb, color=utils.MUTED, linestyle="--", linewidth=1)      # target GoS line
    ax.set_yscale("log"); ax.set_ylim(1e-4, 1)             # log axis shows the 1 % region clearly
    ax.set_xlabel("Offered traffic per cell A (Erlang)"); ax.set_ylabel("Blocking probability Pb")
    ax.set_title("Erlang-B: blocking vs offered traffic (dots = design point at Pb = 1 %)")
    ax.legend(loc="lower right")
    return utils.save_fig(fig, name)


def plot_capacity_vs_channels(pb, highlight, name):
    """Capacity A(C) at the GoS and trunking efficiency A(1-Pb)/C against C (the 'trunking gain')."""
    cs = np.arange(1, 101)                                  # 1 ... 100 channels
    caps = np.array([capacity_at_gos(c, pb) for c in cs])   # offered traffic that meets the GoS
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(cs, caps * (1 - pb) / cs * 100, color=utils.PALETTE[0], linewidth=2)   # efficiency in %
    for k, c in enumerate(highlight):                       # mark the channel counts of the lab
        ax.plot(c, capacity_at_gos(c, pb) * (1 - pb) / c * 100, "o", color=utils.PALETTE[1 + k % 4],
                markersize=8, markeredgecolor="white", label=f"C = {c}")
    ax.set_xlabel("Channels per cell C"); ax.set_ylabel("Trunking efficiency (% of channel time used)")
    ax.set_title("Bigger channel pools are used more efficiently at the same 1 % blocking")
    ax.legend(loc="lower right")
    return utils.save_fig(fig, name)


def plot_users_bar(rows, name):
    """Bars: users per cell and users in the whole system for N = 4, 12, 13."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    ns = [str(r["N"]) for r in rows]                        # x labels = cluster sizes
    b1 = axes[0].bar(ns, [r["offered_erl_per_cell"] for r in rows], color=utils.PALETTE[0], width=0.5)
    axes[0].bar_label(b1, fmt="%.1f", padding=2)            # value labels on top
    axes[0].set_title("Max traffic per cell at Pb = 1 %"); axes[0].set_xlabel("Cluster size N")
    axes[0].set_ylabel("Offered traffic (Erlang)")
    b2 = axes[1].bar(ns, [r["users_system"] for r in rows], color=utils.PALETTE[1], width=0.5)
    axes[1].bar_label(b2, fmt="%d", padding=2)
    axes[1].set_title("Users served by the 84-cell system"); axes[1].set_xlabel("Cluster size N")
    axes[1].set_ylabel("Users")
    return utils.save_fig(fig, name)


def plot_mc_validation(rows, mc, pb, name):
    """Bars comparing the Monte-Carlo measured blocking with the 1 % Erlang-B target."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ns = [f"N = {r['N']}\n(C = {r['channels_per_cell']})" for r in rows]
    bars = ax.bar(ns, [m * 100 for m in mc], color=utils.PALETTE[2], width=0.5)   # measured %
    ax.bar_label(bars, fmt="%.2f %%", padding=2)
    ax.axhline(pb * 100, color=utils.PALETTE[4], linestyle="--", label="Erlang-B target 1 %")
    ax.set_ylabel("Measured blocking (%)"); ax.set_ylim(0, 1.6)
    ax.set_title("Monte-Carlo simulation confirms the analytical Erlang-B design point")
    ax.legend()
    return utils.save_fig(fig, name)


def make_inference(rows):
    """Plain-English conclusion generated from the numbers (so it can never disagree with them)."""
    best = max(rows, key=lambda r: r["users_system"])       # cluster size with most users
    worst = min(rows, key=lambda r: r["users_system"])      # cluster size with fewest users
    ratio = best["users_system"] / worst["users_system"]    # capacity ratio
    lines = [
        f"N = {best['N']} serves the most users ({best['users_system']:,}) and N = {worst['N']} the fewest "
        f"({worst['users_system']:,}); the capacity ratio is {ratio:.2f}x.",
        "Capacity falls as N grows because each cell receives only 300/N channels: a smaller reuse "
        "cluster gives each cell more channels and therefore more Erlangs.",
        "Capacity does NOT fall in proportion to the channel count: trunking efficiency improves with "
        f"pool size ({rows[0]['trunking_efficiency']*100:.1f} % at C = {rows[0]['channels_per_cell']} versus "
        f"{rows[-1]['trunking_efficiency']*100:.1f} % at C = {rows[-1]['channels_per_cell']}).",
        "The price of a small N is co-channel interference (D/R = sqrt(3N) shrinks) - quantified by the "
        "integrated planner.",
        "N = 13 leaves 1 channel unused (300 = 13 x 23 + 1) and 84 cells are not a whole number of "
        "13-cell clusters; the textbook calculation assigns 23 channels to every cell and ignores this.",
    ]
    return lines


# ------------------------------------------------------------------ main entry
def run(cfg=None, mc_calls=None):
    """Run Experiment 2 and return the dictionary of results."""
    cfg = cfg or settings.EXP2
    mc_calls = mc_calls or cfg["mc_calls"]
    utils.apply_style()
    rows = [design_row(n, cfg) for n in cfg["cluster_sizes"]]          # N = 4, 12, 13
    rng = np.random.default_rng(settings.RANDOM_SEED)                   # reproducible random numbers
    mc = [simulate_blocking(r["offered_erl_per_cell"], r["channels_per_cell"], mc_calls, rng)
          for r in rows]                                                # simulate each design point
    for r, m in zip(rows, mc):
        r["mc_blocking"] = m                                            # store measured blocking
    figs = [plot_blocking_curves(rows, cfg["blocking_prob"], "exp2_erlang_b_curves"),
            plot_capacity_vs_channels(cfg["blocking_prob"], [r["channels_per_cell"] for r in rows],
                                      "exp2_trunking_efficiency"),
            plot_users_bar(rows, "exp2_users_per_system"),
            plot_mc_validation(rows, mc, cfg["blocking_prob"], "exp2_monte_carlo_validation")]
    utils.save_table(
        [[r["N"], r["channels_per_cell"], round(r["offered_erl_per_cell"], 3),
          round(r["carried_erl_per_cell"], 3), round(r["trunking_efficiency"], 4),
          r["users_per_cell"], r["users_system"], round(r["mc_blocking"], 5)] for r in rows],
        ["N", "Channels per cell C", "Max offered traffic per cell (Erl)", "Max carried traffic per cell (Erl)",
         "Trunking efficiency", "Users per cell", "Users in 84-cell system", "Monte-Carlo blocking"],
        "exp2_trunking_table")
    return {"rows": rows, "inference": make_inference(rows), "figures": figs, "config": cfg}


if __name__ == "__main__":
    out = run()
    for r in out["rows"]:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    print("\n".join(out["inference"]))
