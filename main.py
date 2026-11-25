# =============================================================================
# FILE        : main.py
# PROJECT     : CellHop Planner  (Wireless Communications & Networks - course project)
# WHAT IT IS  : The ONE command that runs the whole project from start to finish.
# WHAT IT DOES: 1. Runs Experiment 1 (frequency reuse + cell splitting)
#               2. Runs Experiment 2 (trunking / Erlang-B / GoS)
#               3. Runs Experiment 3 (PDP, delay spread, coherence bandwidth)
#               4. Runs Experiment 4 (path loss, shadowing, Rayleigh fading, Doppler)
#               5. Runs Experiment 5 (FHSS: BER under AWGN and jamming)
#               6. Runs the integrated planner (joins 1-5 into a design decision)
#               7. Saves every figure to outputs/figures, tables to outputs/tables,
#                  numbers to outputs/results.json and builds outputs/report/*.docx
# USAGE       : python main.py                  full run (about 1-2 minutes)
#               python main.py --fast           10x fewer random samples (quick check)
#               python main.py --interactive    type your own multipath delays/powers (Expt 3)
#               python main.py --pdp my.csv     load multipath delays(ns),powers(dBm) from a CSV
#               python main.py --no-report      skip the Word report
# LAST STEP   : config/settings.py (parameters) -> wcn/*.py (the experiment modules).
# NEXT STEP   : Open outputs/report/WCN_CellHop_Report.docx and the PNGs in outputs/figures/.
# =============================================================================

import argparse                               # argparse: command-line options
import time                                   # time: measure how long each stage takes

from config import settings                   # parameters and folders
from wcn import utils                         # saving helpers
from wcn import (exp1_frequency_reuse as e1, exp2_trunking_gos as e2, exp3_multipath as e3,
                 exp4_fading as e4, exp5_fhss as e5, integrated_planner as planner,
                 report_builder)              # all experiment modules + the report writer


def banner(text):
    """Print a visible section title in the console."""
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)


