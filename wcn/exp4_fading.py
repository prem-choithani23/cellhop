# =============================================================================
# FILE        : wcn/exp4_fading.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Experiment 4 - Large-scale and small-scale fading, and the effect of
#               distance and mobility (Doppler).
# WHAT IT DOES: Part A  (10 positions x 100 samples)
#                 1. average received power from the Log-Distance path-loss model
#                       Pr(d) = P0 - 10 n log10(d / d0)           [dBm]
#                 2. adds log-normal shadowing X ~ N(0, sigma^2)  (large-scale fading, dB domain)
#                 3. adds Rayleigh small-scale fading 10log10(|h|^2), h ~ CN(0,1)
#                 4. prints the table and draws the three graphs of the handout
#               Part B (mobility)
#                 wavelength, maximum Doppler shift fd = v/lambda, Doppler spread (2 fd),
#                 coherence time Tc ~ 0.423/fd, a TIME-VARYING Rayleigh signal
#                 (sum-of-sinusoids / Clarke model) and Doppler-vs-velocity.
#               EXTRA validation: autocorrelation vs Bessel J0(2 pi fd tau) and the measured
#               level-crossing rate vs theory, proving the generator is statistically correct.
# LAST STEP   : exp3 explained delay spread (frequency selectivity); here we study
#               time selectivity (Doppler) and distance dependence.
# NEXT STEP   : wcn/exp5_fhss.py sends BPSK over AWGN/jamming and compares with the
#               Rayleigh-fading BER curve produced from this fading model.
# =============================================================================

import numpy as np                            # numpy: arrays and random numbers
import matplotlib.pyplot as plt               # pyplot: drawing
from scipy.special import j0                  # j0: Bessel function used in the theory of fading

from config import settings                   # EXP4 parameters
from wcn import utils                         # saving helpers

C_LIGHT = 299_792_458.0                       # speed of light in m/s


# ----------------------------------------------------------------- Part A models
def log_distance_power(d, p0_dbm, d0, n):
    """Average received power (dBm) at distance d using the Log-Distance Path Loss model."""
    return p0_dbm - 10.0 * n * np.log10(np.asarray(d, float) / d0)


def rayleigh_power_db(rng, size):
    """
    Rayleigh small-scale fading expressed as a power gain in dB.
    h = (X + jY)/sqrt(2) with X, Y ~ N(0,1)  ->  E[|h|^2] = 1 and |h| is Rayleigh distributed.
    """
    h = (rng.standard_normal(size) + 1j * rng.standard_normal(size)) / np.sqrt(2.0)   # complex Gaussian
    return 10.0 * np.log10(np.abs(h) ** 2)                                           # |h|^2 in dB


def partA(cfg, rng):
    """Simulate Part A and return the table plus the raw arrays for plotting."""
    d = np.geomspace(cfg["d_min_m"], cfg["d_max_m"], cfg["n_positions"])   # 10 distances (log-spaced)
    avg = log_distance_power(d, cfg["p0_dbm"], cfg["d0_m"], cfg["pathloss_exp"])   # large-scale mean
    shadow = rng.normal(0.0, cfg["shadow_sigma_db"], size=d.size)          # one shadowing draw per position
    with_shadow = avg + shadow                                             # + large-scale fading
    fad = rayleigh_power_db(rng, (d.size, cfg["samples_per_position"]))    # 100 Rayleigh samples / position
    final = with_shadow[:, None] + fad                                     # + small-scale fading
    rows = []                                                              # table rows
    for k in range(d.size):
        rows.append({"pos": k + 1, "d_m": float(d[k]), "avg_dbm": float(avg[k]),
                     "shadow_db": float(shadow[k]), "shadowed_dbm": float(with_shadow[k]),
                     "final_mean_dbm": float(final[k].mean()), "final_min_dbm": float(final[k].min()),
                     "final_max_dbm": float(final[k].max()), "final_std_db": float(final[k].std())})
    # estimate the path-loss exponent back from the shadowed data (should be close to the input n)
    slope = np.polyfit(10 * np.log10(d / cfg["d0_m"]), with_shadow, 1)[0]
    return {"d": d, "avg": avg, "shadowed": with_shadow, "final": final, "rows": rows,
            "n_estimated": float(-slope),
            "rayleigh_mean_db": float(fad.mean()),            # theory: -2.51 dB (Euler constant)
            "rayleigh_std_db": float(fad.std())}              # theory: 5.57 dB


