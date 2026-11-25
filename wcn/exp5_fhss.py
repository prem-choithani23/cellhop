# =============================================================================
# FILE        : wcn/exp5_fhss.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Experiment 5 - software-defined Frequency Hopping Spread Spectrum (FHSS)
#               transmitter, channel and receiver, with BER measurement.
# WHAT IT DOES: TRANSMITTER : random bits -> BPSK -> mixed with a carrier that hops among
#                             N channels following a PN sequence from an LFSR.
#               CHANNEL     : AWGN at a chosen Eb/N0 (0-12 dB) + single-tone or partial-band
#                             jammer placed on hopping channels (random phase each bit).
#               RECEIVER    : its own synchronised copy of the PN generator de-hops (multiplies
#                             by the same carrier), integrates over one bit, takes the sign.
#               OUTPUTS     : * 8-bit demo table (input bits, PN sequence, hop frequency, FHSS output)
#                             * BER vs Eb/N0 for: no jammer, fixed-frequency under jamming,
#                               FHSS under tone jamming, FHSS under partial-band jamming (+ theory)
#                             * processing gain PG = 10 log10(N) and BER vs N under a tone jammer
#                             * BER over Rayleigh fading (links to Expt 4) -> the 'fading penalty'
#                             * spectrum of FHSS vs plain BPSK (shows the spreading)
# LAST STEP   : exp4 modelled Rayleigh fading and Doppler (used here only for the fading BER curve).
# NEXT STEP   : wcn/integrated_planner.py sets the hop-set size N = channels per cell of each
#               cluster design and computes the resulting processing gain / jam resilience.
# SIMULATION NOTE: carriers are placed at INTEGER numbers of cycles per bit, so different hop
#               channels are exactly orthogonal over one bit - the same orthogonality that makes
#               a real FHSS receiver reject a tone on a channel it is not currently listening to.
# =============================================================================

import numpy as np                            # numpy: arrays, random numbers, FFT
import matplotlib.pyplot as plt               # pyplot: drawing
from scipy.signal import welch                # welch: power-spectral-density estimate

from config import settings                   # EXP5 parameters
from wcn import utils                         # Q-function, conversions, saving helpers

K0 = 2                                        # lowest hop channel = 2 cycles per bit (keeps carriers off DC)


# ------------------------------------------------------------------ PN generator
def lfsr_bits(degree, taps, seed, n_bits):
    """
    Fibonacci linear-feedback shift register (LFSR) - the PN sequence generator.
    degree : number of flip-flops   taps : polynomial exponents, e.g. [16,14,13,11]
    seed   : non-zero start state   returns an array of n_bits output bits (0/1).
    """
    if seed == 0:                             # the all-zero state would stay zero forever
        raise ValueError("LFSR seed must be non-zero")
    state = seed & ((1 << degree) - 1)        # keep only `degree` bits of the seed
    shifts = [degree - t for t in taps]       # tap exponent t  ->  bit position (degree - t)
    out = np.empty(n_bits, dtype=np.uint8)    # output buffer
    for k in range(n_bits):                   # one clock cycle per output bit
        out[k] = state & 1                    # output = least-significant bit
        fb = 0                                # feedback bit = XOR of the tapped bits
        for s in shifts:
            fb ^= (state >> s) & 1
        state = (state >> 1) | (fb << (degree - 1))   # shift right, insert feedback at the top
    return out


def lfsr_period(degree, taps, seed):
    """Count clock cycles until the state repeats (maximal-length LFSR gives 2^degree - 1)."""
    state0 = seed & ((1 << degree) - 1); state = state0
    shifts = [degree - t for t in taps]
    for count in range(1, (1 << degree) + 1):
        fb = 0
        for s in shifts:
            fb ^= (state >> s) & 1
        state = (state >> 1) | (fb << (degree - 1))
        if state == state0:
            return count
    return None


