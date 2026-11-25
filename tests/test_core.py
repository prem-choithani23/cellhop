# =============================================================================
# FILE        : tests/test_core.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Automatic self-checks of the maths. Every important formula is compared with a
#               known textbook value or an independent calculation (scipy), so we can PROVE
#               the numbers in the report are right.
# WHAT IT DOES: * Erlang-B against known values and against scipy's Poisson-based formula
#               * cluster-size formula, frequency labelling and measured D/R = sqrt(3N)
#               * LFSR maximal period, Doppler/coherence numbers, PDP formulas, PG
# LAST STEP   : All wcn/*.py modules exist.
# NEXT STEP   : Run with   python -m pytest -q   (or)   python tests/test_core.py
# =============================================================================

import math                                   # math: sqrt, log10
import os, sys                                # make the project root importable when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                            # numpy: arrays
from scipy.stats import poisson               # poisson: independent Erlang-B check

from wcn import hexgrid as hg, exp1_frequency_reuse as e1, exp2_trunking_gos as e2
from wcn import exp3_multipath as e3, exp4_fading as e4, exp5_fhss as e5
from config import settings


def test_erlang_b_known_values():
    assert abs(e2.erlang_b(1.0, 1) - 0.5) < 1e-12            # one channel, 1 Erlang -> 50 %
    assert abs(e2.erlang_b(2.0, 3) - 4.0 / 19.0) < 1e-12     # classic textbook value 0.2105


def test_erlang_b_matches_poisson_formula():
    # independent formula: B(A,C) = Poisson_pmf(C; A) / Poisson_cdf(C; A)
    for a, c in [(60.7, 75), (16.1, 25), (14.5, 23)]:
        independent = poisson.pmf(c, a) / poisson.cdf(c, a)
        assert abs(e2.erlang_b(a, c) - independent) < 1e-10


def test_capacity_hits_one_percent():
    for c in (23, 25, 75):
        a = e2.capacity_at_gos(c, 0.01)
        assert abs(e2.erlang_b(a, c) - 0.01) < 1e-8


def test_expt2_headline_numbers():
    rows = {r["N"]: r for r in (e2.design_row(n, settings.EXP2) for n in (4, 12, 13))}
    assert [rows[n]["channels_per_cell"] for n in (4, 12, 13)] == [75, 25, 23]
    assert abs(rows[4]["offered_erl_per_cell"] - 60.73) < 0.01
    assert abs(rows[12]["offered_erl_per_cell"] - 16.12) < 0.01


def test_cluster_formula_and_labels():
    assert [hg.cluster_size(*p) for p in [(1, 1), (2, 0), (2, 1), (3, 0), (2, 2), (3, 1)]] == [3, 4, 7, 9, 12, 13]
    for (i, j) in [(1, 1), (2, 0), (2, 1), (2, 2), (3, 1)]:
        n = hg.cluster_size(i, j)
        labels = hg.assign_labels(hg.hex_disc(6), i, j)
        assert len(set(labels.values())) == n                # exactly N frequency groups


def test_measured_reuse_ratio_equals_sqrt_3n():
    R = hg.cell_radius_from_area(5.0)
    for (i, j) in [(1, 1), (2, 1), (2, 2), (3, 1)]:
        sim = e1.simulate_cochannel_distance(i, j, R, 3)
        assert abs(sim["q_sim"] - math.sqrt(3 * hg.cluster_size(i, j))) < 1e-9


def test_channel_budget():
    assert e1.channel_budget(35e6, 200e3, 12) == (87, 7)     # 35 MHz / 400 kHz = 87.5 -> 87 duplex channels


def test_lfsr_is_maximal_length():
    assert e5.lfsr_period(4, [4, 3], 0b1001) == 15
    assert e5.lfsr_period(16, [16, 14, 13, 11], 0xACE1) == 65535


def test_doppler_and_coherence_time():
    mob = e4.mobility_parameters(900e6, 30.0)
    assert abs(mob["fd_hz"] - 90.06) < 0.01 and abs(mob["tc_s"] - 0.423 / mob["fd_hz"]) < 1e-12


def test_delay_spread_formulas():
    # two equal-power rays 0 and 1000 ns apart -> mean 500 ns, RMS spread 500 ns, Bc = 1/(5*500ns) = 400 kHz
    r = e3.delay_spread_analysis([0, 1000], [1.0, 1.0])
    assert abs(r["tau_mean_s"] - 500e-9) < 1e-15 and abs(r["sigma_s"] - 500e-9) < 1e-15
    assert abs(r["bc_50_hz"] - 400e3) < 1.0


def test_fhss_awgn_ber_matches_theory():
    rng = np.random.default_rng(1)
    sim = e5.simulate_ber(4.0, 100_000, 8, rng)
    assert abs(sim - float(e5.ber_awgn(4.0))) < 0.15 * float(e5.ber_awgn(4.0)) + 1e-4


if __name__ == "__main__":                       # simple runner without pytest
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