def plot_partA(res, cfg):
    """Three graphs of Part A (average / +shadowing / +shadowing+Rayleigh) in one figure and singly."""
    d = res["d"]
    # ---- single combined figure that shows the 3 curves together (easy to compare)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.semilogx(d, res["avg"], "-", color=utils.INK, linewidth=2, label="Average (path loss only)")
    ax.semilogx(d, res["shadowed"], "o-", color=utils.PALETTE[1], linewidth=1.5, markersize=7,
                label=f"+ log-normal shadowing (sigma = {cfg['shadow_sigma_db']:g} dB)")
    for k in range(d.size):                                   # all 100 faded samples per position
        ax.semilogx(np.full(res["final"].shape[1], d[k]), res["final"][k], ".", color=utils.PALETTE[0],
                    alpha=0.25, markersize=4, label="+ Rayleigh fading (100 samples/position)" if k == 0 else None)
    ax.set_xlabel("Distance (m, log axis)"); ax.set_ylabel("Received power (dBm)")
    ax.set_title("Received power vs distance: smooth trend = large-scale, scatter = small-scale")
    ax.legend(loc="lower left")
    p1 = utils.save_fig(fig, "exp4A_received_power_combined")
    # ---- three separate graphs exactly as the handout lists them
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), sharey=True)
    axes[0].semilogx(d, res["avg"], "o-", color=utils.INK); axes[0].set_title("1. Average received power")
    axes[1].semilogx(d, res["shadowed"], "o-", color=utils.PALETTE[1]); axes[1].set_title("2. With shadowing")
    axes[2].semilogx(d, res["final"].mean(axis=1), "o-", color=utils.PALETTE[0])
    axes[2].semilogx(np.repeat(d, res["final"].shape[1]), res["final"].ravel(), ".", color=utils.PALETTE[0],
                     alpha=0.15, markersize=3)
    axes[2].set_title("3. With shadowing + Rayleigh fading")
    for ax in axes: ax.set_xlabel("Distance (m)")
    axes[0].set_ylabel("Received power (dBm)")
    p2 = utils.save_fig(fig, "exp4A_three_graphs")
    return [p1, p2]


# ----------------------------------------------------------------- Part B models
def mobility_parameters(fc_hz, v_mps):
    """Wavelength, maximum Doppler shift, Doppler spread and coherence time for a moving receiver."""
    lam = C_LIGHT / fc_hz                         # wavelength = c / fc
    fd = v_mps / lam                              # maximum Doppler shift = v / lambda
    return {"wavelength_m": lam, "fd_hz": fd,
            "doppler_spread_hz": 2.0 * fd,        # Doppler spectrum spans -fd ... +fd -> width 2 fd
            "tc_s": 0.423 / fd,                   # Rappaport: Tc ~ 9/(16 pi fd) = 0.423/fd
            "tc_simple_s": 1.0 / fd}              # cruder rule Tc ~ 1/fd


def clarke_rayleigh(fd, t, n_osc, rng):
    """
    Time-varying Rayleigh fading h(t) by the sum-of-sinusoids (Clarke / Jakes) model:
        h(t) = (1/sqrt(M)) * sum_m exp( j (2 pi fd cos(alpha_m) t + phi_m) )
    alpha_m = random angle of arrival of scattered wave m, phi_m = random phase.
    For large M this tends to a complex Gaussian process with Doppler spectrum 1/sqrt(1-(f/fd)^2).
    `t` may be a 1-D time vector; the output has the same length.
    """
    alpha = rng.uniform(0.0, 2.0 * np.pi, n_osc)               # random arrival angles
    phi = rng.uniform(0.0, 2.0 * np.pi, n_osc)                 # random phases
    doppler = fd * np.cos(alpha)                               # Doppler shift of each wave (Hz)
    phase = 2.0 * np.pi * np.outer(t, doppler) + phi           # (time x oscillator) phase matrix
    return np.exp(1j * phase).sum(axis=1) / np.sqrt(n_osc)     # sum all waves, normalise to unit power