def hop_indices(n_hops, n_channels, degree, taps, seed):
    """
    Map the PN bit stream to channel numbers 0..N-1 by grouping log2(N) PN bits per hop.
    (N must be a power of two so that every channel is equally likely.)
    """
    m = int(np.log2(n_channels))              # PN bits needed per hop
    if 2 ** m != n_channels:
        raise ValueError("n_channels must be a power of two")
    period = (1 << degree) - 1                # period of a maximal LFSR
    base = lfsr_bits(degree, taps, seed, period)           # generate ONE period only (fast)
    stream = np.resize(base, n_hops * m)                   # repeat it as often as needed
    words = stream.reshape(n_hops, m)                      # one row of m bits per hop
    weights = 1 << np.arange(m - 1, -1, -1)                # binary weights  [2^(m-1) ... 1]
    return (words * weights).sum(axis=1).astype(int), stream


# ------------------------------------------------------------ transmitter / receiver
def carrier_table(n_channels, spb):
    """cos carriers: row k has (K0 + k) full cycles per bit period, sampled at `spb` samples per bit."""
    n = np.arange(spb)                                     # sample index inside one bit
    freqs = (K0 + np.arange(n_channels))[:, None]          # cycles per bit of each channel
    return np.cos(2.0 * np.pi * freqs * n[None, :] / spb)  # shape (N, spb)


def simulate_ber(ebn0_db, n_bits, n_channels, rng, hopping=True, jam_channels=(), jsr_db=6.0,
                 bits_per_hop=1, lfsr=None, chunk=20_000):
    """
    Full waveform simulation of the FHSS link; returns the measured bit error rate.
    hopping=False -> the carrier stays on channel 0 (plain fixed-frequency BPSK, for comparison).
    jam_channels  -> channels carrying a jamming tone (empty = no jammer).
    """
    lfsr = lfsr or {"degree": 16, "taps": [16, 14, 13, 11], "seed": 0xACE1}
    spb = 4 * (K0 + n_channels)                            # samples per bit (> 2 x highest carrier)
    table = carrier_table(n_channels, spb)                 # all carriers
    gamma = 10.0 ** (ebn0_db / 10.0)                       # Eb/N0 as a ratio
    sigma = np.sqrt(spb / (4.0 * gamma))                   # noise std/sample so that Eb/N0 is exact
    if hopping:                                            # PN-controlled hop sequence
        n_hops = int(np.ceil(n_bits / bits_per_hop))
        hops, _ = hop_indices(n_hops, n_channels, lfsr["degree"], lfsr["taps"], lfsr["seed"])
        hop_per_bit = np.repeat(hops, bits_per_hop)[:n_bits]   # slow hopping repeats a hop for L bits
    else:
        hop_per_bit = np.zeros(n_bits, dtype=int)          # fixed carrier = channel 0
    amp_each = np.sqrt(10.0 ** (jsr_db / 10.0) / max(len(jam_channels), 1))   # amplitude of each jam tone
    tone_idx = np.arange(spb)                              # sample index for jam tones
    errors = 0
    for start in range(0, n_bits, chunk):                  # process the bits in blocks (saves memory)
        m = min(chunk, n_bits - start)
        bits = rng.integers(0, 2, m)                       # TX: random data bits
        sym = 2 * bits - 1                                 # BPSK mapping 0 -> -1, 1 -> +1
        car = table[hop_per_bit[start:start + m]]          # TX: carrier chosen by the PN sequence
        rx = sym[:, None] * car + sigma * rng.standard_normal((m, spb))   # signal + AWGN
        for ch in jam_channels:                            # add each jamming tone
            phase = rng.uniform(0, 2 * np.pi, m)           # unknown jammer phase, new for each bit
            freq = K0 + ch                                 # jammer sits exactly on hop channel `ch`
            rx += amp_each * np.cos(2 * np.pi * freq * tone_idx[None, :] / spb + phase[:, None])
        z = (2.0 / spb) * (rx * car).sum(axis=1)           # RX: de-hop with the same carrier + integrate
        errors += int(np.sum((z > 0) != (bits == 1)))      # compare decisions with the sent bits
    return errors / n_bits


# ----------------------------------------------------------------- theory
def ber_awgn(ebn0_db):
    """Theoretical coherent BPSK in AWGN:  Pb = Q( sqrt(2 Eb/N0) )."""
    return utils.q_function(np.sqrt(2.0 * 10.0 ** (np.asarray(ebn0_db, float) / 10.0)))


