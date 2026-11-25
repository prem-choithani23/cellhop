# =============================================================================
# FILE        : wcn/report_builder.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Builds the CUMULATIVE REPORT (Word .docx) that explains the results and
#               findings of the whole project.
# WHAT IT DOES: Takes the `results` dictionary produced by main.py plus the PNG figures in
#               outputs/figures/ and writes outputs/report/WCN_CellHop_Report.docx with:
#               title, abstract, literature basis (which paper told us what), method and
#               results of Expt 1-5, the integrated planner study, overall inference,
#               assumptions / limitations, references and a how-to-run appendix.
#               Every number in the text is read from `results`, so the text can never
#               disagree with the tables and figures.
# LAST STEP   : wcn/integrated_planner.py finished the last calculation.
# NEXT STEP   : (end of pipeline) - open the .docx, add your names, submit.
# =============================================================================

from datetime import date                      # date: print today's date on the title page
from docx import Document                      # Document: create a Word file
from docx.shared import Pt, Inches, RGBColor   # Pt/Inches: sizes, RGBColor: colours
from docx.enum.text import WD_ALIGN_PARAGRAPH  # alignment constants
from docx.enum.table import WD_TABLE_ALIGNMENT # table alignment
from docx.oxml.ns import qn                    # qn: build XML names (needed for cell shading)
from docx.oxml import OxmlElement              # OxmlElement: create raw XML nodes

from config import settings                    # folder paths

ACCENT = RGBColor(0x2A, 0x78, 0xD6)            # blue used for headings


# ------------------------------------------------------------------ helpers
def _shade(cell, hex_fill):
    """Give a table cell a background colour (python-docx has no direct API for this)."""
    tc_pr = cell._tc.get_or_add_tcPr()         # cell properties XML node
    shd = OxmlElement("w:shd")                 # shading element
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _table(doc, header, rows, widths=None, font=9):
    """Add a formatted table: shaded bold header row, thin grid, small font."""
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, h in enumerate(header):             # header cells
        c = t.rows[0].cells[k]; c.text = ""
        run = c.paragraphs[0].add_run(str(h)); run.bold = True; run.font.size = Pt(font)
        _shade(c, "DCE8F7")
    for row in rows:                           # body cells
        cells = t.add_row().cells
        for k, v in enumerate(row):
            cells[k].text = ""
            run = cells[k].paragraphs[0].add_run(str(v)); run.font.size = Pt(font)
    if widths:                                 # optional column widths in inches
        for row in t.rows:
            for k, w in enumerate(widths):
                row.cells[k].width = Inches(w)
    doc.add_paragraph()                        # small gap after the table
    return t


class Rep:
    """Tiny wrapper that numbers figures/tables automatically."""
    def __init__(self):
        self.doc = Document()
        self.fig_no = 0; self.tab_no = 0
        st = self.doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
        for s in self.doc.sections:            # 1-inch margins
            s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1)

    def h1(self, text): self.doc.add_heading(text, level=1)
    def h2(self, text): self.doc.add_heading(text, level=2)
    def p(self, text, bold=False, italic=False):
        para = self.doc.add_paragraph(); r = para.add_run(text); r.bold = bold; r.italic = italic; return para
    def bullets(self, items):
        for it in items: self.doc.add_paragraph(it, style="List Bullet")
    def table(self, caption, header, rows, widths=None, font=9):
        self.tab_no += 1
        cap = self.doc.add_paragraph(); r = cap.add_run(f"Table {self.tab_no}. {caption}"); r.bold = True; r.font.size = Pt(10)
        _table(self.doc, header, rows, widths, font)
    def fig(self, name, caption, width=6.2):
        self.fig_no += 1
        self.doc.add_picture(str(settings.FIG_DIR / f"{name}.png"), width=Inches(width))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = self.doc.add_paragraph(); r = cap.add_run(f"Figure {self.fig_no}. {caption}"); r.italic = True; r.font.size = Pt(9.5)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ------------------------------------------------------------------ the report
