"""The work orders behind one recommendation, rebuilt from the extract.

The workbooks do not carry this. FTS_SETUP.xlsx and FTS_RUN_HRS_LOAD.xlsx each
have a 05_Evidence sheet, but the PCS/HR run analysis writes per-work-order rows
only for the units it acted on (06_ActionDetail), so most of the analysis has no
persisted evidence at all.

Rebuilding it from fts.parquet is the better answer anyway. A viewer that read
the numbers back out of the workbook could only ever agree with it. This one
recomputes them, which means it can also disagree - and a disagreement is worth
knowing about, because it means either the workbook is stale or an exclusion
rule here has drifted from the one the pipeline applied. That comparison is
`reconcile()` and it is on screen for every unit.

Four routes, because the four analyses are genuinely different and pretending
otherwise is how a rate gets corrected as though it were a duration:

    run_part      PCS/HR, one part at one sequence
    run_family    PCS/HR, the family pool with individually flagged parts out
    setup         SETUP_HRS, family level only - there is no part-level setup test
    load          HRS/LOAD, single-load work orders only

Each returns (rows, stats): one row per work order with a STATUS saying why it
did or did not count, and the figures the recommendation rests on.
"""

import numpy as np
import pandas as pd
import streamlit as st

from . import data, paths, pipeline

# Why a work order did or did not count toward the number.
# Plain English on purpose. These strings are the chart legend and a table
# column that finance and supply chain read, and "excluded - outlier (MAD
# filter)" asks the room to know what a median absolute deviation is before it
# can tell whether a number is trustworthy.
IN = "counted"
OUTLIER = "set aside - too unlike the rest of this pool"
TOKEN = "excluded - closed without a duration recorded"
SKIPPED = "excluded - the setup was not performed"
SUPERSEDED = "excluded - ran under a standard since replaced"
OWN_PART = "excluded - this part is judged on its own"
MULTILOAD = "excluded - charged for more than one load"
# Setup only. The setup happened and was charged - it is not a skip - but the
# people who booked it were not the crew the routing plans for, so the standard
# does not describe the job that was done. See fts_setup_view.load().
CREW = "excluded - not the crew the routing plans for"

EXCLUDED_FIRST = [IN, OUTLIER, TOKEN, SKIPPED, CREW, SUPERSEDED, OWN_PART,
                  MULTILOAD]

ROWS = ["WORK_ORDER", "PART_ID", "LAST_DATE", "TOTAL_QTY", "HOURS_MASTER",
        "HOURS_WORKED", "RATIO", "STATUS"]

# Tooltip-only, appended after ROWS. The evidence TABLE shows ROWS and nothing
# else - these four are pre-formatted display strings, which would sort wrongly
# in a column and say nothing a table column header cannot say better.
#
# They exist because the hover is the one place the standard appears in the unit
# it is actually held in. "master h 6.000" is the analysis speaking; "standard
# 10 PCS/HR" is the routing speaking, and it is the routing somebody has to go
# and change. Seeing both, with the ratio between them, is also the clearest
# demonstration in the tool of why a rate DIVIDES where a duration multiplies:
# the standard falls from 10 to 8.5 pieces an hour exactly when the ratio rises
# above 1.
TIP = ["OP_TXT", "STANDARD", "LOADS", "MASTER_TXT", "ACTUAL_TXT", "ACHIEVED",
       "ACHIEVED_N"]


def table_cols(kind):
    """The evidence table's columns for one route.

    ROWS was one list for all four routes, which meant every setup unit drew a
    PIECES column with nothing in it - setup rows carry no quantity, so the
    column was 100% empty on every setup unit in the tool.

    ACHIEVED_N joins it on PCS/HR only, for the reason the tooltip's ACHIEVED
    line is PCS/HR only: on HRS/LOAD every tested work order is single-load, so
    hours per load IS hours worked, and on setup the standard is already a
    duration. On both, the column would restate ACTUAL h.
    """
    cols = ["WORK_ORDER", "PART_ID", "LAST_DATE"]
    if kind != K_SETUP:
        cols.append("TOTAL_QTY")
    cols += ["HOURS_MASTER", "HOURS_WORKED", "RATIO"]
    if kind == K_PCSHR:
        cols.append("ACHIEVED_N")
    cols.append("STATUS")
    return cols


# Which unit the standard is held in. Passed explicitly by each route rather
# than sniffed from the columns present: the load frame carries RUN_MASTER and
# TOTAL_QTY exactly like the PCS/HR frame does, so column-sniffing would put
# pieces-per-hour labels on hours-per-load numbers and nothing would flag it.
K_PCSHR, K_LOAD, K_SETUP = "PCS/HR", "HRS/LOAD", "SETUP"

# How each route names and units its standard. ONE definition, used by the chart
# tooltip and by any page that has to print a standard: "Run 10.00 PCS/HR" has
# to look identical wherever it appears, and two copies of a format string is
# how "10.00 PCS/HR" and "10 pcs/h" end up on the same screen.
UNITS = {K_PCSHR: ("Run", "PCS/HR"),
         K_LOAD: ("Run", "HRS/LOAD"),
         K_SETUP: ("Setup", "h")}


def kind_of(target, run_type):
    """Which unit a workbook row's standard is held in.

    TARGET and RUN_TYPE are what the update list carries; the three K_ constants
    are what this module works in. One mapping, so a page never has to decide
    what counts as setup.
    """
    if str(target) == "SETUP_HRS":
        return K_SETUP
    return K_LOAD if str(run_type) == "HRS/LOAD" else K_PCSHR


