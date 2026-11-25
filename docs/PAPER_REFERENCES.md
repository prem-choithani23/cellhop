# Paper basis of the project

**Main paper:** V. H. MacDonald, "The Cellular Concept," *The Bell System Technical Journal*, vol. 58, no. 1,
pp. 15–41, January 1979.

## What the main paper tells us
The paper argues that a cellular system can serve a large mobile-telephone market within a limited slice of spectrum
at reasonable cost. It introduces **frequency reuse**, analyses the mathematics of **hexagonal cell geometry**, and
describes **cell splitting** as the way to grow capacity; it also describes the AMPS system.

## Concepts of our project that come from it
| Concept in the paper | Where it is in our project |
|---|---|
| Frequency reuse with clusters of N cells | Expt 1 — `exp1_frequency_reuse.py`, `hexgrid.py` |
| Hexagon geometry, N = i² + ij + j², D/R = √(3N) | `hexgrid.py`, Expt 1 lab table |
| Co-channel interference falls as D/R grows | Expt 1 and the SIR part of `integrated_planner.py` |
| Cell splitting (smaller cells → more capacity) | Expt 1 splitting figure; splitting what-if in the planner |
| Capacity vs. number of channels per cell | Expt 2 (Erlang-B) and the planner |

## Supporting references
| Reference | What it tells us | Used for | Checked online in this session? |
|---|---|---|---|
| R. L. Pickholtz, D. L. Schilling, L. B. Milstein, "Theory of Spread-Spectrum Communications — A Tutorial," *IEEE Trans. Commun.*, vol. COM-30, no. 5, pp. 855–884, May 1982 | Processing gain = spread bandwidth / data bandwidth; frequency hopping; anti-jam performance against partial-band jamming; jamming margin | Expt 5, hop-set processing gain in the planner | Yes (full text) |
| B. Sklar, "Rayleigh Fading Channels in Mobile Digital Communication Systems, Part I: Characterization," *IEEE Commun. Mag.*, vol. 35, no. 7, pp. 90–100, July 1997 | Large-scale vs small-scale fading; delay spread; coherence bandwidth ≈ 1/(5σ); Doppler spread; coherence time | Expt 3 and 4 | Yes (title, author, journal, date, topics; volume/issue from memory) |
| V. H. MacDonald (above) | see above | Expt 1, 2, planner | Yes (journal, volume, issue, pages, date, summary) |
| T. S. Rappaport, *Wireless Communications: Principles and Practice*, 2nd ed., Prentice Hall, 2002 | Course textbook: trunking, SIR, delay spread, Doppler, cell splitting power rule | Formulas in all experiments | Not checked (textbook) |
| A. K. Erlang (1917) | Blocked-calls-cleared loss formula | Expt 2 | Not checked (classic) |
| R. H. Clarke, *BSTJ* 47(6), 1968; W. C. Jakes, *Microwave Mobile Communications*, 1974 | Sum-of-sinusoids model of Rayleigh fading | Expt 4 generator | Not checked |
| H. Hashemi, "The indoor radio propagation channel," *Proc. IEEE*, vol. 81, no. 7, pp. 943–968, 1993 | Delay-spread statistics of real channels | Context for Expt 3 | **No — double-check the details before submitting** |

## Honest note
The integrated study (hop set = cell channel set; outage-constrained capacity) is our own course-level synthesis of
standard building blocks. It is not a result taken from these papers.