def ber_tone_hit(ebn0_db, amp):
    """
    BER of one bit that IS hit by a tone of amplitude `amp` (signal amplitude = 1) with random phase:
        Pb|hit = (1/pi) * integral_0^pi Q( sqrt(2 gamma) (1 + amp cos(phi)) ) dphi
    """
    gamma = 10.0 ** (np.asarray(ebn0_db, float) / 10.0)
    phi = np.linspace(0.0, np.pi, 2001)                    # phase grid
    arg = np.sqrt(2.0 * gamma)[..., None] * (1.0 + amp * np.cos(phi))
    return utils.q_function(arg).mean(axis=-1)             # numerical average over the phase


def ber_fhss_jam(ebn0_db, n_channels, n_jam, jsr_db, hopping=True):
    """
    Theory for FHSS under jamming. A bit is hit with probability n_jam/N (hopping) or 1 (fixed carrier
    sitting on a jammed channel). Hit bits see BER_hit, the others see plain AWGN BER.
    """
    amp = np.sqrt(10.0 ** (jsr_db / 10.0) / max(n_jam, 1))   # amplitude of each tone
    p_hit = (n_jam / n_channels) if hopping else 1.0          # probability that the carrier is jammed
    return p_hit * ber_tone_hit(ebn0_db, amp) + (1 - p_hit) * ber_awgn(ebn0_db)


def ber_rayleigh_theory(ebn0_db):
    """Average BER of coherent BPSK over flat Rayleigh fading:  0.5 (1 - sqrt(g/(1+g)))."""
    g = 10.0 ** (np.asarray(ebn0_db, float) / 10.0)
    return 0.5 * (1.0 - np.sqrt(g / (1.0 + g)))


def ber_rayleigh_sim(ebn0_db, n_bits, rng):
    """Symbol-level Monte-Carlo of BPSK with a fresh Rayleigh gain per hop (independent fading)."""
    g = 10.0 ** (ebn0_db / 10.0)
    h = (rng.standard_normal(n_bits) + 1j * rng.standard_normal(n_bits)) / np.sqrt(2.0)   # CN(0,1) gains
    bits = rng.integers(0, 2, n_bits); sym = 2 * bits - 1
    noise = rng.standard_normal(n_bits) / np.sqrt(2.0 * g)  # noise std for Eb/N0 = g (|h|^2 averages to 1)
    z = np.abs(h) * sym + noise                             # coherent detection removes the phase of h
    return float(np.mean((z > 0) != (bits == 1)))


def snr_for_ber(target, ber_fn):
    """Eb/N0 (dB) at which a decreasing BER function reaches `target` (bisection search)."""
    lo, hi = -10.0, 60.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if ber_fn(mid) > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------- 8-bit demo
def demo(cfg):
    """Display PN sequence, binary input and FHSS output for the 8-bit stream asked in the handout."""
    n_ch = cfg["n_channels"]; bits = np.array(cfg["demo_bits"])
    hops, pn_stream = hop_indices(bits.size, n_ch, cfg["demo_degree"], cfg["demo_taps"], cfg["demo_seed"])
    m = int(np.log2(n_ch))
    rows = []
    for k in range(bits.size):
        pn_word = "".join(str(int(x)) for x in pn_stream[k * m:(k + 1) * m])   # the PN bits used for this hop
        f_rf = cfg["rf_base_hz"] + hops[k] * cfg["rf_spacing_hz"]              # RF carrier shown to the user
        rows.append({"bit_no": k + 1, "data": int(bits[k]), "bpsk": int(2 * bits[k] - 1), "pn_bits": pn_word,
                     "hop_channel": int(hops[k]), "rf_mhz": float(f_rf / 1e6)})
    # waveform for the plot: 60 samples per bit so the highest carrier is smooth
    spb = 60
    n = np.arange(spb)
    wave = np.concatenate([(2 * bits[k] - 1) * np.cos(2 * np.pi * (K0 + hops[k]) * n / spb) for k in range(bits.size)])
    return {"rows": rows, "bits": bits, "hops": hops, "wave": wave, "spb": spb,
            "pn_stream": pn_stream, "pn_degree": cfg["demo_degree"]}