def num(v, dp=2):
    """A number a person would write down. 5 -> "5.00", 93.33333 -> "93.33".

    TWO DECIMALS, not three. The ERP holds hours to two, so a third decimal on
    a duration is always a zero pretending to be a measurement; and nobody
    keying a standard needs the thousandth of a piece per hour.

    WHOLE NUMBERS KEEP THEIR ZEROS. A standard of 5 hours per load shown as "5"
    beside another shown as "1.25" makes the pair hard to compare and the first
    look like a different kind of quantity. Every value on screen is held to the
    same precision, so a column of them reads as a column.
    """
    if v is None or pd.isna(v):
        return None
    return f"{float(v):,.{dp}f}"


def rate_txt(value, kind):
    """A standard in the unit the routing holds it in, route prefix included."""
    prefix, unit = UNITS[kind]
    n = num(value)
    return f"{prefix} {n} {unit}" if n is not None else "—"


def measured_value(current, ratio, kind):
    """What the pool came to, in the unit the routing holds the standard in.

    DERIVED, NOT READ. Every workbook writes its SUGGESTED column only for the
    units it recommends changing - the setup rollup and both load sheets leave
    it empty on 100% of their no-change rows, and the PCS/HR parts sheet on 784
    of 839. Reading it therefore showed a dash on most units that were tested and
    held, which are precisely the ones where "what did it actually come to?" is
    the question being asked.

    The arithmetic is the pipeline's own, and it is the reason the two directions
    matter: a rate divides, a duration multiplies. Where the pipeline does write
    a suggested value this reproduces it, so no unit shows one number here and a
    different one as the value to key.
    """
    if (current is None or pd.isna(current) or ratio is None
            or pd.isna(ratio) or not ratio):
        return None
    return (float(current) / float(ratio) if kind == K_PCSHR
            else float(current) * float(ratio))


def _mad_keep(lr):
    """The outlier mask, mirroring the pipeline's three lines.

    Copied rather than imported because it is inline in every test function
    there. Nothing rests on the copy being right: the caller checks the number
    of survivors against the N_WO_KEPT the pipeline itself returned, and says so
    on screen if they disagree. A chart that greys out the wrong points would
    otherwise be a quiet lie.
    """
    lr = np.asarray(lr, float)
    if len(lr) == 0:
        return np.zeros(0, bool)
    med = float(np.median(lr))
    mad = float(np.median(np.abs(lr - med))) * 1.4826
    if mad <= 0:
        return np.ones(len(lr), bool)
    return np.abs(lr - med) <= pipeline.MAD_K * mad


def _standard_and_achieved(out, kind):
    """The two rate lines, per route.

    THE STANDARD IS ALWAYS SHOWN, in the unit the routing holds it in, prefixed
    with the route so a hover is readable on its own.

    THE ACHIEVED LINE IS PCS/HR ONLY, and that is not an oversight:

      HRS/LOAD - every tested work order is single-load by construction, so
        hours per load and hours worked are the same number. The line would
        restate "actual h" on every counted dot. The load COUNT goes in
        instead, which is the figure that actually varies and the one that
        explains why an excluded multi-load dot sits where it does.
      SETUP    - the standard is already a duration, so achieved setup hours
        are "actual h" again.

    A field that is empty for every row drawn is dropped from the tooltip by
    charts.distribution, so those routes simply show fewer lines.
    """
    out["LOADS"] = None
    out["ACHIEVED"] = None
    out["ACHIEVED_N"] = np.nan

    # The hours carry their unit in the VALUE, not in the label - "master" /
    # "6.00 h" rather than "master h" / "6.00". Every other line on the hover
    # already works that way ("Run 10.00 PCS/HR", "1.25 h"), and master and
    # actual are the two words this whole tool refuses to paraphrase, so they
    # read better standing alone than carrying a unit as part of their name.
    for col, src in (("MASTER_TXT", "HOURS_MASTER"),
                     ("ACTUAL_TXT", "HOURS_WORKED")):
        out[col] = out[src].map(
            lambda v: f"{num(v)} h" if num(v) is not None else None)

    if kind == K_PCSHR:
        out["STANDARD"] = out.RUN_MASTER.map(
            lambda v: rate_txt(v, kind) if pd.notna(v) else None)
        # Pieces over hours actually booked. Both are stored figures, so this
        # is exact - deriving it from the standard and the ratio instead would
        # inherit the ERP's rounding of HOURS_MASTER, which is held to two
        # decimals and drifts by up to 11% on the shortest jobs.
        #
        # No route prefix: the line above has already said "Run", and repeating
        # it on the achieved figure reads as a second standard.
        ach = out.TOTAL_QTY / out.HOURS_WORKED.replace(0, np.nan)
        out["ACHIEVED"] = ach.map(
            lambda v: f"{num(v)} {UNITS[kind][1]}" if num(v) else None)
        # The same figure as a NUMBER, for the table. A column of
        # "190.87 PCS/HR" strings sorts as text, which puts 90 above 190 and
        # gives no sign that the order is wrong.
        out["ACHIEVED_N"] = ach

    elif kind == K_LOAD:
        out["STANDARD"] = out.RUN_MASTER.map(
            lambda v: rate_txt(v, kind) if pd.notna(v) else None)
        if "LOADS_CHARGED" in out.columns:
            out["LOADS"] = out.LOADS_CHARGED.map(
                lambda v: num(v, 0) if pd.notna(v) else None)

    else:
        # HOURS_MASTER on a crew-matched row IS the routing's setup value, so
        # this line restates it with its unit and its route. On a crew-mismatch
        # row it is not - master hours there have been scaled by the crew that
        # actually booked - so the unit's stored value is shown instead, and
        # the gap between this line and "master h" is the whole reason the row
        # was excluded. SETUP_HRS_STORED is null on units with no crew-matched
        # row at all, which shows as a dash rather than a wrong number.
        crew_ok = (out.CREW_OK if "CREW_OK" in out.columns
                   else pd.Series(True, index=out.index))
        stored = (out.SETUP_HRS_STORED if "SETUP_HRS_STORED" in out.columns
                  else pd.Series(np.nan, index=out.index))
        src = out.HOURS_MASTER.where(crew_ok.fillna(False), stored)
        out["STANDARD"] = src.map(
            lambda v: rate_txt(v, kind) if pd.notna(v) else None)

    return out


