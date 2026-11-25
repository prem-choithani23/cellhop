# =============================================================================
# FILE        : wcn/exp3_multipath.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Experiment 3 - Multipath propagation: Power Delay Profile (PDP),
#               delay spread and coherence bandwidth.
# WHAT IT DOES: Part A (powers in dBm)
#                 * prints the multipath table, strongest / weakest ray,
#                   maximum excess delay and average received power
#                 * plots the PDP (received power vs excess delay)
#               Part B (powers in Watts)
#                 * mean excess delay   tau_bar = sum(P_i tau_i) / sum(P_i)
#                 * RMS delay spread    sigma   = sqrt( sum(P_i (tau_i - tau_bar)^2) / sum(P_i) )
#                 * coherence bandwidth Bc ~ 1/(5 sigma) (50 % correlation) and 1/(50 sigma) (90 %)
#               EXTRA (our project): compares Bc with real system bandwidths (GSM, IS-95,
#               WCDMA, LTE) to decide FLAT vs FREQUENCY-SELECTIVE fading. This Bc is later
#               used by the integrated planner to say whether hopping channels fade independently.
#               The PDP can be typed in by the user (--interactive) or loaded from a CSV.
# LAST STEP   : exp2 produced the capacity numbers (not needed here - independent module).
# NEXT STEP   : wcn/exp4_fading.py adds path loss, shadowing and Doppler on top of the same
#               idea that a signal arrives through many paths.
# =============================================================================

import csv                                    # csv: read a user supplied PDP file
import numpy as np                            # numpy: vector maths
import matplotlib.pyplot as plt               # pyplot: drawing

from config import settings                   # PDP defaults
from wcn import utils                         # unit conversions, saving helpers


# ------------------------------------------------------------------ input helpers
def load_pdp_csv(path):
    """Read a CSV with two columns: excess delay (ns), received power (dBm). Header row allowed."""
    delays, powers = [], []                   # lists that collect the numbers
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):            # go through every line
            try:
                delays.append(float(row[0])); powers.append(float(row[1]))   # numeric line
            except (ValueError, IndexError):
                continue                      # skip header / blank lines
    return np.array(delays), np.array(powers)


def prompt_pdp():
    """Interactive input exactly as the handout says: the user enters delay and power for each path."""
    n = int(input("Number of multipath components (>= 5 recommended): "))   # how many rays
    delays, powers = [], []
    for k in range(1, n + 1):                 # ask for each ray
        delays.append(float(input(f"  Path {k}: excess delay (ns) = ")))
        powers.append(float(input(f"  Path {k}: received power (dBm) = ")))
    return np.array(delays), np.array(powers)


# ---------------------------------------------------------------------- Part A
def pdp_analysis(delays_ns, powers_dbm):
    """Strongest / weakest path, maximum excess delay and average received power (Part A)."""
    order = np.argsort(delays_ns)             # sort rays by arrival time
    d = np.asarray(delays_ns, float)[order]   # sorted delays
    p = np.asarray(powers_dbm, float)[order]  # powers in the same order
    i_max, i_min = int(np.argmax(p)), int(np.argmin(p))      # indices of strongest / weakest ray
    p_lin_mw = utils.db_to_lin(p)             # dBm -> mW (linear) for a physically correct mean
    return {
        "delays_ns": d, "powers_dbm": p,
        "table": [[k + 1, float(d[k]), float(p[k])] for k in range(len(d))],   # path no., delay, power
        "strongest": {"path": i_max + 1, "delay_ns": float(d[i_max]), "power_dbm": float(p[i_max])},
        "weakest": {"path": i_min + 1, "delay_ns": float(d[i_min]), "power_dbm": float(p[i_min])},
        "max_excess_delay_ns": float(d.max() - d.min()),      # last arrival minus first arrival
        "avg_power_dbm_arithmetic": float(p.mean()),          # simple mean of the dBm numbers
        "avg_power_dbm_linear": float(utils.lin_to_db(p_lin_mw.mean())),   # mean in mW, back to dBm
    }


# ---------------------------------------------------------------------- Part B
def delay_spread_analysis(delays_ns, powers_w):
    """Mean excess delay, RMS delay spread and coherence bandwidth from a linear-power PDP."""
    tau = np.asarray(delays_ns, float) * 1e-9             # ns -> seconds
    p = np.asarray(powers_w, float)                       # linear power in Watts
    p_tot = p.sum()                                       # sum of P_i (normaliser)
    tau_mean = (p * tau).sum() / p_tot                    # first moment of the PDP
    tau_second = (p * tau ** 2).sum() / p_tot             # second moment of the PDP
    sigma = np.sqrt(tau_second - tau_mean ** 2)           # RMS delay spread (equals the textbook form)
    sigma_direct = np.sqrt((p * (tau - tau_mean) ** 2).sum() / p_tot)   # formula exactly as in handout
    return {"tau_mean_s": float(tau_mean), "sigma_s": float(sigma), "sigma_direct_s": float(sigma_direct),
            "bc_50_hz": float(1.0 / (5.0 * sigma)),       # coherence bandwidth, correlation >= 0.5
            "bc_90_hz": float(1.0 / (50.0 * sigma)),      # coherence bandwidth, correlation >= 0.9
            "total_power_w": float(p_tot)}


