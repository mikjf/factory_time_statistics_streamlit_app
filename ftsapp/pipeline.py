"""The analysis scripts, imported rather than reimplemented.

The thresholds shown on screen and the arithmetic behind every number come from
the same modules that wrote the workbooks. Re-declaring MIN_WO or MAD_K here
would let the tool describe a rule the pipeline had stopped applying, and it
would do so in a way nothing could detect.

ONE FUNCTION IS DELIBERATELY NOT USED: fts_analysis.load(). It rebuilds the
parquet when fts.xlsx is newer and rotates fts_prev.parquet out of the way
in the process. That baseline is what compare_to_previous() uses to report a
change of scope between extracts, and a team member opening a dashboard must
never be able to destroy it. read_extract() below does the reading half of that
function and nothing else.

fts_setup_view.load() and fts_load_view.load() only read, so they are called
directly. Both take their input path from a module-level CACHE, and
fts_family_view additionally reads a module-level OPERATION, so those are set
here to absolute values before anything calls them.
"""

import sys

import pandas as pd

from . import paths

# Importing a module normally drops a .pyc beside it, which would put this tool
# in the business of writing to the project folder over a detail nobody asked
# for. "Writes nothing" is a claim worth being able to make without an asterisk,
# and the cost is a few milliseconds of parse time per launch.
sys.dont_write_bytecode = True

# THE PIPELINE'S CODE IS CHECKED FOR BEFORE IT IS IMPORTED. Without this a
# wrong root surfaced as a bare "No module named 'fts_analysis'", naming neither
# the folder that was searched nor how it was chosen nor how to fix it.
if not (paths.ROOT / paths.MARKER).exists():
    raise ImportError(
        f"The pipeline's code is not in {paths.ROOT} (found via: "
        f"{paths.ROOT_FOUND_BY}). Clone {paths.PIPELINE_REPO} beside this app, "
        f"or set FTS_ROOT to the folder that holds {paths.MARKER}.")

# The analysis scripts sit in the project root and are imported, not copied.
if str(paths.ROOT) not in sys.path:
    sys.path.insert(0, str(paths.ROOT))

import fts_analysis as analysis          # noqa: E402
import fts_family_view as family_view    # noqa: E402
import fts_load_view as load_view        # noqa: E402
import fts_setup_view as setup_view      # noqa: E402

# RE-IMPORTED WHEN THEIR FILES CHANGE (2026-10-09). Streamlit reloads the
# app's own modules on save but not these, which live in the pipeline's clone:
# a running app kept the rules it started with until it was restarted. The
# timestamps of paths.CODE when these four were last imported:
_LOADED = tuple(paths.mtime(p) for p in paths.CODE)


def refresh():
    """Re-import the pipeline modules if their files changed since import.

    Called by paths.cache_key(), so no cached figure is ever computed under a
    key that names newer code than the code in memory. Reloads in import order
    - fts_analysis first, the views import it - and then this module itself,
    which re-runs everything below: CACHE re-pointed at the absolute path
    (a reload resets it to the relative default), and every constant and
    function re-exported, so pipeline.SETUP_MIN and the rest follow the new
    code too. The module objects stay the same objects, so every caller that
    holds `pipeline` or `pipeline.setup_view` sees the new code. True when it
    reloaded.
    """
    import importlib
    if tuple(paths.mtime(p) for p in paths.CODE) == _LOADED:
        return False
    for m in (analysis, family_view, load_view, setup_view):
        importlib.reload(m)
    importlib.reload(sys.modules[__name__])
    return True

# Point them all at the real parquet. They resolve CACHE relative to the working
# directory, which is wherever streamlit happened to be launched from.
_CACHE = str(paths.CACHE)
analysis.CACHE = _CACHE
analysis.SRC = str(paths.EXTRACT)
analysis.PREV_CACHE = str(paths.ROOT / "fts_prev.parquet")
family_view.CACHE = _CACHE
load_view.CACHE = _CACHE
setup_view.CACHE = _CACHE

# ---- thresholds, taken from the scripts that applied them -------------------
FY_START = analysis.FY_START

# The window's NAME, derived from its start rather than written down, so it
# cannot drift from the date the analysis actually filters on. Lives here beside
# FY_START because three pages print it and a second copy is how "FY26" outlives
# the year it referred to.
#
# ASSUMES THE FISCAL YEAR IS NAMED AFTER THE CALENDAR YEAR IT ENDS IN and opens
# in the one before - true here, where 1 Oct 2025 opens FY26. A fiscal year
# opening in January would need the +1 dropped.
FY_LABEL = f"FY{(pd.Timestamp(FY_START).year + 1) % 100:02d}"
MIN_WO = analysis.MIN_WO
ALPHA = analysis.ALPHA
MIN_EFFECT = analysis.MIN_EFFECT
MIN_HOURS_IMPACT = analysis.MIN_HOURS_IMPACT
MAD_K = analysis.MAD_K
TOKEN_HOURS = analysis.TOKEN_HOURS

SETUP_MIN = setup_view.MIN_SETUPS
SETUP_MIN_HOURS = setup_view.MIN_HOURS_IMPACT
SKIP_CUT = setup_view.SKIP_CUT

REVIEW_LO = load_view.REVIEW_LO
REVIEW_HI = load_view.REVIEW_HI

slug = analysis.slug

# Re-exported rather than reimplemented: the funnel has to count at exactly the
# grain the analysis tests on, and a second copy of the grouping would drift.
UNIT = analysis.UNIT
to_wo_level = analysis.to_wo_level
drop_token_bookings = analysis.drop_token_bookings


def parts_workbook(operation):
    return paths.OUTPUTS / f"FTS_{slug(operation)}_PARTS.xlsx"


def family_workbook(operation):
    return paths.OUTPUTS / f"FTS_{slug(operation)}_FAMILY.xlsx"


def read_extract():
    """The extract, read-only.

    This repeats the reading half of fts_analysis.load() - the parquet read,
    the whitespace strip, the ANALYTIC_SECTION title-case and the date coercion
    - and omits the rebuild branch.

    The duplication is deliberate. The alternative was to call load() and rely
    on a freshness check upstream to keep the rebuild branch unreachable, which
    is a guarantee that holds only until somebody reorders that function. Eight
    lines copied is cheaper than a viewer that can silently rewrite the
    project's data files.

    Kept line-for-line alongside the original so a divergence is easy to see.
    """
    df = pd.read_parquet(paths.CACHE)
    for c in ["FAMILY", "PART_TYPE", "PART_ID", "PART_DESCRIPTION",
              "WORK_ORDER", "WO_REV", "OPERATION", "LT_TYPE",
              "RUN_TYPE_MASTER", "ANALYTIC_SECTION"]:
        df[c] = df[c].str.strip()
    df["ANALYTIC_SECTION"] = df["ANALYTIC_SECTION"].str.title()
    df["LAST_TRANSACTION_DATE"] = pd.to_datetime(df["LAST_TRANSACTION_DATE"],
                                                 errors="coerce")
    return df