def plot_demo(d, name):
    """Four stacked panels: data bits, PN hop index, carrier frequency, FHSS waveform."""
    n_b = d["bits"].size; spb = d["spb"]
    fig, axes = plt.subplots(4, 1, figsize=(10, 8.4), sharex=True)
    axes[0].step(np.arange(n_b + 1), np.append(d["bits"], d["bits"][-1]), where="post", color=utils.PALETTE[0], linewidth=2)
    axes[0].set_ylabel("Data bit"); axes[0].set_yticks([0, 1]); axes[0].set_title("FHSS transmitter, 8-bit demo")
    axes[1].step(np.arange(n_b + 1), np.append(d["hops"], d["hops"][-1]), where="post", color=utils.PALETTE[3], linewidth=2)
    axes[1].set_ylabel("PN hop\nchannel"); axes[1].set_yticks(range(0, 8))
    axes[2].step(np.arange(n_b + 1), np.append(K0 + d["hops"], K0 + d["hops"][-1]), where="post", color=utils.PALETTE[1], linewidth=2)
    axes[2].set_ylabel("Carrier\n(cycles/bit)")
    t = np.arange(d["wave"].size) / spb
    axes[3].plot(t, d["wave"], color=utils.INK, linewidth=0.9)
    axes[3].set_ylabel("FHSS output"); axes[3].set_xlabel("Time (bit periods)")
    for ax in axes: ax.set_xlim(0, n_b)
    return utils.save_fig(fig, name)


def plot_spectrum(n_ch, name, rng):
    """Power spectral density of plain BPSK vs FHSS: the hopped signal occupies N times more bandwidth."""
    n_bits = 4000; spb = 4 * (K0 + n_ch); table = carrier_table(n_ch, spb)
    bits = 2 * rng.integers(0, 2, n_bits) - 1
    hops, _ = hop_indices(n_bits, n_ch, 16, [16, 14, 13, 11], 0xACE1)
    fixed = (bits[:, None] * table[0][None, :]).ravel()          # no hopping: always channel 0
    hopped = (bits[:, None] * table[hops]).ravel()               # hopping with the PN sequence
    f1, p1 = welch(fixed, fs=spb, nperseg=2048); f2, p2 = welch(hopped, fs=spb, nperseg=2048)
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.semilogy(f1, p1, color=utils.PALETTE[1], label="Plain BPSK (one carrier)")
    ax.semilogy(f2, p2, color=utils.PALETTE[0], label=f"FHSS over N = {n_ch} channels")
    ax.set_xlim(0, K0 + n_ch + 2); ax.set_ylim(1e-6, 1)
    ax.set_xlabel("Frequency (multiples of the bit rate)"); ax.set_ylabel("Power spectral density")
    ax.set_title("Spectrum spreading: the energy is spread over N channels"); ax.legend()
    return utils.save_fig(fig, name)


# ---------------------------------------------------------------- BER studies
def run_ber_curves(cfg, rng):
    """BER vs Eb/N0 for the four situations, simulated and theoretical."""
    n_ch = cfg["n_channels"]; ebn0 = cfg["ebn0_db"]; jsr = cfg["jsr_db"]; nb = cfg["n_bits"]
    n_partial = n_ch // 2                                  # partial-band jammer covers half the channels
    lf = {"degree": cfg["lfsr_degree"], "taps": cfg["lfsr_taps"], "seed": cfg["lfsr_seed"]}
    sims = {"fhss_clean": [], "fixed_jam": [], "fhss_tone": [], "fhss_partial": []}
    for e in ebn0:                                         # one simulation per Eb/N0 point
        sims["fhss_clean"].append(simulate_ber(e, nb, n_ch, rng, True, (), jsr, cfg["bits_per_hop"], lf))
        sims["fixed_jam"].append(simulate_ber(e, nb, n_ch, rng, False, (0,), jsr, 1, lf))
        sims["fhss_tone"].append(simulate_ber(e, nb, n_ch, rng, True, (0,), jsr, cfg["bits_per_hop"], lf))
        sims["fhss_partial"].append(simulate_ber(e, nb, n_ch, rng, True, tuple(range(n_partial)), jsr, cfg["bits_per_hop"], lf))
    theo = {"awgn": ber_awgn(ebn0),
            "fixed_jam": ber_fhss_jam(ebn0, n_ch, 1, jsr, hopping=False),
            "fhss_tone": ber_fhss_jam(ebn0, n_ch, 1, jsr, hopping=True),
            "fhss_partial": ber_fhss_jam(ebn0, n_ch, n_partial, jsr, hopping=True)}
    return {"ebn0": ebn0, "sim": sims, "theory": theo, "n_partial": n_partial}