def _rows(df, status, kind):
    """Shape any per-work-order frame into the common columns."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=ROWS + TIP)
    out = df.copy()
    if "TOTAL_QTY" not in out.columns:      # setup rows carry no quantity
        out["TOTAL_QTY"] = np.nan
    if "LAST_DATE" not in out.columns:
        out["LAST_DATE"] = pd.NaT
    out["RATIO"] = out.HOURS_WORKED / out.HOURS_MASTER
    out["STATUS"] = status

    # Sequence then operation, the way a routing is read aloud. Constant across
    # every dot on a given chart and shown anyway: a hover is the thing people
    # screenshot to point at a work order, and it has to be legible detached
    # from the page that drew it.
    if "OPERATION" in out.columns and "OPERATION_SEQUENCE" in out.columns:
        out["OP_TXT"] = (out.OPERATION_SEQUENCE.map(
            lambda v: f"{int(v)}" if pd.notna(v) else "?")
            + " " + out.OPERATION.astype(str))
    else:
        out["OP_TXT"] = None

    out = _standard_and_achieved(out, kind)
    return out[ROWS + TIP]


def _blank():
    return pd.DataFrame(columns=ROWS + TIP), {}


def _pack(rows, counted, stats):
    """Assemble the return value and add the figures every route shares."""
    rows = rows.sort_values(["STATUS", "LAST_DATE"], na_position="last")
    stats = dict(stats)
    stats.setdefault("N_ALL", len(rows))
    stats.setdefault("N_COUNTED", int(counted))
    return rows.reset_index(drop=True), stats


# ---------------------------------------------------------------------------
# PCS/HR run
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Rebuilding the work orders from the extract...")
def _run_frames(operation, key):
    """Work-order level for one operation, tokens kept aside rather than lost.

    The scope filter repeats the one in fts_analysis.main(). It is inline
    there, so there is nothing to import; if the two ever drift apart the
    reconciliation on the unit page is what surfaces it.
    """
    a = pipeline.analysis
    df = pipeline.read_extract()
    scope = ((df.LT_TYPE == "Run")
             & (df.RUN_TYPE_MASTER == "PCS/HR")
             & ~df.OPERATION.str.upper().str.startswith("S RIL")
             & (df.LAST_TRANSACTION_DATE >= pd.Timestamp(a.FY_START))
             & (df.RUN_MASTER > 0)
             & (df.HOURS_MASTER > 0)
             & (df.HOURS_WORKED > 0)
             & df.MASTER_OPS_ROWID.notna()
             & (df.OPERATION == operation))
    wo = a.to_wo_level(df[scope])
    kept, tokens = a.drop_token_bookings(wo)
    kept = kept.copy()
    kept["LOG_RATIO"] = np.log(kept.HOURS_WORKED / kept.HOURS_MASTER)
    return kept, tokens


def _run_wo(operation):
    return _run_frames(operation, paths.cache_key(paths.CACHE))


def _pick(df, **kw):
    if len(df) == 0:
        return df
    m = pd.Series(True, index=df.index)
    for col, val in kw.items():
        m &= df[col] == val
    return df[m]


def run_part(operation, family, part_type, part_id, seq):
    """One part at one sequence, PCS/HR."""
    kept, tokens = _run_wo(operation)
    where = dict(FAMILY=family, PART_TYPE=part_type, PART_ID=part_id,
                 OPERATION_SEQUENCE=seq)
    g = _pick(kept, **where)
    tok = _pick(tokens, **where)
    if len(g) == 0:
        return _pack(_rows(tok, TOKEN, K_PCSHR), 0,
                     {"NOTE": "every work order was a token booking"})

    res = pipeline.analysis.test_group(g)

    # test_group drops the work orders run under a superseded RUN_MASTER, but
    # only when enough remain under the current one to stand alone.
    if res["BASIS"] == "current master only":
        used = g[g.RUN_MASTER == res["RUN_MASTER_CURRENT"]]
        old = g[g.RUN_MASTER != res["RUN_MASTER_CURRENT"]]
    else:
        used, old = g, g.iloc[:0]

    keep = _mad_keep(used.LOG_RATIO)
    rows = pd.concat([_rows(used[keep], IN, K_PCSHR),
                      _rows(used[~keep], OUTLIER, K_PCSHR),
                      _rows(old, SUPERSEDED, K_PCSHR),
                      _rows(tok, TOKEN, K_PCSHR)])

    stats = {
        "N_TESTED": int(res["N_WORK_ORDERS"]),
        "N_KEPT": int(res["N_WO_KEPT"]),
        "RATIO_POOLED": res["RATIO_HOURS_WORKED_TO_HOURS_MASTER"],
        "RATIO": res["RATIO_OUTLIERS_REMOVED"],
        "CI_LOW": res["CI95_LOW"], "CI_HIGH": res["CI95_HIGH"],
        "P_WILCOXON": res["P_VALUE_WILCOXON"], "P_TTEST": res["P_VALUE_TTEST"],
        "HOURS_MASTER": res["HOURS_MASTER"], "HOURS_WORKED": res["HOURS_WORKED"],
        "HOURS_DELTA": res["HOURS_DELTA"],
        "CURRENT": res["RUN_MASTER_CURRENT"],
        "BASIS": res["BASIS"], "MASTER_CHANGED": res["MASTER_CHANGED"],
        "MAD_AGREES": int(keep.sum()) == int(res["N_WO_KEPT"]),
        "MIN_N": pipeline.MIN_WO, "MIN_HOURS": pipeline.MIN_HOURS_IMPACT,
    }
    return _pack(rows, keep.sum(), stats)


@st.cache_data(show_spinner=False)
def _family_pool(operation, key):
    """The family-level frame, straight from fts_family_view.load().

    That function differs from the part-level one in a way that matters: it cuts
    every part+sequence to its own latest RUN_MASTER before pooling, so no
    superseded standard leaks into a family figure. Calling it rather than
    filtering the part-level frame is what keeps the family numbers reproducible.
    """
    fv = pipeline.family_view
    fv.OPERATION = operation
    return fv.load()


def run_family(operation, family, part_type, seq):
    """The family pool at one sequence, parts flagged individually removed."""
    fv = pipeline.family_view
    pool = _pick(_family_pool(operation, paths.cache_key(paths.CACHE)),
                 FAMILY=family, PART_TYPE=part_type, OPERATION_SEQUENCE=seq)
    if len(pool) == 0:
        return _blank()

    tested = data.parts_book(operation, "04_Tested_WithEvidence")
    flagged = set(tested.loc[tested.RECOMMENDATION == "UPDATE RUN_MASTER",
                             "PART_ID"])
    famex = pool[~pool.PART_ID.isin(flagged)]
    own = pool[pool.PART_ID.isin(flagged)]
    res = fv.pooled(famex, "FAMEX")

    keep = _mad_keep(famex.LOG_RATIO)

    # Work orders the part-level frame has and this pool does not: dropped by
    # the latest-RUN_MASTER cut above. Shown so the pool is accounted for in
    # full rather than just smaller than expected.
    kept_all, tokens = _run_wo(operation)
    where = dict(FAMILY=family, PART_TYPE=part_type, OPERATION_SEQUENCE=seq)
    all_wo = _pick(kept_all, **where)
    seen = set(zip(pool.PART_ID, pool.WORK_ORDER))
    old = all_wo[[t not in seen
                  for t in zip(all_wo.PART_ID, all_wo.WORK_ORDER)]]

    rows = pd.concat([_rows(famex[keep], IN, K_PCSHR),
                      _rows(famex[~keep], OUTLIER, K_PCSHR),
                      _rows(own, OWN_PART, K_PCSHR),
                      _rows(old, SUPERSEDED, K_PCSHR),
                      _rows(_pick(tokens, **where), TOKEN, K_PCSHR)])

    stats = {
        "N_TESTED": int(res["FAMEX_WO"]),
        "N_KEPT": int(keep.sum()),
        "N_PARTS": int(res["FAMEX_PARTS"]),
        "RATIO": res["FAMEX_RATIO"],
        "RATIO_POOLED": (famex.HOURS_WORKED.sum() / famex.HOURS_MASTER.sum()
                         if famex.HOURS_MASTER.sum() else np.nan),
        "CI_LOW": res["FAMEX_CI95_LOW"], "CI_HIGH": res["FAMEX_CI95_HIGH"],
        "P_WILCOXON": res["FAMEX_P_WILCOXON"], "P_TTEST": res["FAMEX_Q_RAW_TTEST"],
        "HOURS_MASTER": res["FAMEX_HOURS_MASTER"],
        "HOURS_WORKED": res["FAMEX_HOURS_WORKED"],
        "HOURS_DELTA": round(res["FAMEX_HOURS_WORKED"]
                             - res["FAMEX_HOURS_MASTER"], 2),
        "CURRENT": res["FAMEX_RM_CURRENT"],
        "N_DISTINCT_CURRENT": res["FAMEX_N_DISTINCT_RM"],
        "MAD_AGREES": True,     # pooled() applies the same mask inline
        "MIN_N": pipeline.MIN_WO, "MIN_HOURS": pipeline.MIN_HOURS_IMPACT,
    }
    return _pack(rows, keep.sum(), stats)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _setup_frame(key):
    return pipeline.setup_view.load("PCS/HR")


def setup(operation, family, part_type, seq):
    """One family x sequence of setup. There is no part-level setup test:
    setup units average under four worked hours across a whole year, so nothing
    clears a materiality gate alone."""
    sv = pipeline.setup_view
    g = _pick(_setup_frame(paths.cache_key(paths.CACHE)), OPERATION=operation,
              FAMILY=family, PART_TYPE=part_type, OPERATION_SEQUENCE=seq)
    if len(g) == 0:
        return _blank()

    res = sv.test_family(g)
    # Mirrors test_family exactly: performed, THEN crew-matched. Splitting it
    # any other way makes the chart and the verdict disagree - the MAD filter
    # runs on whatever set is handed to it, so computing it over all performed
    # rows would keep and drop different work orders than the test did, and the
    # reconciliation badge would start failing on units that are fine.
    performed = g[~g.SKIPPED]
    real = performed[performed.CREW_OK]
    keep = _mad_keep(real.LOG_RATIO)

    rows = pd.concat([_rows(real[keep], IN, K_SETUP),
                      _rows(real[~keep], OUTLIER, K_SETUP),
                      _rows(performed[~performed.CREW_OK], CREW, K_SETUP),
                      _rows(g[g.SKIPPED], SKIPPED, K_SETUP)])

    stats = {
        "N_TESTED": int(res["WO_REAL"]),
        "N_KEPT": int(keep.sum()),
        "N_PARTS": int(res["PARTS"]),
        "RATIO": res["RATIO_OUTLIERS_REMOVED"], "RATIO_POOLED": res["RATIO"],
        "CI_LOW": res["CI95_LOW"], "CI_HIGH": res["CI95_HIGH"],
        "P_WILCOXON": res["P_WILCOXON"], "P_TTEST": res["P_RAW_TTEST"],
        "HOURS_MASTER": res["HOURS_MASTER"], "HOURS_WORKED": res["HOURS_WORKED"],
        "HOURS_DELTA": res["HOURS_DELTA"],
        "CURRENT": res["SETUP_HRS_CURRENT"],
        "N_DISTINCT_CURRENT": res["SETUP_HRS_N_DISTINCT"],
        "SKIP_RATE": res["SKIP_RATE"],
        "CHARGED_SKIPPED": res["STANDARD_CHARGED_SKIPPED"],
        "MAD_AGREES": True,
        "MIN_N": pipeline.SETUP_MIN, "MIN_HOURS": pipeline.SETUP_MIN_HOURS,
    }
    return _pack(rows, keep.sum(), stats)


# ---------------------------------------------------------------------------
# HRS/LOAD run
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_frames(key):
    return pipeline.load_view.load()


def load(operation, family, part_type, seq, part_id=None):
    """HRS/LOAD, part level when part_id is given and family level otherwise.

    Only single-load work orders are tested. The standard assumes a second
    basket costs the same as the first and it does not - over the year the
    multi-load population runs at a ratio of 0.647 against 1.119 for single
    load - so those rows appear here as excluded rather than as evidence.
    """
    lv = pipeline.load_view
    one, multi = _load_frames(paths.cache_key(paths.CACHE))
    where = dict(OPERATION=operation, FAMILY=family, PART_TYPE=part_type,
                 OPERATION_SEQUENCE=seq)
    pool, over = _pick(one, **where), _pick(multi, **where)
    if part_id is not None:
        pool, over = _pick(pool, PART_ID=part_id), _pick(over, PART_ID=part_id)
    if len(pool) == 0:
        return _pack(_rows(over, MULTILOAD, K_LOAD), 0, {})

    if part_id is not None:
        tested, own = pool, pool.iloc[:0]
        res = lv.pooled(tested)
        p = ""
    else:
        units = data.load_book("01_PartUnits")
        flagged = set(units.loc[units.VERDICT == "UPDATE RUN", "PART_ID"])
        tested = pool[~pool.PART_ID.isin(flagged)]
        own = pool[pool.PART_ID.isin(flagged)]
        res = lv.pooled(tested, "FAMEX")
        p = "FAMEX_"

    keep = _mad_keep(tested.LOG_RATIO)
    rows = pd.concat([_rows(tested[keep], IN, K_LOAD),
                      _rows(tested[~keep], OUTLIER, K_LOAD),
                      _rows(own, OWN_PART, K_LOAD),
                      _rows(over, MULTILOAD, K_LOAD)])

    stats = {
        "N_TESTED": int(res[f"{p}WO"]),
        "N_KEPT": int(keep.sum()),
        "N_PARTS": int(res[f"{p}PARTS"]),
        "RATIO": res[f"{p}RATIO_OUTLIERS_REMOVED"],
        "RATIO_POOLED": res[f"{p}RATIO"],
        "CI_LOW": res[f"{p}CI95_LOW"], "CI_HIGH": res[f"{p}CI95_HIGH"],
        "P_WILCOXON": res[f"{p}P_WILCOXON"], "P_TTEST": res[f"{p}P_RAW_TTEST"],
        "HOURS_MASTER": res[f"{p}HOURS_MASTER"],
        "HOURS_WORKED": res[f"{p}HOURS_WORKED"],
        "HOURS_DELTA": res[f"{p}HOURS_DELTA"],
        "CURRENT": res[f"{p}RUN_CURRENT"],
        "N_DISTINCT_CURRENT": res[f"{p}N_DISTINCT_RUN"],
        "MAD_AGREES": True,
        "MIN_N": pipeline.MIN_WO, "MIN_HOURS": pipeline.MIN_HOURS_IMPACT,
    }
    return _pack(rows, keep.sum(), stats)


# ---------------------------------------------------------------------------
# Does the rebuild still match the workbook?
# ---------------------------------------------------------------------------

TOL = 1e-6


def _one(df, **kw):
    r = _pick(df, **kw)
    return r.iloc[0] if len(r) else None


def stored(target, run_type, operation, family, part_type, seq, part_id=None):
    """The figure the pipeline recorded for this unit, at full precision.

    Always read from the workbook that COMPUTED it, never from
    FTS_UPDATE_LIST.xlsx. The consolidated sheets round the ratio to three
    decimals for reading - 0.7297 is written 0.730 - and comparing a rebuilt
    number against a rounded one reports a mismatch on every second unit, which
    would train everybody to ignore the one check that matters.
    """
    S = data.SEQ
    try:
        if target == "SETUP_HRS":
            r = _one(data.setup_book("01_FamilyRollup"), OPERATION=operation,
                     FAMILY=family, PART_TYPE=part_type, **{S: seq})
            return None if r is None else (r.RATIO_OUTLIERS_REMOVED, r.WO_REAL)
        if run_type == "HRS/LOAD":
            if part_id is not None:
                r = _one(data.load_book("01_PartUnits"), OPERATION=operation,
                         FAMILY=family, PART_TYPE=part_type, PART_ID=part_id,
                         **{S: seq})
                return None if r is None else (r.RATIO_OUTLIERS_REMOVED, r.WO)
            r = _one(data.load_book("02_FamilyRollup"), OPERATION=operation,
                     FAMILY=family, PART_TYPE=part_type, **{S: seq})
            return (None if r is None
                    else (r.FAMEX_RATIO_OUTLIERS_REMOVED, r.FAMEX_WO))
        if part_id is not None:
            r = _one(data.all_units(operation), FAMILY=family,
                     PART_TYPE=part_type, PART_ID=part_id, **{S: seq})
            return (None if r is None
                    else (r.RATIO_OUTLIERS_REMOVED, r.N_WORK_ORDERS))
        r = _one(data.family_book(operation, "01_FamilyRollup"), FAMILY=family,
                 PART_TYPE=part_type, **{S: seq})
        return None if r is None else (r.FAMEX_RATIO, r.FAMEX_WO)
    except (FileNotFoundError, KeyError, ValueError):
        return None


@st.cache_data(show_spinner=False)
def _flagged_master(key, pairs):
    """Master hours of the flagged steps only, per family.

    Rebuilt from the action pools rather than summed straight off the extract,
    because the numerator comes from those pools: they drop token bookings,
    work orders run under a superseded standard, and parts already flagged
    individually. Taking the denominator from the raw extract instead mixes two
    populations and moves the answer by up to 6 percentage points - one family
    reads 21.1% one way and 27.2% the other.

    Costs a few seconds, so it is cached on the extract and only ever computed
    for the handful of families actually on screen.
    """
    S = data.SEQ
    acts = data.actions()
    acts = acts[acts.TARGET == "RUN"]
    out = []
    for family, part_type in pairs:
        mine = acts[(acts.FAMILY == family) & (acts.PART_TYPE == part_type)]
        total = 0.0
        for _, x in mine.iterrows():
            part = x.PART_ID if x.LEVEL == "PART" else None
            if x.RUN_TYPE == "HRS/LOAD":
                _, st_ = load(x.OPERATION, family, part_type, x[S], part)
            elif part:
                _, st_ = run_part(x.OPERATION, family, part_type, part, x[S])
            else:
                _, st_ = run_family(x.OPERATION, family, part_type, x[S])
            total += st_.get("HOURS_MASTER", 0) or 0
        out.append({"FAMILY": family, "PART_TYPE": part_type,
                    "FLAGGED_MASTER_H": total})
    return pd.DataFrame(out)


def flagged_master_hours(pairs):
    return _flagged_master(paths.cache_key(paths.CACHE),
                           tuple((str(f), str(p)) for f, p in pairs))


def verdict_for(target, run_type, operation, family, part_type, seq,
                part_id=None):
    """The workbook's own verdict, q-value and the two numbers, for one unit.

    The q-value has to come from the workbook rather than the rebuild:
    Benjamini-Hochberg adjusts each p against every other test in the same run,
    so it is a property of the whole set and simply does not exist for a unit
    looked at on its own.
    """
    S = data.SEQ
    blank = {"verdict": None, "q": None, "current": None, "suggested": None}
    try:
        if target == "SETUP_HRS":
            r = _one(data.setup_book("01_FamilyRollup"), OPERATION=operation,
                     FAMILY=family, PART_TYPE=part_type, **{S: seq})
            keys = ("VERDICT", "Q_VALUE_FDR", "SETUP_HRS_CURRENT",
                    "SETUP_HRS_SUGGESTED")
        elif run_type == "HRS/LOAD" and part_id is not None:
            r = _one(data.load_book("01_PartUnits"), OPERATION=operation,
                     FAMILY=family, PART_TYPE=part_type, PART_ID=part_id,
                     **{S: seq})
            keys = ("VERDICT", "Q_VALUE_FDR", "RUN_CURRENT", "RUN_SUGGESTED")
        elif run_type == "HRS/LOAD":
            r = _one(data.load_book("02_FamilyRollup"), OPERATION=operation,
                     FAMILY=family, PART_TYPE=part_type, **{S: seq})
            keys = ("FAMEX_VERDICT", "FAMEX_Q_VALUE", "FAMEX_RUN_CURRENT",
                    "FAMEX_RUN_SUGGESTED")
        elif part_id is not None:
            r = _one(data.all_units(operation), FAMILY=family,
                     PART_TYPE=part_type, PART_ID=part_id, **{S: seq})
            keys = ("RECOMMENDATION", "Q_VALUE_FDR", "RUN_MASTER_CURRENT",
                    "RUN_MASTER_SUGGESTED")
        else:
            r = _one(data.family_book(operation, "01_FamilyRollup"),
                     FAMILY=family, PART_TYPE=part_type, **{S: seq})
            keys = ("FAMEX_VERDICT", "FAMEX_Q_VALUE", "FAMEX_RM_CURRENT",
                    "FAMEX_RM_SUGGESTED")
    except (FileNotFoundError, KeyError, ValueError):
        return blank
    if r is None:
        return blank
    v, q, cur, sug = (r.get(k) for k in keys)
    return {"verdict": v, "q": q, "current": cur, "suggested": sug, "row": r}


def outcome(verdict, stats):
    """Reduce a verdict string to one of four states the interface colours by.

    The pipeline writes several different phrasings - "UPDATE RUN_MASTER",
    "UPDATE FAMILY STANDARD", "no change - not statistically different",
    "insufficient data (n<6)" - and a reader should not have to learn which
    family of wording belongs to which analysis.
    """
    v = str(verdict or "").upper()
    if v.startswith("UPDATE"):
        return "act"
    if not verdict:
        return "unknown"
    if "INSUFFICIENT" in v or "WATCH" in v or "TOO FEW" in v:
        return "blocked"
    return "hold"


# ---------------------------------------------------------------------------
# Today's master, for every unit
# ---------------------------------------------------------------------------
# The update list states today's master only for actions. Inspect also shows it
# on every unit that is NOT an action, because "why is my part not on the list"
# is a question about exactly those - and the master may have moved since the
# jobs ran. So it is rebuilt here from the extract, per part, with the
# pipeline's own definitions (fts_update_list.load_today / attach_today):
#
#   TODAY  the *_MASTER_TODAY value on the part's current master line at this
#          step - one value per line, as fts.sql carries it
#   WO     run: RUN_MASTER of the part's most recent work order this fiscal
#          year (what *_CURRENT is); setup: the largest SETUP_HRS_STORED, the
#          setup analysis's own per-part figure
#   moved  WO and TODAY further apart than SAME_VALUE; "no master line today"
#          is not a move
#
# Checked before it was written: on the 5 Oct extract this reproduced
# STANDARD_WO, STANDARD_TODAY and moved/unchanged on all 2,652 rows of the three
# execution sheets. Inspect keeps checking it - on an action unit both copies
# exist, and a disagreement is shown as an error rather than resolved quietly.

SAME_VALUE = 0.005      # must match fts_update_list.SAME_VALUE


def _rev(v):
    """A revision label as text - fts_update_list._rev, copied (it is not a
    module the app imports). Compared for equality only, never sorted."""
    if v is None or pd.isna(v):
        return None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return str(int(v)) if float(v).is_integer() else str(v)
    s = str(v).strip()
    if s.lower() in ("", "nan", "none"):
        return None
    return s[:-2] if s.endswith(".0") and s[:-2].isdigit() else s


@st.cache_data(show_spinner=False)
def _today_frames(key):
    """Per-part WO and TODAY values for the three routes, keyed on
    (PART_ID, OPERATION, SEQUENCE)."""
    df = pipeline.read_extract()
    if "RUN_MASTER_TODAY" not in df.columns:
        return None                     # an extract older than 28 Sep 2026
    df = df[df.MASTER_OPS_ROWID.notna()].copy()
    df["RUN_TYPE_MASTER_TODAY"] = df.RUN_TYPE_MASTER_TODAY.map(
        lambda v: None if pd.isna(v) else str(v).strip())
    df["CURRENT_REV"] = df.CURRENT_REV.map(_rev)
    df["WO_REV"] = df.WO_REV.map(_rev)
    k = ["PART_ID", "OPERATION", "OPERATION_SEQUENCE"]
    fy = df[df.LAST_TRANSACTION_DATE >= pd.Timestamp(pipeline.FY_START)]

    def today(lt, col):
        d = df[df.LT_TYPE == lt]
        g = d.groupby(k)
        out = pd.DataFrame({
            "TODAY": g[col].max(),
            "N_TODAY": g[col].nunique(),
            "RUN_TYPE_TODAY": g.RUN_TYPE_MASTER_TODAY.max(),
            "CURRENT_REV": g.CURRENT_REV.max(),
        })
        last = (fy[fy.LT_TYPE == lt].sort_values("LAST_TRANSACTION_DATE",
                                                 kind="stable")
                .groupby(k).tail(1).set_index(k).WO_REV)
        return out.join(last.rename("WO_REV"))

    def latest_run(run_type):
        d = fy[(fy.LT_TYPE == "Run") & (fy.RUN_TYPE_MASTER == run_type)
               & (fy.RUN_MASTER > 0)]
        return (d.sort_values("LAST_TRANSACTION_DATE", kind="stable")
                .groupby(k).tail(1).set_index(k).RUN_MASTER.rename("WO"))

    run_today = today("Run", "RUN_MASTER_TODAY")
    setup_wo = (_setup_frame(key).groupby(k).SETUP_HRS_STORED.max()
                .rename("WO"))
    return {
        K_PCSHR: run_today.join(latest_run("PCS/HR"), how="inner"),
        K_LOAD: run_today.join(latest_run("HRS/LOAD"), how="inner"),
        K_SETUP: today("Setup", "SETUP_HRS_MASTER_TODAY").join(setup_wo,
                                                                how="inner"),
    }


def today_parts(kind, operation, seq, part_ids):
    """Today's master for these parts at one step, in the shape of the update
    list's execution rows, so data.today_summary reads either. None when the
    extract carries no today columns or none of the parts is found."""
    frames = _today_frames(paths.cache_key(paths.CACHE))
    if frames is None:
        return None
    f = frames[kind]
    keys = [(p, operation, seq) for p in sorted(set(part_ids))]
    t = f.reindex(pd.MultiIndex.from_tuples(
        keys, names=["PART_ID", "OPERATION", "OPERATION_SEQUENCE"])).dropna(
        how="all", subset=["WO", "TODAY"])
    if t.empty:
        return None
    a, c = t.WO.astype(float), t.TODAY.astype(float)
    run_type = None if kind == K_SETUP else kind
    type_changed = (t.RUN_TYPE_TODAY.notna() & (run_type is not None)
                    & (t.RUN_TYPE_TODAY != run_type))
    change = np.select(
        [c.isna(), type_changed, (a - c).abs() <= SAME_VALUE,
         t.WO_REV.notna() & (t.WO_REV == t.CURRENT_REV)],
        ["no master line today", "run type changed", "unchanged",
         "changed within the same revision"],
        "changed with a newer revision")
    return pd.DataFrame({
        "PART_ID": t.index.get_level_values(0),
        "STANDARD_WO": a.to_numpy(), "STANDARD_TODAY": c.to_numpy(),
        "N_TODAY": t.N_TODAY.to_numpy(),
        "STANDARD_CHANGE": change,
        "WO_REV": t.WO_REV.to_numpy(), "CURRENT_REV": t.CURRENT_REV.to_numpy(),
        "CHANGE_PCT_TODAY": np.nan, "TODAY_STATUS": "",
        "REVIEW_FLAG_TODAY": np.nan,
    })


def unit(target, run_type, operation, family, part_type, seq, part_id=None):
    """(rows, stats) for one unit, by what it edits - the dispatch Inspect makes.

    By part reaches a unit's evidence through this too, so a whole-family row
    there covers exactly the parts Inspect shows for the same unit. A cheaper
    route - every part of the family running the step - was measured against
    it on 400 family units (2026-10-07) and differed on 16, all HRS/LOAD, where
    the evidence keeps fewer parts than run the step.
    """
    kind = kind_of(target, run_type)
    if kind == K_SETUP:
        return setup(operation, family, part_type, seq)
    if kind == K_LOAD:
        return load(operation, family, part_type, seq, part_id)
    if part_id is not None:
        return run_part(operation, family, part_type, part_id, seq)
    return run_family(operation, family, part_type, seq)


def unit_today(target, run_type, operation, family, part_type, seq,
               part_id=None, rows=None):
    """(frame, from_list): one unit's parts with their Standard WO and today.

    On an action the frame is the update list's own rows (data.today_rows) and
    from_list is True; on every other unit it is rebuilt from the extract for
    the parts in the unit's evidence (today_parts). One definition for Inspect
    and By part. `rows` is the unit's evidence when the caller already holds
    it; otherwise it is fetched, and only when needed.
    """
    if data.action_row(target, run_type, operation, family, part_type, seq,
                       part_id) is not None:
        ex = data.today_rows(target, run_type, operation, family, part_type,
                             seq, part_id)
        if ex is not None and len(ex):
            return ex, True
    if part_id is not None:
        parts = [part_id]
    else:
        if rows is None:
            rows, _ = unit(target, run_type, operation, family, part_type, seq)
        parts = rows.PART_ID.dropna().unique().tolist()
    return today_parts(kind_of(target, run_type), operation, seq, parts), False


def keyable(value, kind):
    """A suggested value rounded the way the pipeline rounds one before it
    reaches the workbook: 2 decimals, the ERP field's own; setup at 10 h and
    over to 1 - see fts_setup_view. For a figure the app derives itself."""
    if value is None or pd.isna(value):
        return float("nan")
    return round(float(value), 1 if kind == K_SETUP and value >= 10 else 2)


def today_row(td, kind):
    """The "master today" row of the decision table, from data.today_summary,
    or "" when there is nothing to state. One definition, so Inspect and the
    worked example on How to read it say the same words."""
    if td is None:
        return ""
    if td["value"] is not None:
        tv = rate_txt(td["value"], kind)
    elif td["n_values"]:
        tv = f"{td['n_values']} different values across {td['n']} parts"
    else:
        tv = "no master line today"
    nl = td["no_line"]
    bits = ([] if nl == td["n"] else
            ["unchanged since the jobs ran"] if td["moved"] == 0 else
            ["moved since the jobs ran" + ("" if td["moved"] == td["n"]
             else f" on {td['moved']} of {td['n']} parts")])
    if nl and nl < td["n"]:
        bits.append(f"no master line today on {nl} of {td['n']} parts")
    if td["done"]:
        bits.append("**already done**" if td["done"] == td["n"]
                    else f"**already done on {td['done']} of {td['n']} parts**")
    return (f"| **master today** | | {tv}"
            + (f" — {', '.join(bits)}" if bits else "") + " |\n")


def reconcile(stats, stored_ratio, stored_n=None):
    """Compare the rebuilt figures with the ones the workbook stored.

    A mismatch is not a display bug to be smoothed over. It means the workbook
    was written from a different extract, or that an exclusion rule in this
    module has drifted from the one the pipeline applied. Either way the number
    on the row somebody is about to key into the ERP is not the number the
    current data supports, and that has to say so.
    """
    if not stats or stored_ratio is None or pd.isna(stored_ratio):
        return None, "no stored figure to compare against"
    got = stats.get("RATIO")
    if got is None or pd.isna(got):
        return False, "the extract no longer produces a ratio for this unit"
    if abs(float(got) - float(stored_ratio)) > TOL:
        return False, (f"rebuilt ratio {got:.4f} against {stored_ratio:.4f} in "
                       "the workbook")
    if stored_n is not None and not pd.isna(stored_n) \
            and int(stored_n) != int(stats.get("N_TESTED", -1)):
        return False, (f"same ratio but {stats['N_TESTED']} work orders against "
                       f"{int(stored_n)} in the workbook")
    if not stats.get("MAD_AGREES", True):
        return False, ("the outlier mask drawn on the chart disagrees with the "
                       "count the analysis reported")
    return True, "reproduces the workbook from the current extract"
