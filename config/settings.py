# =============================================================================
# FILE        : config/settings.py
# PROJECT     : CellHop Planner  (Wireless Communications & Networks - course project)
# WHAT IT IS  : The single place where EVERY tunable number of the project lives
#               (bandwidths, traffic per user, path-loss exponent, jammer power ...).
# WHAT IT DOES: Defines folder paths for the outputs/ directory, the random seed
#               and one dictionary of parameters per experiment (EXP1 ... EXP5)
#               plus the integrated-planner parameters (PLANNER).
#               All values default to the numbers given in the lab handouts.
# LAST STEP   : Nothing runs before this file; main.py imports it first.
# NEXT STEP   : main.py hands these dictionaries to wcn/exp1 ... exp5 and to
#               wcn/integrated_planner.py. Change a number here -> whole project updates.
# =============================================================================

from pathlib import Path  # Path gives us OS-independent file-path handling

# ---------------------------------------------------------------- folder layout
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # folder that contains main.py
OUTPUT_DIR   = PROJECT_ROOT / "outputs"                 # everything we produce is saved here
FIG_DIR      = OUTPUT_DIR / "figures"                   # PNG charts
TABLE_DIR    = OUTPUT_DIR / "tables"                    # CSV tables
REPORT_DIR   = OUTPUT_DIR / "report"                    # cumulative .docx report
RESULTS_JSON = OUTPUT_DIR / "results.json"              # machine-readable results (feeds the report)

RANDOM_SEED = 2026   # fixed seed -> every run reproduces the same random numbers / plots

# ------------------------------------------------------------------- Expt 1
# Frequency reuse, co-channel interference, cell splitting
EXP1 = {
    "total_bandwidth_hz": 35e6,      # total spectrum allocated to the operator (35 MHz)
    "simplex_channel_hz": 200e3,     # one simplex channel needs 200 kHz
    "cell_area_km2": 5.0,            # area of one hexagonal cell (given in the handout)
    "ij_pairs": [(1, 1), (2, 0), (2, 1), (3, 0), (2, 2), (3, 1)],  # -> N = 3,4,7,9,12,13
    "primary_ij": (2, 2),            # handout says "perform for cluster size 12" -> (2,2)
    "repeats_M": 3,                  # how many times the cluster is repeated in the plot
    "split_factor": 2,               # cell splitting: new radius = R / 2
    "split_pathloss_exp": [3.0, 4.0] # exponents used to show transmit-power reduction
}

# ------------------------------------------------------------------- Expt 2
# Trunking and Grade of Service (Erlang-B, blocked-calls-cleared)
EXP2 = {
    "n_cells": 84,                   # cells covering the service area
    "total_channels": 300,           # voice channels available to the whole system
    "traffic_per_user_erl": 0.04,    # offered traffic per user (Erlang)
    "blocking_prob": 0.01,           # designated GoS: Pb = 1 %
    "cluster_sizes": [4, 12, 13],    # the three cluster sizes asked in the handout
    "mc_calls": 300_000,             # calls simulated for the Monte-Carlo check of Erlang-B
}

# ------------------------------------------------------------------- Expt 3
# Multipath: Power Delay Profile, delay spread, coherence bandwidth
EXP3 = {
    # Part A input : excess delay (ns) and received power (dBm) of each multipath ray
    "delays_ns": [0, 150, 350, 600, 1000, 1600],
    "powers_dbm": [-60.0, -63.0, -68.0, -72.0, -78.0, -86.0],
    # Channel bandwidths we compare against the coherence bandwidth (name -> Hz)
    "systems_hz": {"GSM 200 kHz": 200e3, "IS-95 1.25 MHz": 1.25e6,
                   "WCDMA 5 MHz": 5e6, "LTE 20 MHz": 20e6},
}

# ------------------------------------------------------------------- Expt 4
# Large-scale (path loss + shadowing) and small-scale (Rayleigh, Doppler) fading
EXP4 = {
    "carrier_hz": 900e6,             # carrier frequency (Part B)
    "d0_m": 10.0,                    # reference distance
    "p0_dbm": -40.0,                 # received power at the reference distance
    "pathloss_exp": 3.0,             # path-loss exponent n
    "shadow_sigma_db": 4.0,          # log-normal shadowing standard deviation
    "n_positions": 10,               # receiver positions
    "d_min_m": 20.0, "d_max_m": 1000.0,   # distance range covered by the positions
    "samples_per_position": 100,     # Part A: Rayleigh samples per position
    "velocity_mps": 30.0,            # Part B: mobile speed
    "n_time_samples": 1000,          # Part B: time samples
    "sample_rate_hz": 2000.0,        # Part B: time-sampling rate (2 kHz >> 2*fd)
    "selected_distance_m": 200.0,    # Part B: distance at which time fading is shown
    "n_sinusoids": 64,               # sum-of-sinusoids oscillators in the Rayleigh generator
    "n_realisations": 300,           # realisations averaged for the validation plots
}

# ------------------------------------------------------------------- Expt 5
# Frequency Hopping Spread Spectrum (FHSS) with BPSK
EXP5 = {
    "n_bits": 200_000,               # bits simulated per Eb/N0 point
    "n_channels": 8,                 # hopping channels N  (power of 2 -> 3 PN bits per hop)
    "bits_per_hop": 1,               # 1 = fast hopping; >1 = slow hopping
    "ebn0_db": list(range(0, 13)),   # 0 ... 12 dB as asked in the handout
    "jsr_db": 6.0,                   # tone-jammer power / signal power (dB)
    "lfsr_degree": 16,               # PN generator length (maximal-length LFSR)
    "lfsr_taps": [16, 14, 13, 11],   # x^16 + x^14 + x^13 + x^11 + 1  (maximal)
    "lfsr_seed": 0xACE1,             # non-zero initial state of the LFSR
    "demo_bits": [1, 0, 1, 1, 0, 0, 1, 0],  # 8-bit demo asked in the handout
    "demo_degree": 4, "demo_taps": [4, 3], "demo_seed": 0b1001,  # tiny LFSR for the demo
    "rf_base_hz": 900e6, "rf_spacing_hz": 200e3,   # RF mapping used only for display
    "pg_sweep_channels": [2, 4, 8, 16],            # N values for the processing-gain study
    "pg_sweep_bits": 100_000,                      # bits per point in that study
    "fading_bits": 400_000,          # bits used for the Rayleigh-fading BER comparison
}

# ------------------------------------------------------- Integrated planner
PLANNER = {
    "cluster_candidates_max_n": 19,  # evaluate every valid N = i^2+ij+j^2 from 3 up to this value
    "sir_threshold_db": 9.0,         # required co-channel C/I (GSM-class digital system)
    "outage_target": 0.10,           # accept at most 10 % of locations below the threshold
    "pathloss_exps": [3.0, 4.0],     # n = 3 (Expt 4 value) and n = 4 (dense urban) sensitivity
    "shadow_sigma_db": 4.0,          # shadowing used in the SIR Monte-Carlo
    "mc_samples": 100_000,           # random user positions per (N, n) in the SIR Monte-Carlo
    "ebn0_db": 10.0,                 # operating Eb/N0 for the jam-resilience figure
    "jsr_db": 6.0,                   # tone-jammer strength for the jam-resilience figure
    "sensitivity_thresholds_db": [9.0, 12.0, 18.0],  # GSM-like / typical / AMPS-like
}