def plot_ber(res, cfg, name):
    """Semilog BER plot. Points with ZERO measured errors cannot be drawn on a log axis and are omitted."""
    e = np.array(res["ebn0"]); floor = 1.0 / cfg["n_bits"]
    fig, ax = plt.subplots(figsize=(9, 5.8))
    spec = [("awgn", None, "BPSK / FHSS, no jammer (theory)", utils.INK, "-"),
            ("fixed_jam", "fixed_jam", "Fixed carrier + tone jammer", utils.PALETTE[4], "o"),
            ("fhss_tone", "fhss_tone", "FHSS + tone jammer", utils.PALETTE[0], "s"),
            ("fhss_partial", "fhss_partial", f"FHSS + partial-band jammer ({res['n_partial']}/{cfg['n_channels']} channels)", utils.PALETTE[2], "^")]
    for tkey, skey, label, colour, mk in spec:
        ax.semilogy(e, res["theory"][tkey], "-" if mk != "-" else "-", color=colour, linewidth=1.3, alpha=0.9,
                    label=None if skey else label)           # theory = line
        if skey:
            y = np.array(res["sim"][skey]); ok = y > 0       # only points with >= 1 error
            ax.semilogy(e[ok], y[ok], mk, color=colour, markersize=6, label=label + " (sim)")
    y = np.array(res["sim"]["fhss_clean"]); ok = y > 0
    ax.semilogy(e[ok], y[ok], "D", color=utils.INK, markersize=5, mfc="white", label="FHSS, no jammer (sim)")
    ax.set_ylim(floor / 2, 1); ax.set_xlabel("Eb/N0 (dB)"); ax.set_ylabel("Bit error rate")
    ax.set_title(f"FHSS BER vs Eb/N0 (N = {cfg['n_channels']}, JSR = {cfg['jsr_db']:g} dB). Lines = theory, markers = simulation")
    ax.legend(loc="lower left", fontsize=8)
    return utils.save_fig(fig, name)


def run_pg_study(cfg, rng):
    """Processing gain and BER (tone jammer, Eb/N0 = 10 dB) for N = 2, 4, 8, 16 hopping channels."""
    out = []
    for n in cfg["pg_sweep_channels"]:
        sim = simulate_ber(10.0, cfg["pg_sweep_bits"], n, rng, True, (0,), cfg["jsr_db"], 1)
        out.append({"N": n, "pg_db": 10 * np.log10(n), "ber_sim": sim,
                    "ber_theory": float(ber_fhss_jam(10.0, n, 1, cfg["jsr_db"], True))})
    return out


def plot_pg(rows, cfg, name):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ns = [r["N"] for r in rows]
    b = axes[0].bar([str(n) for n in ns], [r["pg_db"] for r in rows], color=utils.PALETTE[0], width=0.5)
    axes[0].bar_label(b, fmt="%.1f dB", padding=2); axes[0].set_xlabel("Hopping channels N")
    axes[0].set_ylabel("Processing gain (dB)"); axes[0].set_title("PG = 10 log10(N)")
    axes[1].semilogy(ns, [r["ber_theory"] for r in rows], "-", color=utils.PALETTE[0], label="theory")
    axes[1].semilogy(ns, [max(r["ber_sim"], 1e-6) for r in rows], "o", color=utils.PALETTE[1], label="simulation")
    axes[1].set_xscale("log", base=2); axes[1].set_xticks(ns); axes[1].set_xticklabels([str(n) for n in ns])
    axes[1].set_xlabel("Hopping channels N"); axes[1].set_ylabel("BER at Eb/N0 = 10 dB")
    axes[1].set_title(f"Tone-jammer damage falls ~1/N (JSR = {cfg['jsr_db']:g} dB)"); axes[1].legend()
    return utils.save_fig(fig, name)


