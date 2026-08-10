"""The work orders behind one recommendation, rebuilt from the extract.

The workbooks do not carry this. H0_v2_SETUP.xlsx and H0_v2_LOAD.xlsx each have
a 05_Evidence sheet, but the PCS/HR run analysis writes per-work-order rows only
for the units it acted on (06_ActionDetail), so most of the analysis has no
persisted evidence at all.

Rebuilding it from h0_v2.parquet is the better answer anyway. A viewer that read
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

EXCLUDED_FIRST = [IN, OUTLIER, TOKEN, SKIPPED, SUPERSEDED, OWN_PART, MULTILOAD]

ROWS = ["WORK_ORDER", "PART_ID", "LAST_DATE", "TOTAL_QTY", "HOURS_MASTER",
        "HOURS_WORKED", "RATIO", "STATUS"]


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


def _rows(df, status):
    """Shape any per-work-order frame into the common columns."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=ROWS)
    out = df.copy()
    if "TOTAL_QTY" not in out.columns:      # setup rows carry no quantity
        out["TOTAL_QTY"] = np.nan
    if "LAST_DATE" not in out.columns:
        out["LAST_DATE"] = pd.NaT
    out["RATIO"] = out.HOURS_WORKED / out.HOURS_MASTER
    out["STATUS"] = status
    return out[ROWS]


def _blank():
    return pd.DataFrame(columns=ROWS), {}


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

    The scope filter repeats the one in h0_v2_analysis.main(). It is inline
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
        return _pack(_rows(tok, TOKEN), 0,
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
    rows = pd.concat([_rows(used[keep], IN), _rows(used[~keep], OUTLIER),
                      _rows(old, SUPERSEDED), _rows(tok, TOKEN)])

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
    """The family-level frame, straight from h0_v2_family_view.load().

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

    rows = pd.concat([_rows(famex[keep], IN), _rows(famex[~keep], OUTLIER),
                      _rows(own, OWN_PART), _rows(old, SUPERSEDED),
                      _rows(_pick(tokens, **where), TOKEN)])

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
    real = g[~g.SKIPPED]
    keep = _mad_keep(real.LOG_RATIO)

    rows = pd.concat([_rows(real[keep], IN), _rows(real[~keep], OUTLIER),
                      _rows(g[g.SKIPPED], SKIPPED)])

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
    multi-load population runs at a ratio of 0.574 against 0.961 for single
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
        return _pack(_rows(over, MULTILOAD), 0, {})

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
    rows = pd.concat([_rows(tested[keep], IN), _rows(tested[~keep], OUTLIER),
                      _rows(own, OWN_PART), _rows(over, MULTILOAD)])

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
    H0_v2_UPDATE_LIST.xlsx. The consolidated sheets round the ratio to three
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