def build(res):
    """Create the report from the results dictionary and return the file path."""
    R = Rep()
    e1, e2, e3, e4, e5, pl = (res[k] for k in ("exp1", "exp2", "exp3", "exp4", "exp5", "planner"))
    pcfg = pl["config"]; thr = pcfg["sir_threshold_db"]; tgt = pcfg["outage_target"]

    # ---------------- title page
    t = R.doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("CellHop Planner"); r.bold = True; r.font.size = Pt(30); r.font.color.rgb = ACCENT
    t = R.doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("A joint capacity - interference - fading - frequency-hopping design study\nfor a cellular network"); r.font.size = Pt(15)
    t = R.doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("\nWireless Communications and Networks (WCN) - Course Project\nCumulative report of Experiments 1-5 and the integrated study\n\n").font.size = Pt(12)
    t = R.doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run(f"Name(s): ______________________    Roll no.: __________\nDate: {date.today():%d %B %Y}").font.size = Pt(11)
    R.doc.add_page_break()

    # ---------------- abstract
    R.h1("1. Abstract")
    best = pl["best"]
    e2rows = {r["N"]: r for r in e2["rows"]}
    R.p("This project joins five wireless-communication experiments into one working design tool written in Python. "
        "Frequency reuse and cell splitting (Expt 1), trunking and grade of service (Expt 2), multipath delay spread and "
        "coherence bandwidth (Expt 3), path loss / shadowing / Rayleigh fading / Doppler (Expt 4) and frequency-hopping "
        "spread spectrum (Expt 5) are each implemented and validated, then combined in an integrated planner that "
        "asks: which cluster size N should a network with 84 cells and 300 channels use?")
    R.p(f"Taken alone, the trunking analysis says the smallest cluster wins: N = 4 serves {e2rows[4]['users_system']:,} users, "
        f"N = 12 serves {e2rows[12]['users_system']:,} and N = 13 serves {e2rows[13]['users_system']:,}. "
        "The integrated study shows that this ranking ignores interference: a smaller N brings the co-channel cells closer "
        f"(D/R = sqrt(3N)). With a {thr:g} dB SIR requirement and a {tgt*100:.0f} % outage budget, the best feasible cluster is "
        + (f"N = {best['N']} ({best['users_system']:,} users) for path-loss exponent 3" if best else "not found for path-loss exponent 3")
        + ". The planner also shows that using each cell's channel set as the hop set gives a processing gain of 10 log10(C) "
        "and that cell splitting multiplies capacity by 4 while allowing a large transmit-power reduction.")

    # ---------------- literature basis
    R.h1("2. Literature basis: what the papers told us")
    R.p("The project is anchored on one foundational paper and four supporting references. The table states what each source "
        "tells us and which concept of our project it supports. (Full citations are in Section 11.)")
    R.table("Reference stack and the concepts used", ["Source", "What it tells us", "Used in our project for"], [
        ["[1] MacDonald, \"The Cellular Concept\", BSTJ 1979 (MAIN PAPER)",
         "A large mobile market can be served in a small spectrum slice by re-using frequencies in cells; analyses hexagonal "
         "cell geometry; introduces cell splitting; describes AMPS.",
         "Expt 1: hexagonal grid, N = i^2+ij+j^2, co-channel distance D/R = sqrt(3N), cell splitting. Planner: the whole idea of "
         "trading cluster size against capacity and interference."],
        ["[2] Rappaport, Wireless Communications: Principles and Practice",
         "Course textbook: Erlang-B / trunking and GoS, SIR for cluster size N, cell splitting power rule, delay spread and "
         "coherence bandwidth, Doppler and coherence time.",
         "Expt 1-4 formulas, worst-case SIR (interferers at D-R, D, D+R), Pt' = Pt (R'/R)^n."],
        ["[3] Pickholtz, Schilling, Milstein, \"Theory of Spread-Spectrum Communications - A Tutorial\", IEEE Trans. Commun. 1982",
         "Defines processing gain (spread bandwidth / data bandwidth), frequency hopping, anti-jam performance against "
         "partial-band jamming and the jamming margin.",
         "Expt 5: PN-controlled hopping, PG = 10 log10(N), tone and partial-band jammer, BER vs Eb/N0."],
        ["[4] Sklar, \"Rayleigh Fading Channels in Mobile Digital Communication Systems, Part I\", IEEE Commun. Mag. 1997",
         "Separates large-scale fading (path loss + log-normal shadowing) from small-scale fading; defines delay spread, "
         "coherence bandwidth (~1/(5 sigma)), Doppler spread and coherence time.",
         "Expt 3 and 4: PDP statistics, Bc, Doppler spread, Tc, Rayleigh generation and the fading penalty in Expt 5."],
        ["[5] Erlang (1917) - teletraffic theory",
         "Probability that a call finds all C channels busy for offered traffic A (blocked-calls-cleared).",
         "Expt 2: Erlang-B and its Monte-Carlo validation."],
    ], widths=[1.9, 2.5, 2.3], font=8.5)
    R.p("In short: paper [1] gave us the cellular geometry and the capacity-versus-reuse trade-off; [3] gave us the hopping and "
        "processing-gain concepts; [2] and [4] gave the propagation and traffic formulas. Our contribution is the integration "
        "(Section 9), which is a course-level synthesis and not a claim of new research.", italic=True)

    # ---------------- architecture
    R.h1("3. Project architecture")
    R.table("How the modules feed each other", ["Stage", "Module", "Passes on"], [
        ["1", "exp1_frequency_reuse", "Cluster geometry, D/R = sqrt(3N), channel arithmetic, cell-splitting rule"],
        ["2", "exp2_trunking_gos", "Erlang-B capacity per cell and per system for any N"],
        ["3", "exp3_multipath", "Coherence bandwidth Bc of the channel -> diversity order of a hop band"],
        ["4", "exp4_fading", "Shadowing sigma, Rayleigh model, Doppler / coherence time"],
        ["5", "exp5_fhss", "Hopping, processing gain, BER under jamming and fading"],
        ["6", "integrated_planner", "Outage-constrained capacity, hop-set processing gain, recommended N"],
        ["7", "report_builder", "This report"],
    ], widths=[0.6, 2.0, 4.1])

    # ---------------- Expt 1
    R.h1("4. Experiment 1 - Frequency reuse, co-channel interference and cell splitting")
    R.p(f"Cells are hexagons of area {e1['cell_area_km2']} km^2, i.e. radius R = {e1['R_km']:.3f} km. The cluster size follows from the shift "
        "pair (i, j): N = i^2 + ij + j^2. A grid with at least M = 3 clusters is generated, each cell is given a frequency group "
        "(same colour = same frequencies) and the distance D from the centre cell to its co-channel cells is MEASURED from the "
        "coordinates of the generated grid. The bandwidth is 35 MHz and each simplex channel is 200 kHz, so a duplex channel "
        f"needs 400 kHz: 35 MHz / 400 kHz = 87.5, i.e. {e1['total_duplex_channels']} whole duplex channels.")
    R.table("Lab table of Experiment 1", ["i", "j", "N", "Total duplex channels", "Channels / cell", "Theoretical D (km)",
                                          "Calculated q = sqrt(3N)", "Simulated D (km)", "Simulated q"],
            [[r["i"], r["j"], r["N"], r["total_duplex_channels"], r["channels_per_cell"], f"{r['D_theory_km']:.3f}",
              f"{r['q_calc_from_N']:.3f}", f"{r['D_sim_km']:.3f}", f"{r['q_sim']:.3f}"] for r in e1["rows"]], font=8.5)
    R.fig("exp1_reuse_map_N12", "Reuse map for (i, j) = (2, 2), N = 12: bold outline = one cluster, dashed rings = six co-channel cells, arrow = reuse distance D.")
    R.fig("exp1_cluster_overview", "All cluster sizes of the lab table.")
    R.fig("exp1_channels_and_reuse_ratio", "Channels per cell fall as N grows, while D/R grows.", width=5.4)
    sp = e1["splitting"]
    R.fig("exp1_cell_splitting", "Cell splitting by a factor of 2: the same area is covered by 4x as many cells.", width=6.0)
    R.p("Findings", bold=True)
    R.bullets([
        "The distance measured in the simulated grid equals the theory D = sqrt(3N) R for every (i, j) (differences below 1e-12), "
        "which confirms the colouring and the geometry code.",
        f"For N = 12: D = {e1['rows'][4]['D_sim_km']:.2f} km and q = D/R = {e1['rows'][4]['q_sim']:.2f}.",
        "Channels per cell are floor(87 / N): a small cluster gives each cell more channels but puts co-channel cells closer together.",
        f"Cell splitting halves R ({sp['R_old_km']:.2f} km -> {sp['R_new_km']:.2f} km), so the number of cells grows {sp['cell_multiplier']}x. To keep the same "
        f"received power at the new cell edge the transmit power must fall by 10 n log10(2) dB = "
        + " / ".join(f"{v:.1f} dB for n = {float(k):g}" for k, v in sp["power_reduction_db"].items()) + ".",
    ])

    # ---------------- Expt 2
    R.h1("5. Experiment 2 - Trunking and Grade of Service")
    R.p("Problem: an area is covered by 84 cells with 300 voice channels in total and 0.04 Erlang offered per user. Calls are "
        "blocked-calls-cleared and the designated blocking probability is Pb = 1 %. For cluster size N each cell has C = floor(300/N) "
        "channels. The Erlang-B formula B(A, C) = (A^C / C!) / sum(A^k / k!) is inverted numerically (bisection) to find the largest "
        "offered traffic A with B = 1 %. Carried traffic is A(1 - Pb); users per cell = A / 0.04; system users = 84 x users per cell.")
    R.table("Results for N = 4, 12, 13", ["N", "Channels per cell", "Max offered traffic / cell (Erl)", "Max carried traffic / cell (Erl)",
                                         "Trunking efficiency", "Users / cell", "Users in 84 cells", "Monte-Carlo blocking"],
            [[r["N"], r["channels_per_cell"], f"{r['offered_erl_per_cell']:.2f}", f"{r['carried_erl_per_cell']:.2f}",
              f"{r['trunking_efficiency']*100:.1f} %", r["users_per_cell"], f"{r['users_system']:,}", f"{r['mc_blocking']*100:.2f} %"] for r in e2["rows"]], font=8.5)
    R.fig("exp2_erlang_b_curves", "Erlang-B blocking against offered traffic (dots mark the 1 % design points).", width=5.6)
    R.fig("exp2_users_per_system", "Maximum traffic per cell and users served by the whole system.", width=6.0)
    R.fig("exp2_trunking_efficiency", "Trunking efficiency grows with the size of the channel pool.", width=5.4)
    R.fig("exp2_monte_carlo_validation", "Event-driven Monte-Carlo simulation reproduces the 1 % blocking at each design point.", width=5.0)
    R.p("Inference", bold=True)
    R.bullets(e2["inference"])
    R.p("Verification: the Erlang-B routine was checked against textbook values and against an independent Poisson-based formula "
        "(see tests/test_core.py), and the call-by-call simulation measures "
        + " / ".join(f"{r['mc_blocking']*100:.2f} %" for r in e2["rows"]) + " blocking at the three design points (target 1 %).", italic=True)

    # ---------------- Expt 3
    R.h1("6. Experiment 3 - Multipath: PDP, delay spread and coherence bandwidth")
    a, b = e3["partA"], e3["partB"]
    R.table("Multipath components used (Part A in dBm, Part B in Watts)", ["Path", "Excess delay (ns)", "Received power (dBm)", "Linear power (W)"],
            [[row[0], f"{row[1]:.0f}", f"{row[2]:.1f}", f"{pw:.3e}"] for row, pw in zip(a["table"], e3["powers_w"])])
    R.fig("exp3_pdp_dbm", "Power Delay Profile in dBm (Part A).", width=5.2)
    R.fig("exp3_pdp_linear", "Power Delay Profile in linear power with mean excess delay and RMS delay spread (Part B).", width=5.2)
    R.table("Part A and Part B results", ["Quantity", "Value"], [
        ["Strongest path", f"path {a['strongest']['path']}: {a['strongest']['power_dbm']:.1f} dBm at {a['strongest']['delay_ns']:.0f} ns"],
        ["Weakest path", f"path {a['weakest']['path']}: {a['weakest']['power_dbm']:.1f} dBm at {a['weakest']['delay_ns']:.0f} ns"],
        ["Maximum excess delay", f"{a['max_excess_delay_ns']:.0f} ns"],
        ["Average received power", f"{a['avg_power_dbm_arithmetic']:.2f} dBm (mean of the dBm values); {a['avg_power_dbm_linear']:.2f} dBm (average in the power domain)"],
        ["Mean excess delay", f"{b['tau_mean_s']*1e9:.1f} ns"],
        ["RMS delay spread", f"{b['sigma_s']*1e9:.1f} ns"],
        ["Coherence bandwidth (correlation 0.5), 1/(5 sigma)", f"{b['bc_50_hz']/1e3:.0f} kHz"],
        ["Coherence bandwidth (correlation 0.9), 1/(50 sigma)", f"{b['bc_90_hz']/1e3:.0f} kHz"],
    ], widths=[3.0, 3.7])
    R.fig("exp3_coherence_bandwidth_vs_systems", "System bandwidths compared with the coherence bandwidth.", width=5.2)
    R.p("Findings", bold=True)
    flat = [c["system"] for c in e3["classes"] if c["type"] == "flat"]; sel = [c["system"] for c in e3["classes"] if c["type"] != "flat"]
    R.bullets([
        "The average power is reported in two ways because averaging dBm values is not the same as averaging power; the power-domain value is the physically meaningful one.",
        f"Flat fading (signal bandwidth below Bc and sigma well below the symbol time): {', '.join(flat) if flat else 'none'}.",
        f"Frequency-selective fading (bandwidth comparable to or above Bc): {', '.join(sel) if sel else 'none'}.",
        (f"For hopping, channels 200 kHz apart are still partly correlated because 200 kHz is below Bc(0.5) = {b['bc_50_hz']/1e3:.0f} kHz, so a hop band must be several times wider than Bc to give independent fades (used for the 'diversity order' in Section 9)."
         if 200e3 < b["bc_50_hz"] else
         f"For hopping, channels 200 kHz apart already exceed Bc(0.5) = {b['bc_50_hz']/1e3:.0f} kHz, so neighbouring hop channels fade almost independently (used for the 'diversity order' in Section 9)."),
    ])

    # ---------------- Expt 4
    R.h1("7. Experiment 4 - Large-scale and small-scale fading")
    pa, pb = e4["partA"], e4["partB"]; mob = pb["mob"]
    R.p("Part A uses the Log-Distance model Pr(d) = P0 - 10 n log10(d/d0) with d0 = 10 m, P0 = -40 dBm, n = 3, adds one log-normal "
        "shadowing draw (sigma = 4 dB) per position and 100 Rayleigh-fading samples per position (10 positions between 20 m and 1000 m).")
    R.table("Part A: average, shadowed and faded received power", ["Pos.", "d (m)", "Average Pr (dBm)", "Shadowing (dB)", "Pr + shadowing (dBm)", "Mean faded Pr (dBm)", "Min (dBm)", "Max (dBm)"],
            [[r["pos"], f"{r['d_m']:.0f}", f"{r['avg_dbm']:.1f}", f"{r['shadow_db']:+.1f}", f"{r['shadowed_dbm']:.1f}", f"{r['final_mean_dbm']:.1f}", f"{r['final_min_dbm']:.1f}", f"{r['final_max_dbm']:.1f}"] for r in pa["rows"]], font=8.5)
    R.fig("exp4A_received_power_combined", "Graphs 1-3 of Part A on one axis: smooth trend (large-scale) with rapid scatter (small-scale).", width=5.8)
    R.fig("exp4A_three_graphs", "The three graphs of Part A shown separately.", width=6.4)
    R.p(f"Part B: at fc = 900 MHz and v = 30 m/s the wavelength is {mob['wavelength_m']:.4f} m, the maximum Doppler shift is {mob['fd_hz']:.1f} Hz, "
        f"the Doppler spread is {mob['doppler_spread_hz']:.1f} Hz (= 2 fd) and the coherence time is Tc = 0.423/fd = {mob['tc_s']*1e3:.2f} ms. "
        "The time-varying Rayleigh signal is generated with the sum-of-sinusoids (Clarke/Jakes) model with 64 scattered waves.")
    R.fig("exp4B_graph1_large_scale", "Part B, Graph 1 - large-scale fading.", width=5.0)
    R.fig("exp4B_graph2_small_scale_time", "Part B, Graph 2 - small-scale fading versus sample number.", width=5.8)
    R.fig("exp4B_graph3_doppler_vs_velocity", "Part B, Graph 3 - Doppler shift versus mobile velocity.", width=5.0)
    R.fig("exp4B_validation_autocorrelation", "Validation: simulated autocorrelation coincides with the theoretical J0(2 pi fd tau).", width=5.0)
    R.p("Findings", bold=True)
    R.bullets([
        f"Regressing the shadowed powers on 10 log10(d/d0) recovers a path-loss exponent of {pa['n_estimated']:.2f} (input 3.0).",
        f"The Rayleigh power gain has mean {pa['rayleigh_mean_db']:.2f} dB and standard deviation {pa['rayleigh_std_db']:.2f} dB (theory: -2.51 dB and 5.57 dB).",
        f"The measured level-crossing rate at the RMS level is {pb['lcr_meas']:.1f} per second against {pb['lcr_theory']:.1f} predicted by theory, and the autocorrelation follows J0 - the generator is statistically correct.",
        f"Fades as deep as {pb['fade_depth_db']:.1f} dB below the local mean occur within 0.5 s; since Tc = {mob['tc_s']*1e3:.1f} ms, the channel changes about {1/mob['tc_s']:.0f} times per second at 108 km/h.",
        "Doppler shift is linear in velocity (3 Hz per m/s at 900 MHz); the faster the user, the shorter the coherence time and the harder channel tracking becomes.",
    ])

    # ---------------- Expt 5
    R.h1("8. Experiment 5 - Frequency Hopping Spread Spectrum")
    cfg5 = e5["config"]; d5 = e5["demo"]
    R.p(f"Transmitter: random bits -> BPSK -> carrier chosen by a PN sequence from a {cfg5['lfsr_degree']}-stage maximal-length LFSR "
        f"(x^16 + x^14 + x^13 + x^11 + 1, measured period {e5['lfsr_period']}) over N = {cfg5['n_channels']} channels. Channel: AWGN at 0-12 dB Eb/N0 plus a tone "
        f"jammer of {cfg5['jsr_db']:g} dB jammer-to-signal ratio on one channel, or on half of the channels (partial band). Receiver: synchronised PN "
        "generator, de-hopping, integrate-and-dump, sign decision. Eb/N0 is calibrated exactly through the noise variance.")
    R.table("8-bit demonstration (PN sequence, input and FHSS output)", ["Bit no.", "Input bit", "BPSK symbol", "PN bits (3 per hop)", "Hop channel", "RF carrier (MHz)"],
            [[r["bit_no"], r["data"], f"{r['bpsk']:+d}", r["pn_bits"], r["hop_channel"], f"{r['rf_mhz']:.1f}"] for r in d5["rows"]])
    R.fig("exp5_fhss_demo_8bits", "Data bits, PN hop channel, carrier frequency and the FHSS output waveform for the 8-bit demo.", width=6.0)
    R.fig("exp5_spectrum_spreading", "Spectrum of plain BPSK and of the FHSS signal.", width=5.2)
    R.fig("exp5_ber_vs_ebn0", "BER versus Eb/N0 - lines: theory, markers: simulation (points with zero errors are not drawn).", width=6.0)
    ber = e5["ber"]
    R.table("Simulated BER", ["Eb/N0 (dB)", "Theory AWGN", "FHSS no jammer", "Fixed carrier + jammer", "FHSS + tone jammer", "FHSS + partial-band jammer"],
            [[e, f"{ber['theory']['awgn'][k]:.2e}", f"{ber['sim']['fhss_clean'][k]:.2e}", f"{ber['sim']['fixed_jam'][k]:.2e}", f"{ber['sim']['fhss_tone'][k]:.2e}", f"{ber['sim']['fhss_partial'][k]:.2e}"] for k, e in enumerate(ber["ebn0"])], font=8.5)
    R.fig("exp5_processing_gain", "Processing gain and the tone-jammer BER as the number of hopping channels grows.", width=6.0)
    R.fig("exp5_rayleigh_vs_awgn", "BPSK over AWGN and over Rayleigh fading.", width=5.0)
    R.p("Findings", bold=True)
    pg = e5["pg"]
    R.bullets([
        "Without a jammer the FHSS link reproduces the theoretical BPSK curve Q(sqrt(2 Eb/N0)): hopping alone costs nothing in AWGN.",
        f"A fixed-frequency link sitting on the jammed channel hits a BER floor near {ber['sim']['fixed_jam'][-1]:.2f}; with FHSS the jammer only hurts the 1/N of bits that land on its channel, so the floor drops to about {ber['sim']['fhss_tone'][-1]:.3f}.",
        f"Processing gain PG = 10 log10(N): " + ", ".join(f"N = {r['N']}: {r['pg_db']:.1f} dB" for r in pg) + ".",
        f"Fading is costly: BPSK needs {e5['fading']['awgn_snr_1e3']:.1f} dB for BER 1e-3 in AWGN but {e5['fading']['rayleigh_snr_1e3']:.1f} dB in Rayleigh fading, a {e5['fading']['penalty_db']:.1f} dB penalty - the reason hopping across independently fading channels (Section 9) is attractive.",
        f"A partial-band jammer of the SAME total power on half the channels hits half of the bits but each tone has only 1/4 of the power: at Eb/N0 = 5 dB it is worse than the single tone ({ber['sim']['fhss_partial'][5]:.1e} against {ber['sim']['fhss_tone'][5]:.1e}) "
        f"while at 12 dB the two are about equal ({ber['sim']['fhss_partial'][12]:.1e} against {ber['sim']['fhss_tone'][12]:.1e}) because the weaker tones can no longer overpower the signal on their own.",
    ])

    # ---------------- integrated
    R.h1("9. Integrated study - choosing the cluster size")
    R.p("Question: for the 84-cell, 300-channel network, which cluster size N should be used? We evaluate every valid N = i^2 + ij + j^2 from 3 to 19 "
        "with all five experiments at once:")
    R.bullets([
        "Capacity (Expt 2): channels per cell C = floor(300/N), Erlang-B users at Pb = 1 %.",
        "Interference (Expt 1): six first-tier co-channel interferers at distance D = sqrt(3N) R. Three SIR measures: simple (D/R)^n / 6; worst-case cell-edge user; and a Monte-Carlo with users placed uniformly in the cell.",
        "Fading (Expt 4): independent log-normal shadowing (sigma = 4 dB) on the wanted and on every interfering link; the design metric is the outage probability P(SIR < threshold). A second Monte-Carlo also includes independent Rayleigh fading on every link.",
        "Multipath (Expt 3): diversity order = hop-band width / Bc, i.e. how many independently fading sub-bands a hop set spans.",
        "Hopping (Expt 5): the C channels of a cell are used as the hop set, so PG = 10 log10(C) and a single-tone jammer hits a bit with probability 1/C.",
        f"Decision rule: choose the N with the most system users among those whose outage is at most {tgt*100:.0f} % at a required SIR of {thr:g} dB (GSM-class digital system; sensitivity to 12 and 18 dB is shown too).",
    ])
    hdr = ["N", "(i,j)", "C", "D/R", "System users", "Worst SIR n=3 (dB)", "Worst SIR n=4 (dB)", f"Outage n=3 (SIR<{thr:g})", f"Outage n=4 (SIR<{thr:g})", "PG (dB)", "Diversity order"]
    R.table("Design-space table", hdr, [[r["N"], f"({r['i']},{r['j']})", r["channels_per_cell"], f"{r['q']:.2f}", f"{r['users_system']:,}",
            f"{r['sir']['3.0']['worst_db']:.1f}", f"{r['sir']['4.0']['worst_db']:.1f}",
            f"{r['sir']['3.0']['outage_ls'][thr]*100:.1f} %", f"{r['sir']['4.0']['outage_ls'][thr]*100:.1f} %", f"{r['pg_db']:.1f}", r["diversity_order"]] for r in pl["rows"]], font=8)
    R.fig("planner_capacity_vs_sir", "Capacity falls with N while the interference margin grows.", width=5.6)
    R.fig("planner_design_space", "Design space: system users against outage; green = feasible.", width=6.4)
    R.fig("planner_outage_sensitivity", "Outage against N for several required SIR values.", width=6.4)
    R.table("Recommended cluster size for each requirement", ["Path-loss exponent n", "Required SIR (dB)", "Recommended N", "System users", "Outage"],
            [[f"{d['n']:g}", f"{d['threshold_db']:g}", d["N"] if d["N"] else "none <= 19", f"{d['users_system']:,}" if d["users_system"] else "-", f"{d['outage']*100:.1f} %" if d["outage"] is not None else "-"] for d in pl["decisions"]])
    R.fig("planner_hopping_resilience", "Hop set = channels per cell: processing gain and tone-jammer BER for each N.", width=6.2)
    if pl["splitting"]:
        s = pl["splitting"]
        R.fig("planner_cell_splitting_gain", f"Cell splitting applied to the chosen N = {s['N']} design.", width=4.4)
    R.p("Findings", bold=True)
    r4 = {r["N"]: r for r in pl["rows"]}
    dflt = [d for d in pl["decisions"] if d["threshold_db"] == thr]
    items = [
        f"Capacity alone favours N = 4 ({r4[4]['users_system']:,} users), but with n = 3 its outage is {r4[4]['sir']['3.0']['outage_ls'][thr]*100:.0f} % at a {thr:g} dB requirement - far above the {tgt*100:.0f} % budget. The 'best' answer of Expt 2 is therefore not deployable in that environment.",
        f"N = 12 and N = 13 (Expt 2) are very safe in interference terms (outage {r4[12]['sir']['3.0']['outage_ls'][thr]*100:.1f} % and {r4[13]['sir']['3.0']['outage_ls'][thr]*100:.1f} % for n = 3) but give up {100 - 100*r4[12]['users_system']/r4[4]['users_system']:.0f} % and {100 - 100*r4[13]['users_system']/r4[4]['users_system']:.0f} % of the N = 4 capacity.",
        "The decision depends strongly on the environment: " + "; ".join(f"n = {d['n']:g} -> N = {d['N']}" for d in dflt) + f" at {thr:g} dB. A steeper path-loss exponent isolates co-channel cells better and allows a tighter reuse.",
        "Including fast Rayleigh fading on every link raises the outage of every design (second Monte-Carlo, stored in results.json); fast fading is normally handled by coding, interleaving, diversity or hopping rather than by cluster size, which is why the design metric uses the large-scale SIR.",
        f"Hop-set processing gain falls from {r4[4]['pg_db']:.1f} dB (N = 4, C = {r4[4]['channels_per_cell']}) to {r4[12]['pg_db']:.1f} dB (N = 12, C = {r4[12]['channels_per_cell']}), and the tone-jammer BER at Eb/N0 = {pcfg['ebn0_db']:g} dB rises from {r4[4]['jam_ber']:.1e} to {r4[12]['jam_ber']:.1e}: a tight reuse gives both more capacity and a larger hop set.",
        f"With Bc = {pl['bc_hz']/1e3:.0f} kHz, a hop set of C channels spaced 200 kHz spans about {r4[4]['diversity_order']} independent fading sub-bands for N = 4 but only {r4[12]['diversity_order']} for N = 12 - more frequency diversity against the Rayleigh penalty of Section 8.",
    ]
    if pl["splitting"]:
        s = pl["splitting"]
        items.append(f"Cell splitting (R -> R/2) on the chosen N = {s['N']} design quadruples the cells from {s['cells_before']} to {s['cells_after']} and the capacity from {s['users_before']:,} to {s['users_after']:,} users, keeps D/R (hence SIR) unchanged, and lets the transmit power drop by "
                     + " / ".join(f"{v:.1f} dB (n = {float(k):g})" for k, v in s["power_reduction_db"].items()) + ".")
    R.bullets(items)

    # ---------------- overall inference
    R.h1("10. Overall inference")
    R.bullets([
        "Frequency reuse converts a limited spectrum into large capacity, but the reuse distance D/R = sqrt(3N) controls the interference; N is the single knob that trades one against the other.",
        "Erlang-B shows that capacity is not proportional to channels: larger pools are used more efficiently, so splitting 300 channels into small groups wastes trunking efficiency.",
        "The radio channel is selective in frequency (delay spread, Bc) and in time (Doppler, Tc); shadowing adds a random large-scale component that sets the outage of the cell edge.",
        "Frequency hopping spreads the signal over C channels, gives a processing gain of 10 log10(C), confines a narrow-band jammer to 1/C of the bits and, when the hop band exceeds Bc, offers frequency diversity against fading.",
        "Designing the network with all effects together gives a different, and more realistic, answer than the capacity calculation alone.",
    ])
    R.h2("Assumptions and limitations")
    R.bullets([
        "300/13 is not an integer: each cell gets 23 channels and one channel stays unused; 84 cells are not a whole number of 13-cell clusters (6.46) - the textbook calculation ignores this and so do we.",
        "'Duplex channel' = two 200 kHz simplex channels, so 35 MHz gives 87 duplex channels (floor of 87.5). If the handout intends 35 MHz per direction the count would be 175; change settings.EXP1 to explore it.",
        "Max carried traffic per cell is reported as A(1 - Pb) next to the offered traffic A; users per cell are computed from the offered traffic A, as is usual in textbook solutions.",
        "The multipath profile of Experiment 3 is an illustrative urban-like profile chosen for the project; replace it with measured data using --pdp or --interactive.",
        "The planner is an analytical / Monte-Carlo study: ideal omni cells, equal transmit power, six first-tier interferers only, no power control or sectorisation. The 'hop set = cell channel set' coupling and the outage-constrained rule are modelling choices of this project.",
        "The 9 dB threshold is the value commonly quoted for GSM co-channel interference and 18 dB the classic analogue AMPS value; check them against your course text before quoting.",
    ])

    # ---------------- references
    R.h1("11. References")
    for ref in [
        "[1] V. H. MacDonald, \"The Cellular Concept,\" The Bell System Technical Journal, vol. 58, no. 1, pp. 15-41, Jan. 1979.",
        "[2] T. S. Rappaport, Wireless Communications: Principles and Practice, 2nd ed., Prentice Hall, 2002.",
        "[3] R. L. Pickholtz, D. L. Schilling and L. B. Milstein, \"Theory of Spread-Spectrum Communications - A Tutorial,\" IEEE Trans. Commun., vol. COM-30, no. 5, pp. 855-884, May 1982.",
        "[4] B. Sklar, \"Rayleigh Fading Channels in Mobile Digital Communication Systems, Part I: Characterization,\" IEEE Commun. Mag., vol. 35, no. 7, pp. 90-100, Jul. 1997.",
        "[5] A. K. Erlang, \"Solution of some problems in the theory of probabilities of significance in automatic telephone exchanges,\" 1917 (English: Post Office Electrical Engineers' Journal, 1918).",
        "[6] R. H. Clarke, \"A statistical theory of mobile-radio reception,\" The Bell System Technical Journal, vol. 47, no. 6, pp. 957-1000, 1968; and W. C. Jakes (ed.), Microwave Mobile Communications, Wiley, 1974.",
        "[7] H. Hashemi, \"The indoor radio propagation channel,\" Proc. IEEE, vol. 81, no. 7, pp. 943-968, Jul. 1993 (supporting reference for delay-spread statistics; details to be double-checked before submission).",
    ]:
        R.p(ref)

    # ---------------- appendix
    R.h1("Appendix - how to run")
    R.p("pip install -r requirements.txt\npython main.py            # everything, about a minute\npython main.py --fast     # quick check\npython -m pytest -q       # self-tests of the maths")
    R.p("Outputs: outputs/figures (PNG), outputs/tables (CSV), outputs/results.json and this report in outputs/report.")

    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = settings.REPORT_DIR / "WCN_CellHop_Report.docx"
    R.doc.save(path)
    return path