def partB(cfg, rng):
    """Simulate Part B: large-scale picture, time-varying fading at one distance, Doppler vs velocity."""
    mob = mobility_parameters(cfg["carrier_hz"], cfg["velocity_mps"])
    # large-scale data at the 10 positions (path loss + shadowing)
    d = np.geomspace(cfg["d_min_m"], cfg["d_max_m"], cfg["n_positions"])
    avg = log_distance_power(d, cfg["p0_dbm"], cfg["d0_m"], cfg["pathloss_exp"])
    shadowed = avg + rng.normal(0.0, cfg["shadow_sigma_db"], size=d.size)
    # time-varying fading at the selected distance
    k_sel = int(np.argmin(np.abs(d - cfg["selected_distance_m"])))       # nearest simulated position
    t = np.arange(cfg["n_time_samples"]) / cfg["sample_rate_hz"]         # time axis in seconds
    h = clarke_rayleigh(mob["fd_hz"], t, cfg["n_sinusoids"], rng)        # complex fading gain
    fading_db = 10.0 * np.log10(np.abs(h) ** 2)                          # small-scale gain (dB)
    p_time = shadowed[k_sel] + fading_db                                 # received power vs time
    # Doppler vs velocity
    v = np.linspace(0.0, 50.0, 101)                                      # 0 ... 50 m/s
    fd_v = v * cfg["carrier_hz"] / C_LIGHT                               # fd = v fc / c
    # validation: autocorrelation & level crossing rate averaged over many realisations
    n_real = cfg["n_realisations"]
    lags = np.arange(0, 120)                                             # lags in samples
    acc = np.zeros(lags.size); crossings = 0; duration = 0.0
    rho = 1.0                                                            # threshold = RMS level (0 dB)
    for _ in range(n_real):
        hh = clarke_rayleigh(mob["fd_hz"], t, cfg["n_sinusoids"], rng)
        acc += np.array([np.mean(hh[:hh.size - L] * np.conj(hh[L:])).real for L in lags])   # Re E[h(t) h*(t+L)]
        env = np.abs(hh)                                                  # envelope r(t)
        crossings += np.sum((env[:-1] > rho) & (env[1:] <= rho))          # downward crossings of rho
        duration += t[-1]
    acf = acc / n_real                                                    # estimated autocorrelation
    lcr_meas = crossings / duration                                       # crossings per second
    lcr_theory = np.sqrt(2.0 * np.pi) * mob["fd_hz"] * rho * np.exp(-rho ** 2)   # Rayleigh LCR formula
    return {"mob": mob, "d": d, "avg": avg, "shadowed": shadowed, "k_sel": k_sel, "t": t,
            "fading_db": fading_db, "p_time": p_time, "v": v, "fd_v": fd_v,
            "lags_s": lags / cfg["sample_rate_hz"], "acf": acf,
            "lcr_meas": float(lcr_meas), "lcr_theory": float(lcr_theory),
            "fade_depth_db": float(fading_db.min()), "mean_gain_db": float(fading_db.mean())}