def main():
    # ------------------------------------------------ command-line options
    ap = argparse.ArgumentParser(description="CellHop Planner - WCN course project")
    ap.add_argument("--fast", action="store_true", help="use 10x fewer random samples")
    ap.add_argument("--interactive", action="store_true", help="enter multipath delays/powers by hand (Expt 3)")
    ap.add_argument("--pdp", type=str, default=None, help="CSV file: delay_ns,power_dbm")
    ap.add_argument("--no-report", action="store_true", help="do not build the .docx report")
    args = ap.parse_args()                    # read what the user typed

    utils.ensure_output_dirs()                # make sure outputs/ exists
    results = {}                              # dictionary that collects everything
    t0 = time.time()                          # start time

    # ------------------------------------------------ Experiment 1
    banner("EXPT 1 - Frequency reuse, co-channel interference, cell splitting")
    results["exp1"] = e1.run()
    print(f"cell radius R = {results['exp1']['R_km']:.3f} km  (cell area {results['exp1']['cell_area_km2']} km^2)")
    print(f"{'i':>2} {'j':>2} {'N':>3} {'duplex ch':>10} {'ch/cell':>8} {'D theory km':>12} {'q=sqrt(3N)':>11} {'D sim km':>9} {'q sim':>7}")
    for r in results["exp1"]["rows"]:
        print(f"{r['i']:>2} {r['j']:>2} {r['N']:>3} {r['total_duplex_channels']:>10} {r['channels_per_cell']:>8} "
              f"{r['D_theory_km']:>12.3f} {r['q_theory']:>11.3f} {r['D_sim_km']:>9.3f} {r['q_sim']:>7.3f}")

    # ------------------------------------------------ Experiment 2
    banner("EXPT 2 - Trunking and Grade of Service (84 cells, 300 channels, 0.04 Erl/user, Pb = 1 %)")
    results["exp2"] = e2.run(mc_calls=(settings.EXP2["mc_calls"] // 10 if args.fast else None))
    print(f"{'N':>3} {'C':>4} {'A offered':>10} {'A carried':>10} {'users/cell':>11} {'system users':>13} {'MC blocking':>12}")
    for r in results["exp2"]["rows"]:
        print(f"{r['N']:>3} {r['channels_per_cell']:>4} {r['offered_erl_per_cell']:>10.3f} {r['carried_erl_per_cell']:>10.3f} "
              f"{r['users_per_cell']:>11} {r['users_system']:>13} {r['mc_blocking']*100:>11.2f}%")
    print("\n".join("  - " + s for s in results["exp2"]["inference"]))

    # ------------------------------------------------ Experiment 3
    banner("EXPT 3 - Multipath: PDP, delay spread, coherence bandwidth")
    if args.interactive:
        d_ns, p_dbm = e3.prompt_pdp()         # user types the multipath components
    elif args.pdp:
        d_ns, p_dbm = e3.load_pdp_csv(args.pdp)
    else:
        d_ns = p_dbm = None                   # use the defaults from settings.py
    results["exp3"] = e3.run(delays_ns=d_ns, powers_dbm=p_dbm)
    a, b = results["exp3"]["partA"], results["exp3"]["partB"]
    print(f"strongest: path {a['strongest']['path']} ({a['strongest']['power_dbm']} dBm), weakest: path {a['weakest']['path']} ({a['weakest']['power_dbm']} dBm)")
    print(f"max excess delay = {a['max_excess_delay_ns']:.0f} ns, average power = {a['avg_power_dbm_arithmetic']:.2f} dBm (mean of dBm) / {a['avg_power_dbm_linear']:.2f} dBm (power domain)")
    print(f"mean excess delay = {b['tau_mean_s']*1e9:.1f} ns, RMS delay spread = {b['sigma_s']*1e9:.1f} ns, Bc(0.5) = {b['bc_50_hz']/1e3:.0f} kHz, Bc(0.9) = {b['bc_90_hz']/1e3:.0f} kHz")
    for c in results["exp3"]["classes"]:
        print(f"  {c['system']:<16} -> {c['type']}")

    # ------------------------------------------------ Experiment 4
    banner("EXPT 4 - Large-scale / small-scale fading and mobility")
    results["exp4"] = e4.run()
    m = results["exp4"]["partB"]["mob"]
    print(f"lambda = {m['wavelength_m']:.4f} m, fd = {m['fd_hz']:.1f} Hz, Doppler spread = {m['doppler_spread_hz']:.1f} Hz, Tc = {m['tc_s']*1e3:.2f} ms")
    print(f"path-loss exponent recovered from the simulation = {results['exp4']['partA']['n_estimated']:.2f} (input 3.0)")
    print(f"Rayleigh mean {results['exp4']['partA']['rayleigh_mean_db']:.2f} dB (theory -2.51), std {results['exp4']['partA']['rayleigh_std_db']:.2f} dB (theory 5.57)")
    print(f"level-crossing rate measured {results['exp4']['partB']['lcr_meas']:.1f}/s vs theory {results['exp4']['partB']['lcr_theory']:.1f}/s")

    # ------------------------------------------------ Experiment 5
    banner("EXPT 5 - FHSS transmitter / receiver, AWGN and jamming")
    results["exp5"] = e5.run(fast=args.fast)
    print("8-bit demo:  bit | PN bits | hop ch | RF carrier (MHz)")
    for r in results["exp5"]["demo"]["rows"]:
        print(f"             {r['data']:>3} | {r['pn_bits']:>7} | {r['hop_channel']:>6} | {r['rf_mhz']:.1f}")
    ber = results["exp5"]["ber"]
    print("Eb/N0  theory-AWGN  FHSS-clean  fixed+jam  FHSS+tone  FHSS+partial")
    for k, e in enumerate(ber["ebn0"]):
        print(f"{e:>5}  {ber['theory']['awgn'][k]:>10.2e}  {ber['sim']['fhss_clean'][k]:>10.2e}  {ber['sim']['fixed_jam'][k]:>9.2e}  "
              f"{ber['sim']['fhss_tone'][k]:>9.2e}  {ber['sim']['fhss_partial'][k]:>11.2e}")
    print(f"LFSR period = {results['exp5']['lfsr_period']} (maximal = 2^16 - 1 = 65535)")
    print(f"Rayleigh fading penalty at BER 1e-3 = {results['exp5']['fading']['penalty_db']:.1f} dB")

    # ------------------------------------------------ Integrated planner
    banner("INTEGRATED PLANNER - capacity x interference x fading x hopping")
    results["planner"] = planner.run(results["exp3"], fast=args.fast)
    thr = settings.PLANNER["sir_threshold_db"]
    print(f"{'N':>3} {'C':>4} {'users':>8} {'SIRworst n=3':>13} {'SIRworst n=4':>13} {'outage n=3':>11} {'outage n=4':>11} {'PG dB':>6} {'div':>4}")
    for r in results["planner"]["rows"]:
        print(f"{r['N']:>3} {r['channels_per_cell']:>4} {r['users_system']:>8} {r['sir']['3.0']['worst_db']:>13.1f} {r['sir']['4.0']['worst_db']:>13.1f} "
              f"{r['sir']['3.0']['outage_ls'][thr]*100:>10.1f}% {r['sir']['4.0']['outage_ls'][thr]*100:>10.1f}% {r['pg_db']:>6.1f} {r['diversity_order']:>4}")
    for d in results["planner"]["decisions"]:
        print(f"  n = {d['n']:g}, threshold {d['threshold_db']:g} dB -> recommended N = {d['N']}  (users {d['users_system']})")

    # ------------------------------------------------ save numbers + report
    utils.save_results(results)
    print(f"\nresults saved to {settings.RESULTS_JSON}")
    if not args.no_report:
        path = report_builder.build(results)
        print(f"report saved to {path}")
    print(f"total time {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