def run_fading_ber(cfg, rng):
    """AWGN vs Rayleigh BER (theory + Monte-Carlo) and the Eb/N0 penalty at BER = 1e-3."""
    e = np.arange(0, 31, 2)
    sim = [ber_rayleigh_sim(float(x), cfg["fading_bits"], rng) for x in e]
    pen_awgn = snr_for_ber(1e-3, lambda x: float(ber_awgn(x)))
    pen_ray = snr_for_ber(1e-3, lambda x: float(ber_rayleigh_theory(x)))
    return {"ebn0": e, "sim": sim, "awgn_snr_1e3": pen_awgn, "rayleigh_snr_1e3": pen_ray,
            "penalty_db": pen_ray - pen_awgn}


def plot_fading_ber(r, name):
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.linspace(0, 30, 200)
    ax.semilogy(x, ber_awgn(x), color=utils.INK, label="AWGN (theory)")
    ax.semilogy(x, ber_rayleigh_theory(x), color=utils.PALETTE[0], label="Rayleigh fading (theory)")
    y = np.array(r["sim"]); ok = y > 0
    ax.semilogy(r["ebn0"][ok], y[ok], "o", color=utils.PALETTE[1], label="Rayleigh fading (simulation)")
    ax.axhline(1e-3, color=utils.MUTED, linestyle=":")
    ax.set_ylim(1e-6, 1); ax.set_xlabel("Eb/N0 (dB)"); ax.set_ylabel("Bit error rate")
    ax.set_title(f"Fading penalty at BER = 1e-3: {r['penalty_db']:.1f} dB more Eb/N0 needed"); ax.legend()
    return utils.save_fig(fig, name)


# ------------------------------------------------------------------ main entry
def run(cfg=None, fast=False):
    """Run Experiment 5. fast=True uses 10x fewer bits (quick smoke test)."""
    cfg = dict(cfg or settings.EXP5)
    if fast:                                          # shrink the workload for quick tests
        cfg["n_bits"] //= 10; cfg["pg_sweep_bits"] //= 10; cfg["fading_bits"] //= 10
    utils.apply_style()
    rng = np.random.default_rng(settings.RANDOM_SEED + 5)
    d = demo(cfg)
    ber = run_ber_curves(cfg, rng)
    pg = run_pg_study(cfg, rng)
    fad = run_fading_ber(cfg, rng)
    figs = [plot_demo(d, "exp5_fhss_demo_8bits"), plot_ber(ber, cfg, "exp5_ber_vs_ebn0"),
            plot_pg(pg, cfg, "exp5_processing_gain"), plot_fading_ber(fad, "exp5_rayleigh_vs_awgn"),
            plot_spectrum(cfg["n_channels"], "exp5_spectrum_spreading", rng)]
    utils.save_table([[r["bit_no"], r["data"], r["bpsk"], r["pn_bits"], r["hop_channel"], f"{r['rf_mhz']:.1f}"] for r in d["rows"]],
                     ["Bit no.", "Input bit", "BPSK symbol", "PN bits", "Hop channel", "RF carrier (MHz)"], "exp5_demo_table")
    utils.save_table([[e, f"{ber['theory']['awgn'][k]:.3e}", f"{ber['sim']['fhss_clean'][k]:.3e}",
                       f"{ber['sim']['fixed_jam'][k]:.3e}", f"{ber['sim']['fhss_tone'][k]:.3e}",
                       f"{ber['sim']['fhss_partial'][k]:.3e}"] for k, e in enumerate(ber["ebn0"])],
                     ["Eb/N0 (dB)", "Theory AWGN", "FHSS no jam (sim)", "Fixed+jam (sim)", "FHSS+tone jam (sim)", "FHSS+partial jam (sim)"],
                     "exp5_ber_table")
    period16 = lfsr_period(cfg["lfsr_degree"], cfg["lfsr_taps"], cfg["lfsr_seed"])
    return {"demo": d, "ber": ber, "pg": pg, "fading": fad, "figures": figs, "lfsr_period": period16, "config": cfg}


if __name__ == "__main__":
    import time; t0 = time.time()
    out = run(fast=True)
    print("period", out["lfsr_period"], "time", round(time.time() - t0, 1))
    for r in out["demo"]["rows"]: print(r)
    print(out["ber"]["sim"]["fhss_tone"][:13])
    print(np.round(out["ber"]["theory"]["fhss_tone"], 5))