def classify_fading(bc_hz, sigma_s, systems):
    """Flat or frequency-selective for each system: flat if signal bandwidth << Bc  (use B < Bc)."""
    out = []
    for name, bw in systems.items():              # loop through GSM, IS-95, ...
        symbol_time = 1.0 / bw                    # approx. symbol duration = 1/bandwidth
        flat = (bw < bc_hz) and (sigma_s < 0.1 * symbol_time)   # both rules of thumb must agree
        out.append({"system": name, "bandwidth_hz": bw, "symbol_time_s": symbol_time,
                    "ratio_bw_over_bc": bw / bc_hz, "type": "flat" if flat else "frequency-selective"})
    return out


# ------------------------------------------------------------------- plotting
def plot_pdp_dbm(d, p, name):
    """Part A figure: stem plot of received power (dBm) versus excess delay (ns)."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ml, sl, bl = ax.stem(d, p, bottom=float(p.min()) - 6)   # stems start at a floor just below the weakest ray
    plt.setp(ml, color=utils.PALETTE[0], markersize=8); plt.setp(sl, color=utils.PALETTE[0])
    plt.setp(bl, color=utils.MUTED)
    for x, y in zip(d, p):                                  # label every ray with its power
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xlabel("Excess delay (ns)"); ax.set_ylabel("Received power (dBm)")
    ax.set_title("Power Delay Profile (Part A)")
    return utils.save_fig(fig, name)


def plot_pdp_linear(d, p_w, ds, name):
    """Part B figure: PDP in linear power with the mean excess delay and +/- RMS spread marked."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(d, p_w * 1e9, width=35, color=utils.PALETTE[0])   # bars: power in nW
    tm = ds["tau_mean_s"] * 1e9; sg = ds["sigma_s"] * 1e9    # convert marks to ns
    ax.axvline(tm, color=utils.PALETTE[1], linewidth=2, label=f"mean excess delay = {tm:.0f} ns")
    ax.axvspan(tm - sg, tm + sg, color=utils.PALETTE[1], alpha=0.15, label=f"RMS spread = {sg:.0f} ns")
    ax.set_xlabel("Excess delay (ns)"); ax.set_ylabel("Received power (nW)")
    ax.set_title("Power Delay Profile in linear scale (Part B)"); ax.legend()
    return utils.save_fig(fig, name)


def plot_bc_vs_systems(ds, classes, name):
    """Horizontal bars: system bandwidths against the coherence-bandwidth line."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    names = [c["system"] for c in classes]
    bws = [c["bandwidth_hz"] / 1e3 for c in classes]         # kHz
    colours = [utils.PALETTE[2] if c["type"] == "flat" else utils.PALETTE[4] for c in classes]
    ax.barh(names, bws, color=colours)                       # green = flat, red = selective
    ax.axvline(ds["bc_50_hz"] / 1e3, color=utils.INK, linestyle="--",
               label=f"Bc (0.5) = {ds['bc_50_hz'] / 1e3:.0f} kHz")
    ax.set_xscale("log"); ax.set_xlabel("Bandwidth (kHz, log scale)")
    ax.set_title("Which systems see flat fading?  (aqua = flat, red = frequency-selective)")
    ax.legend(loc="lower right")
    return utils.save_fig(fig, name)


# ------------------------------------------------------------------ main entry
def run(cfg=None, delays_ns=None, powers_dbm=None):
    """Run Experiment 3 (Part A + Part B + extras)."""
    cfg = cfg or settings.EXP3
    utils.apply_style()
    delays_ns = np.array(cfg["delays_ns"] if delays_ns is None else delays_ns, float)
    powers_dbm = np.array(cfg["powers_dbm"] if powers_dbm is None else powers_dbm, float)
    a = pdp_analysis(delays_ns, powers_dbm)                       # Part A numbers
    powers_w = utils.dbm_to_watt(a["powers_dbm"])                 # Part B input = same rays in Watts
    b = delay_spread_analysis(a["delays_ns"], powers_w)           # Part B numbers
    classes = classify_fading(b["bc_50_hz"], b["sigma_s"], cfg["systems_hz"])
    figs = [plot_pdp_dbm(a["delays_ns"], a["powers_dbm"], "exp3_pdp_dbm"),
            plot_pdp_linear(a["delays_ns"], powers_w, b, "exp3_pdp_linear"),
            plot_bc_vs_systems(b, classes, "exp3_coherence_bandwidth_vs_systems")]
    utils.save_table([[r[0], r[1], r[2], f"{pw:.4e}"] for r, pw in zip(a["table"], powers_w)],
                     ["Path", "Excess delay (ns)", "Received power (dBm)", "Linear power (W)"], "exp3_pdp_table")
    return {"partA": a, "partB": b, "powers_w": powers_w, "classes": classes, "figures": figs}


if __name__ == "__main__":
    out = run()
    print(out["partA"]["strongest"], out["partA"]["weakest"], out["partA"]["max_excess_delay_ns"])
    print(out["partB"])