def plot_partB(res, cfg):
    """The three graphs of Part B + the validation plot."""
    figs = []
    # Graph 1: large-scale fading
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.semilogx(res["d"], res["avg"], "-", color=utils.INK, linewidth=2, label="Path loss")
    ax.semilogx(res["d"], res["shadowed"], "o-", color=utils.PALETTE[1], label="Path loss + shadowing")
    ax.set_xlabel("Distance (m)"); ax.set_ylabel("Received power (dBm)")
    ax.set_title("Graph 1 - Large-scale fading"); ax.legend()
    figs.append(utils.save_fig(fig, "exp4B_graph1_large_scale"))
    # Graph 2: small-scale fading vs time
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(np.arange(res["t"].size), res["p_time"], color=utils.PALETTE[0], linewidth=1.1)
    ax.axhline(res["shadowed"][res["k_sel"]], color=utils.INK, linestyle="--", linewidth=1,
               label=f"local mean at d = {res['d'][res['k_sel']]:.0f} m")
    ax.set_xlabel("Sample number (1000 samples at 2 kHz = 0.5 s)"); ax.set_ylabel("Received power (dBm)")
    ax.set_title(f"Graph 2 - Small-scale fading at v = {cfg['velocity_mps']:g} m/s "
                 f"(fd = {res['mob']['fd_hz']:.0f} Hz, Tc = {res['mob']['tc_s'] * 1e3:.1f} ms)"); ax.legend()
    figs.append(utils.save_fig(fig, "exp4B_graph2_small_scale_time"))
    # Graph 3: Doppler vs velocity
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(res["v"], res["fd_v"], color=utils.PALETTE[0], linewidth=2)
    ax.plot(cfg["velocity_mps"], res["mob"]["fd_hz"], "o", color=utils.PALETTE[1], markersize=9,
            label=f"selected v = {cfg['velocity_mps']:g} m/s -> {res['mob']['fd_hz']:.0f} Hz")
    ax.set_xlabel("Mobile velocity (m/s)"); ax.set_ylabel("Maximum Doppler shift (Hz)")
    ax.set_title("Graph 3 - Effect of velocity on Doppler shift (fc = 900 MHz)"); ax.legend()
    figs.append(utils.save_fig(fig, "exp4B_graph3_doppler_vs_velocity"))
    # Validation: autocorrelation vs Bessel J0
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(res["lags_s"] * 1e3, res["acf"], color=utils.PALETTE[0], linewidth=2, label="Simulated Re{R(tau)}")
    ax.plot(res["lags_s"] * 1e3, j0(2 * np.pi * res["mob"]["fd_hz"] * res["lags_s"]), "--",
            color=utils.PALETTE[1], linewidth=2, label="Theory J0(2 pi fd tau)")
    ax.axvline(res["mob"]["tc_s"] * 1e3, color=utils.MUTED, linestyle=":", label="Coherence time Tc")
    ax.set_xlabel("Time lag tau (ms)"); ax.set_ylabel("Normalised autocorrelation")
    ax.set_title("Validation: the generated fading has the Clarke/Jakes autocorrelation"); ax.legend()
    figs.append(utils.save_fig(fig, "exp4B_validation_autocorrelation"))
    return figs


# ------------------------------------------------------------------ main entry
def run(cfg=None):
    """Run Experiment 4 (Part A and Part B) and return the dictionary of results."""
    cfg = cfg or settings.EXP4
    utils.apply_style()
    rng = np.random.default_rng(settings.RANDOM_SEED + 4)        # reproducible random stream for Expt 4
    a = partA(cfg, rng)
    b = partB(cfg, rng)
    figs = plot_partA(a, cfg) + plot_partB(b, cfg)
    utils.save_table([[r["pos"], round(r["d_m"], 1), round(r["avg_dbm"], 2), round(r["shadow_db"], 2),
                       round(r["shadowed_dbm"], 2), round(r["final_mean_dbm"], 2),
                       round(r["final_min_dbm"], 2), round(r["final_max_dbm"], 2)] for r in a["rows"]],
                     ["Position", "Distance (m)", "Average Pr (dBm)", "Shadowing (dB)", "Pr + shadowing (dBm)",
                      "Mean final Pr (dBm)", "Min final Pr (dBm)", "Max final Pr (dBm)"], "exp4A_table")
    return {"partA": a, "partB": b, "figures": figs}


if __name__ == "__main__":
    out = run()
    print(out["partB"]["mob"])
    print("LCR measured / theory:", out["partB"]["lcr_meas"], out["partB"]["lcr_theory"])
    print("n estimated", out["partA"]["n_estimated"], "rayleigh mean/std", out["partA"]["rayleigh_mean_db"], out["partA"]["rayleigh_std_db"])
