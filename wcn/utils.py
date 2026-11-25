# =============================================================================
# FILE        : wcn/utils.py
# PROJECT     : CellHop Planner
# WHAT IT IS  : Small shared helpers used by every experiment module:
#               unit conversions (dB <-> linear), the Q-function, a common
#               matplotlib style, and functions that save figures / tables / JSON
#               into the outputs/ folder.
# WHAT IT DOES: * db_to_lin / lin_to_db / dbm_to_watt / watt_to_dbm / q_function
#               * apply_style()  -> one consistent chart look for all figures
#               * save_fig()     -> writes a PNG into outputs/figures/
#               * save_table()   -> writes a CSV into outputs/tables/
#               * save_results() -> writes outputs/results.json (feeds the report)
# LAST STEP   : config/settings.py supplied the folder paths used here.
# NEXT STEP   : Every wcn/exp*.py module imports these helpers to compute and save outputs.
# =============================================================================

import csv                       # csv: write tables in a format Excel can open
import json                      # json: store all numerical results in one file
from pathlib import Path         # Path: file-system paths

import numpy as np               # numpy: numerical arrays and maths
import matplotlib                # matplotlib: plotting library
matplotlib.use("Agg")            # "Agg" backend = draw to files, no pop-up window needed
import matplotlib.pyplot as plt  # pyplot: the plotting interface
from scipy.special import erfc   # erfc: complementary error function, needed for Q(x)

from config import settings      # folder paths

# Validated colour-blind-safe categorical palette (blue, orange, aqua, violet, red, yellow, magenta, green)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e34948", "#eda100", "#e87ba4", "#008300"]
INK = "#222222"          # main text colour
MUTED = "#6b6b6b"        # secondary text / grid colour


def apply_style():
    """Set one clean matplotlib style for every figure of the project."""
    plt.rcParams.update({
        "figure.dpi": 110,                 # on-screen resolution
        "savefig.dpi": 160,                # saved-file resolution (sharp in the .docx report)
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),  # default colour order
        "axes.spines.top": False,          # remove top frame line (cleaner look)
        "axes.spines.right": False,        # remove right frame line
        "axes.edgecolor": MUTED,           # axis line colour
        "axes.labelcolor": INK,            # axis label colour
        "xtick.color": INK, "ytick.color": INK,   # tick label colours
        "text.color": INK,                 # general text colour
        "axes.grid": True,                 # light grid for reading values
        "grid.color": "#dddddd", "grid.linewidth": 0.7,
        "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.labelsize": 10, "legend.frameon": False, "font.size": 10,
    })


# ------------------------------------------------------------- unit conversions
def db_to_lin(x_db):
    """Convert decibels to a linear power ratio: lin = 10^(dB/10)."""
    return 10.0 ** (np.asarray(x_db, dtype=float) / 10.0)


def lin_to_db(x_lin):
    """Convert a linear power ratio to decibels: dB = 10*log10(lin)."""
    return 10.0 * np.log10(np.asarray(x_lin, dtype=float))


def dbm_to_watt(p_dbm):
    """dBm -> Watt.  0 dBm = 1 mW, so P[W] = 10^((dBm-30)/10)."""
    return 10.0 ** ((np.asarray(p_dbm, dtype=float) - 30.0) / 10.0)


def watt_to_dbm(p_w):
    """Watt -> dBm."""
    return 10.0 * np.log10(np.asarray(p_w, dtype=float)) + 30.0


def q_function(x):
    """Gaussian tail probability Q(x) = 0.5*erfc(x/sqrt(2)); used for theoretical BER."""
    return 0.5 * erfc(np.asarray(x, dtype=float) / np.sqrt(2.0))


# ------------------------------------------------------------------ file output
def ensure_output_dirs():
    """Create outputs/, outputs/figures, outputs/tables and outputs/report if missing."""
    for folder in (settings.FIG_DIR, settings.TABLE_DIR, settings.REPORT_DIR):
        folder.mkdir(parents=True, exist_ok=True)   # parents=True creates missing parents too


def save_fig(fig, name):
    """Save a matplotlib figure as outputs/figures/<name>.png and close it. Returns the path."""
    ensure_output_dirs()                            # make sure the folder exists
    path = settings.FIG_DIR / f"{name}.png"         # build the full file path
    fig.savefig(path, bbox_inches="tight", facecolor="white")  # write PNG, trim white margins
    plt.close(fig)                                  # free memory (important when saving many figures)
    return path


def save_table(rows, header, name):
    """Save a list of rows as outputs/tables/<name>.csv. `header` is the list of column names."""
    ensure_output_dirs()
    path = settings.TABLE_DIR / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:   # open file for writing
        writer = csv.writer(fh)                                  # CSV writer object
        writer.writerow(header)                                  # first line = column names
        writer.writerows(rows)                                   # remaining lines = data
    return path


def _to_jsonable(obj):
    """Helper for json.dump: turn numpy numbers/arrays and Paths into plain Python types."""
    if isinstance(obj, (np.integer,)):  return int(obj)       # numpy int -> int
    if isinstance(obj, (np.floating,)): return float(obj)     # numpy float -> float
    if isinstance(obj, np.ndarray):     return obj.tolist()   # numpy array -> list
    if isinstance(obj, Path):           return str(obj)       # Path -> string
    raise TypeError(f"Cannot serialise {type(obj)}")


def save_results(results_dict):
    """Write the dictionary of all experiment results to outputs/results.json."""
    ensure_output_dirs()
    with open(settings.RESULTS_JSON, "w", encoding="utf-8") as fh:
        json.dump(results_dict, fh, indent=2, default=_to_jsonable)   # pretty JSON
    return settings.RESULTS_JSON


def load_results():
    """Read outputs/results.json back (used by the report builder)."""
    with open(settings.RESULTS_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)
