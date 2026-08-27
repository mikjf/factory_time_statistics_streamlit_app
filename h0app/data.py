"""Cached readers for the workbooks the pipeline produced.

Every reader takes a `key` from paths.cache_key() so the cache turns over when
the file underneath it does. That argument is never read - it exists purely to
be hashed. Passing it as `_key` would tell streamlit to skip hashing it, which
is exactly backwards, so the name has no underscore on purpose.

Reading is lazy per operation. There are 94 per-operation workbooks and only the
selected one is ever opened.
"""

import numpy as np
import pandas as pd
import streamlit as st

from . import paths, pipeline

# The sequence column is called SEQ in the update lists, OPERATION_SEQUENCE in
# the setup and load workbooks and SEQUENCE in 01_Actions. One name here.
SEQ = "SEQUENCE"
_SEQ_ALIASES = {"SEQ": SEQ, "OPERATION_SEQUENCE": SEQ}


def _norm(df):
    return df.rename(columns=_SEQ_ALIASES)


@st.cache_data(show_spinner=False)
def _read(path, sheet, key):
    return _norm(pd.read_excel(path, sheet_name=sheet))


def update_list(sheet):
    return _read(paths.UPDATE_LIST, sheet, paths.cache_key(paths.UPDATE_LIST))


def setup_book(sheet):
    return _read(paths.SETUP, sheet, paths.cache_key(paths.SETUP))


def load_book(sheet):
    return _read(paths.LOAD, sheet, paths.cache_key(paths.LOAD))


def parts_book(operation, sheet):
    p = pipeline.parts_workbook(operation)
    return _read(p, sheet, paths.cache_key(p))


def family_book(operation, sheet):
    p = pipeline.family_workbook(operation)
    return _read(p, sheet, paths.cache_key(p))


def has_setup():
    return paths.mtime(paths.SETUP) is not None


def has_load():
    return paths.mtime(paths.LOAD) is not None


@st.cache_data(show_spinner="Reading the per-operation workbooks...")
def operations(key):
    """One row per operation, from each part-level workbook's 00_Summary.

    Read once and cached on the workbooks' mtimes. It is 47 small reads, which
    is why nothing else in the app opens more than the one workbook it needs -
    but the funnel on the landing page has to count the whole analysis, and
    these sheets already hold every stage of it.

    Labels are matched on a prefix because they carry the thresholds inside
    them: "  ...testable (n >= 6)" becomes "  ...testable (n >= 8)" the day
    MIN_WO changes, and an exact match would silently start returning nothing.
    """
    rows = []
    for p in sorted(paths.ROOT.glob("H0_v2_*_PARTS.xlsx")):
        s = pd.read_excel(p, sheet_name="00_Summary")
        m = {str(k).strip(): v for k, v in zip(s.METRIC, s.VALUE)}
        h = {str(k).strip(): v for k, v in zip(s.METRIC, s.HOURS)}

        def get(prefix, src=m, default=0):
            for k, v in src.items():
                if k.startswith(prefix):
                    return v
            return default

        rows.append({
            "OPERATION": str(m.get("Operation", "")).strip(),
            "WORK_ORDERS": pd.to_numeric(get("Work orders in scope"),
                                         errors="coerce"),
            "TOKENS": pd.to_numeric(get("...token"), errors="coerce"),
            "UNITS": pd.to_numeric(get("Units (part"), errors="coerce"),
            "TESTABLE": pd.to_numeric(get("...testable"), errors="coerce"),
            "SIGNIFICANT": pd.to_numeric(get("...statistically"),
                                         errors="coerce"),
            "MATERIAL": pd.to_numeric(get("...material"), errors="coerce"),
            "HOURS_IN_SCOPE": pd.to_numeric(h.get("Work orders in scope"),
                                            errors="coerce"),
            "NOTHING_TESTABLE": any(str(k).startswith("NOTHING TESTABLE")
                                    for k in m),
        })
    out = pd.DataFrame(rows).fillna({"WORK_ORDERS": 0, "TOKENS": 0, "UNITS": 0,
                                     "TESTABLE": 0, "SIGNIFICANT": 0,
                                     "MATERIAL": 0})
    return out.sort_values("OPERATION").reset_index(drop=True)


def operation_summaries():
    return operations(paths.cache_key(*sorted(
        paths.ROOT.glob("H0_v2_*_PARTS.xlsx"))))


def operation_list():
    return operation_summaries().OPERATION.tolist()


def skip_hours_total():
    """Hours charged for setups never performed, ACROSS EVERY STEP.

    03_SkipRate lists only steps with SETUP_MIN or more work orders, so summing
    it comes up short - 540 h against a true 591 h on the current extract. The
    whole figure is the one 00_Summary carries, which is also what the README
    and the workbook quote, so reading it rather than recomputing keeps the
    three in step.

    Falls back to the sheet's own sum if that summary row is ever renamed, so a
    changed label degrades to a smaller number rather than to an exception.
    """
    skip = setup_book("03_SkipRate")
    try:
        sm = setup_book("00_Summary")
        row = sm[sm.METRIC.astype(str).str.strip()
                 == "Standard charged for setups never performed"]
        if len(row):
            return float(row.HOURS.iloc[0])
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return float(skip.STANDARD_CHARGED_SKIPPED.sum())


# ---- the multi-load gap ----------------------------------------------------
# RECOMPUTED, NOT READ, and it is the only finding on that page that has to be.
# 04_MultiLoadGap is four rows, one per operation, and 05_Evidence holds the
# SINGLE-load steps only - the multi-load population never reaches a sheet at
# part level. A Family filter has nothing to filter on unless the frame is
# rebuilt here.
#
# load_view.load() only reads the parquet; see the note at the top of
# pipeline.py on which of the pipeline's loaders are safe to call.


@st.cache_data(show_spinner=False)
def _multi(key):
    return _norm(pipeline.load_view.load()[1])


def multi_load_rows():
    """One row per multi-load work order at one routing step - 557 of them.

    The frame the tiles count off. A work order is distinct here even where it
    appears at two sequences, so counting it once is possible; on any
    aggregate, including 04_MultiLoadGap, it is not.
    """
    return _multi(paths.cache_key(paths.CACHE))


def multi_loads(frame=None):
    """Multi-load work orders at PART grain - one row, one standard.

    FAMILY x PART_TYPE x SEQUENCE x OPERATION x PART_ID. Started as the family
    grain the other two findings use, and that pooled parts that do not share
    a load size: one row could show `Loads, median 9 / max 14` because two
    parts basket at 40 pieces and two at 25, the family average hiding the
    physical fact that explains the row. RUN_MASTER and LOAD_SIZE are per-part
    routing fields, so at part grain every row carries exactly one of each -
    confirmed on the current extract, 0 of 240 rows mix either.

    That makes RUN_EFF and LOAD_SIZE plain `"first"` rather than a fitted
    average: there is one value to take. MEDIAN_LOADS / MAX_LOADS stay
    meaningful too - 39 of 240 parts still see their own load count vary
    across their own work orders, from quantity alone.

    Pass an already-filtered multi_load_rows() to keep this table and the
    figures above it describing the same set.
    """
    m = multi_load_rows() if frame is None else frame
    g = (m.groupby(["FAMILY", "PART_TYPE", SEQ, "OPERATION", "PART_ID"],
                   dropna=False)
          .agg(WORK_ORDERS=("WORK_ORDER", "nunique"),
               RUN_EFF=("RUN_MASTER", "first"),
               LOAD_SIZE=("LOAD_SIZE", "first"),
               MEDIAN_LOADS=("LOADS_CHARGED", "median"),
               MAX_LOADS=("LOADS_CHARGED", "max"),
               HOURS_MASTER=("HOURS_MASTER", "sum"),
               HOURS_WORKED=("HOURS_WORKED", "sum"))
          .reset_index())
    g["MASTER_PER_WO"] = g.HOURS_MASTER / g.WORK_ORDERS
    g["OVER_RESERVED_HOURS"] = g.HOURS_MASTER - g.HOURS_WORKED
    g["RATIO"] = g.HOURS_WORKED / g.HOURS_MASTER
    return g.sort_values("OVER_RESERVED_HOURS", ascending=False)


@st.cache_data(show_spinner=False)
def _multi_facts(key):
    one, multi = pipeline.load_view.load()
    n1, nm = len(one), len(multi)
    return {"RATIO_ONE": float(one.HOURS_WORKED.sum() / one.HOURS_MASTER.sum()),
            "RATIO_MULTI": float(multi.HOURS_WORKED.sum()
                                 / multi.HOURS_MASTER.sum()),
            "STEPS_ONE": n1, "STEPS_MULTI": nm,
            "SHARE_ONE": n1 / (n1 + nm) if n1 + nm else float("nan")}


def multi_load_facts():
    """The two pooled ratios the explanation on that page quotes.

    Hardcoded until now, and they had drifted: the text said single load ran at
    0.96 - "the standard is roughly right" - against a live 1.119, which is not
    the same claim nor even the same direction. Read them instead.
    """
    return _multi_facts(paths.cache_key(paths.CACHE))


@st.cache_data(show_spinner=False)
def _run_by_operation(key):
    _, multi = pipeline.load_view.load()
    return multi.groupby("OPERATION").RUN_MASTER.median()


def run_by_operation():
    """RUN's median among each operation's multi-load parts.

    04_MultiLoadGap stores MARGINAL_AS_PCT_OF_RUN but not the RUN it was taken
    against, so the percentage there is not independently checkable. This is
    the same median h0_v2_load_view.py's own fit loop divides by - g.RUN_MASTER
    .median() inside multi.groupby("OPERATION") - read fresh rather than
    back-derived from two already-rounded sheet columns, which would drift.
    """
    return _run_by_operation(paths.cache_key(paths.CACHE))


def actions():
    """01_Actions, with the review flag recomputed and the value to key attached.

    REVIEW_FLAG lives on the three execution sheets rather than here, but the
    rule is a plain band on the ratio and the reviewer wants to see it while
    scanning decisions, not only when keying them in.

    TO_KEY COMES FROM THE EXECUTION SHEETS, which is why this function reaches
    into them at all. It is RM_RECOMMENDED, the column h0_v2_update_list calls
    "the exact RUN_MASTER to apply", and it is what a reviewer keys.

    IT NOW EQUALS SUGGESTED_VALUE ON EVERY PART ROW, and that is the point. A
    part that cleared all six rules on its own evidence keeps its own figure;
    the family value covers only the parts that could not be judged alone, and
    h0_v2_family_view removes the flagged parts from the family pool before
    computing it. Until 2026-08-26 a rule here overrode 17 of the 64 part rows
    with a family figure pooled over ALL parts - including the ones being
    overwritten - which was circular and has been removed.

    So the join is now a consistency check rather than a correction: if TO_KEY
    ever differs from SUGGESTED_VALUE on a part row again, something upstream
    has changed and should be understood before it is shown to anyone.

    TO_KEY_CHANGE_PCT COMES WITH IT, always. CHANGE_PCT on 01_Actions is derived
    from SUGGESTED_VALUE on all 59, so showing the recommended value beside the
    suggested value's percentage would put a row on screen that contradicts its
    own arithmetic - 120.00 to 90.50 labelled -31.1% when it is -24.6%.

    PART-LEVEL ROWS ONLY. A family row is left exactly as 01_Actions wrote it,
    and that is a scoping decision rather than an oversight.

    A part-level action names one part, so the join to its execution row is 1:1
    and the value is unambiguous. A family action names a pool, and 01_Actions
    gives it ONE representative pair whose RATIO is right and whose absolute
    values are an hours-weighted blend across parts that may run different
    standards. On one bending step every part of the pool sits at 90.00 and the
    sheet reports 44.98 - a crewed routing whose master hours are stated per
    operator. Setup and HRS/LOAD have the same shape for a different reason:
    their recommendation is each part's own value times a shared ratio, so a
    pool with parts at 1.9 and 1.4 carries a single blended pair on 01_Actions.

    So a family pool has no single number to key in those cases, and dropping
    the sheet's blended pair for one part's value would be a different error
    from the one being fixed. That question is open and belongs with the blend
    itself, not here.
    """
    a = update_list("01_Actions").copy()
    a["NEEDS_REVIEW"] = ((a.RATIO < pipeline.REVIEW_LO)
                         | (a.RATIO > pipeline.REVIEW_HI))

    # edits() is the same normalisation By part reads, which is the page that
    # has always shown the right number. Joining through it makes By part the
    # reference for the other two rather than a fourth opinion.
    e = edits().rename(columns={"TARGET_COLUMN": "TARGET"})
    e = e.assign(ROUTE=e.ROUTE.astype(str).str.upper())
    K = ["FAMILY", "PART_TYPE", "OPERATION", SEQ, "TARGET", "RUN_TYPE"]
    cols = {"RECOMMENDED": "TO_KEY", "CHANGE": "TO_KEY_CHANGE_PCT",
            "BASIS": "TO_KEY_BASIS"}

    part = (e[e.ROUTE == "PART"][K + ["PART_ID"] + list(cols)]
            .rename(columns=cols))

    # ROW ORDER IS PRESERVED EXPLICITLY. A merge resets the index and the two
    # halves are concatenated, so without this the queue's rows would come back
    # in a different order than the sheet - and the dataframe's row selection is
    # positional.
    a["_ORD"] = range(len(a))
    is_part = a.LEVEL.astype(str).str.upper() == "PART"
    fam = a[~is_part].assign(TO_KEY=lambda d: d.SUGGESTED_VALUE,
                             TO_KEY_CHANGE_PCT=lambda d: d.CHANGE_PCT,
                             TO_KEY_BASIS="family")
    a = pd.concat([a[is_part].merge(part, on=K + ["PART_ID"], how="left"), fam])
    a = a.sort_values("_ORD").drop(columns="_ORD").reset_index(drop=True)

    # ---- CHANGE % WHERE THERE IS NO SINGLE VALUE -----------------------------
    # 01_Actions computes CHANGE_PCT as (SUGGESTED / CURRENT - 1), so it comes
    # back blank on the rows whose family runs several different current values:
    # there is no single CURRENT and no single SUGGESTED, so the division has
    # nothing to work with.
    #
    # BUT THE PERCENTAGE IS STILL WELL DEFINED. Every part in that family is
    # corrected by the SAME ratio, so they all move by the same proportion even
    # though they start and end at different absolute values. The ratio carries
    # it, and the ratio is present on all of those rows.
    #
    # PCS/HR holds a RATE, so the correction DIVIDES and the change is
    # (1/ratio - 1). Setup and HRS/LOAD hold DURATIONS, so it multiplies and the
    # change is (ratio - 1). Getting that backwards would print a plausible
    # number with the wrong sign, which is the one failure this column cannot
    # afford - see EFFECT on the Review queue.
    #
    # Checked against the 216 rows that carry both: derived agrees with stored
    # to within 2 percentage points on every one, and within 0.5 on 95%. The
    # residue is tidy() rounding the suggested value before the stored figure is
    # computed from it; the derived one comes off the unrounded ratio.
    #
    # ONLY FILLS BLANKS. Where 01_Actions has a figure it is left alone, so the
    # two never compete for the same cell.
    gap = a.TO_KEY_CHANGE_PCT.isna() & a.RATIO.notna() & (a.RATIO > 0)
    if gap.any():
        rate = (a.TARGET == "RUN") & (a.RUN_TYPE == "PCS/HR")
        derived = np.where(rate, (1 / a.RATIO - 1) * 100, (a.RATIO - 1) * 100)
        a.loc[gap, "TO_KEY_CHANGE_PCT"] = np.round(derived[gap.values], 1)
    return a


def action_row(target, run_type, operation, family, part_type, seq,
               part_id=None):
    """The 01_Actions row for one unit, TO_KEY included, or None.

    Inspect reaches its numbers through the per-operation workbooks rather than
    through 01_Actions, so it cannot see TO_KEY without asking for it. It only
    needs it on units that carry an action - the value is shown under "Change it
    to", which a non-action unit does not render - and every action has a row
    here by construction.

    Matched on the full key including LEVEL, because one family and step can
    carry both a family action and a part action, and the two propose different
    values. Without the level the first match would win by sheet order.
    """
    a = actions()
    lvl = "PART" if part_id is not None else "FAMILY"
    m = ((a.TARGET == target) & (a.RUN_TYPE == run_type)
         & (a.OPERATION == operation) & (a.FAMILY == family)
         & (a.PART_TYPE == part_type) & (a[SEQ] == seq)
         & (a.LEVEL.astype(str).str.upper() == lvl))
    if part_id is not None:
        m &= (a.PART_ID == part_id)
    hit = a[m]
    return hit.iloc[0] if len(hit) else None


def edits():
    """Every field edit across the three execution sheets, one shape.

    02/03/04 write to different columns and cannot be merged in the workbook -
    that would invite keying a duration into a rate. For looking a part up they
    do need to come together, so this normalises the value columns and keeps
    TARGET_COLUMN as the thing that says which field each row edits.
    """
    frames = []
    run = update_list("02_RunUpdateList")
    frames.append(run.assign(
        CURRENT=run.RM_CURRENT, RECOMMENDED=run.RM_RECOMMENDED,
        CHANGE=run.CHANGE_PCT_RECOMMENDED, RUN_TYPE="PCS/HR",
        EVIDENCE_N=run.N_WO_EVIDENCE, BASIS=run.RECOMMENDED_BASIS))
    if has_setup():
        s = update_list("03_SetupUpdateList")
        frames.append(s.assign(
            CURRENT=s.SETUP_HRS_CURRENT, RECOMMENDED=s.SETUP_HRS_RECOMMENDED,
            CHANGE=s.CHANGE_PCT, RUN_TYPE="-", EVIDENCE_N=s.N_SETUPS,
            BASIS="family - setup is never judged per part"))
    if has_load():
        ld = update_list("04_LoadUpdateList")
        frames.append(ld.assign(
            CURRENT=ld.RUN_CURRENT, RECOMMENDED=ld.RUN_RECOMMENDED,
            CHANGE=ld.CHANGE_PCT, RUN_TYPE="HRS/LOAD",
            EVIDENCE_N=ld.N_WO_EVIDENCE,
            BASIS=np.where(ld.ROUTE == "PART", "part", "family")))
    cols = ["OPERATION", "FAMILY", "PART_TYPE", "PART_ID", SEQ, "ROUTE",
            "TARGET_COLUMN", "RUN_TYPE", "MASTER_OPS_ROWID", "ROWID_FOUND",
            "CURRENT", "RECOMMENDED", "CHANGE", "BASIS", "RATIO", "EVIDENCE_N",
            "REVIEW_FLAG", "LAST_DATE"]
    return pd.concat([f[cols] for f in frames], ignore_index=True)


@st.cache_data(show_spinner=False)
def _known_parts(key):
    return set(pd.read_parquet(paths.CACHE, columns=["PART_ID"])
               .PART_ID.str.strip().unique())


def known_parts():
    """Every part number the extract contains, at all.

    Needed because "has no PCS/HR run unit" is NOT the same as "does not
    exist". 54 real parts have no run unit - every ticket of theirs was a token
    booking, or rework, or a routing step no longer in the master revision - and
    telling their owner the part is not in the extract is a worse answer than
    the false all-clear it replaced. Reads one column, so it is cheap.
    """
    return _known_parts(paths.cache_key(paths.CACHE))


@st.cache_data(show_spinner=False)
def _master_hours(key):
    """Master hours each family carried over the fiscal year.

    The denominator for "how wrong is this family", as opposed to "how many
    hours". RUN ONLY, matching a run-only numerator, so the percentage means
    exactly one thing and needs no caveat.

    It counts the family's whole in-scope run workload, including operations
    where nothing was flagged. That is the conservative reading: "of all the
    master run time this family carries, this much is misstated", rather than
    the narrower and larger "of the steps we are changing".
    """
    df = pd.read_parquet(paths.CACHE, columns=[
        "FAMILY", "PART_TYPE", "LT_TYPE", "OPERATION", "MASTER_OPS_ROWID",
        "LAST_TRANSACTION_DATE", "HOURS_MASTER", "HOURS_WORKED"])
    for c in ["FAMILY", "PART_TYPE", "LT_TYPE", "OPERATION"]:
        df[c] = df[c].str.strip()
    df["LAST_TRANSACTION_DATE"] = pd.to_datetime(df.LAST_TRANSACTION_DATE,
                                                 errors="coerce")
    scope = ((df.LT_TYPE == "Run")
             & ~df.OPERATION.str.upper().str.startswith("S RIL")
             & (df.LAST_TRANSACTION_DATE >= pd.Timestamp(pipeline.FY_START))
             & (df.HOURS_MASTER > 0) & (df.HOURS_WORKED > 0)
             & df.MASTER_OPS_ROWID.notna())
    return (df[scope].groupby(["FAMILY", "PART_TYPE"], as_index=False)
            .HOURS_MASTER.sum().rename(columns={"HOURS_MASTER": "MASTER_H"}))


def master_hours_by_family():
    return _master_hours(paths.cache_key(paths.CACHE))


def _run_actions():
    """Actions that edit a RUN standard - PCS/HR and HRS/LOAD, no setup.

    05_FamilyTotals and 00_Summary both bundle setup in, which is right for the
    headline but wrong for anything compared against run hours. Setup is judged
    on a different population with a different floor, so mixing it into a run
    ranking silently changes what the ranking means.
    """
    a = actions()
    a = a[a.TARGET == "RUN"]
    return a.assign(ABS=a.HOURS_DELTA.abs())


def run_gross_by_operation():
    return (_run_actions().groupby("OPERATION", as_index=False)
            .ABS.sum().rename(columns={"ABS": "GROSS_HOURS"}))


def run_gross_by_family():
    return (_run_actions().groupby(["FAMILY", "PART_TYPE"], as_index=False)
            .ABS.sum().rename(columns={"ABS": "GROSS_HOURS"}))


def _by_type(keys):
    """PCS/HR and HRS/LOAD as two columns instead of one row each.

    For the chart tooltips only - run_gross_by_operation/family stay at one
    row per bar, which is what sets its height and its rank. S SABBIARE mixes
    both run types (45 h HRS/LOAD, 55 h PCS/HR) despite sitting outside the
    operation top ten today, so a single run-type label per bar would be
    correct now and silently wrong the moment it grows into it - the split is
    shown regardless of whether a given row actually mixes.
    """
    g = (_run_actions().groupby(keys + ["RUN_TYPE"], as_index=False)
         .ABS.sum().rename(columns={"ABS": "GROSS_HOURS"}))
    p = (g.pivot(index=keys, columns="RUN_TYPE", values="GROSS_HOURS")
          .reindex(columns=["PCS/HR", "HRS/LOAD"], fill_value=0)
          .fillna(0))
    p.columns = ["PCSHR_HOURS", "HRSLOAD_HOURS"]
    return p.reset_index()


def run_gross_by_operation_by_type():
    return _by_type(["OPERATION"])


def run_gross_by_family_by_type():
    return _by_type(["FAMILY", "PART_TYPE"])


def most_wrong_families(floor_h, top=10):
    """Run misstatement as a share of the family's master run hours.

    Both sides run only, so the figure means exactly one thing: of the master
    run time this family carries, this much is misstated.
    """
    d = (run_gross_by_family()
         .merge(master_hours_by_family(), on=["FAMILY", "PART_TYPE"],
                how="left"))
    d = d[d.MASTER_H >= floor_h].copy()
    d["PCT"] = 100 * d.GROSS_HOURS / d.MASTER_H
    return d.nlargest(top, "PCT").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _extract_facts(key):
    """Shape and reach of the extract itself, before any analysis touches it."""
    df = pd.read_parquet(paths.CACHE, columns=[
        "WORK_ORDER", "PART_ID", "FAMILY", "OPERATION", "LT_TYPE",
        "LAST_TRANSACTION_DATE"])
    d = pd.to_datetime(df.LAST_TRANSACTION_DATE, errors="coerce")
    fy = d[d >= pd.Timestamp(pipeline.FY_START)]
    return {
        "rows": len(df),
        "work_orders": df.WORK_ORDER.str.strip().nunique(),
        "parts": df.PART_ID.str.strip().nunique(),
        "families": df.FAMILY.str.strip().nunique(),
        "operations": df.OPERATION.str.strip().nunique(),
        "first": fy.min(), "last": fy.max(),
        "months": (fy.max() - fy.min()).days / 30.44 if len(fy) else 0,
    }


def extract_facts():
    return _extract_facts(paths.cache_key(paths.CACHE))


@st.cache_data(show_spinner=False)
def _extract_span(key):
    """Earliest and latest booking in the extract, before any filtering.

    Deliberately not taken from extract_facts(), which reports dates from
    FY_START onward - that would hide the very thing this is watching for.
    Reads one column.
    """
    d = pd.to_datetime(
        pd.read_parquet(paths.CACHE, columns=["LAST_TRANSACTION_DATE"])
        .LAST_TRANSACTION_DATE, errors="coerce")
    return d.min(), d.max()


def extract_span():
    return _extract_span(paths.cache_key(paths.CACHE))


# The exclusions, in the order they are reported. ORDER IS AN ATTRIBUTION
# DECISION AND NOTHING ELSE - the surviving total is identical whichever way
# round they run, because every ticket that matches any rule leaves.
#
# What order buys is a sensible answer to "why did this one go". The rules
# overlap heavily: a rework step usually also carries no master hours, so on
# independent counts it appears under both and the two columns sum to half as
# much again as the extract holds. Applied in sequence each ticket is counted
# once, against the first rule it meets, and the column reconciles.
#
# So rules that say what a ticket IS come before rules that say what it LACKS.
# Rework is reported as rework rather than as a step with no standard, and a
# reversal as a reversal rather than as a ticket with no time on it. Reordering
# these moves tickets between rows and changes nothing else.
#
# The third field says whether the rule is DESCRIBED to the reader. All of them
# run; one is not worth explaining. The fiscal-year bound is a mirror of the
# query's own lower bound - the window opens at FY_START and runs forward with
# no upper end, so a ticket can only fall foul of this by predating the year,
# and the query already refuses those at source. It stays in the list so the
# surviving total keeps matching the analysis scope filter exactly, which is the
# whole claim the deduction table makes. Describing it invited the reader to
# think the year is closed at both ends. It is not.
EXCLUSIONS = [
    ("Booked before the fiscal year opened",
     lambda d, fy: d.LAST_TRANSACTION_DATE < fy, False),
    ("Rework",
     lambda d, fy: d.OPERATION.str.upper().str.startswith("S RIL"), True),
    ("Ticket negative correction",
     lambda d, fy: d.HOURS_WORKED < 0, True),
    ("Step is no longer in the master routing",
     lambda d, fy: d.MASTER_OPS_ROWID.isna(), True),
    ("Step carries no master hours to compare against",
     lambda d, fy: ~(d.HOURS_MASTER > 0), True),
    ("Nothing was booked against it",
     lambda d, fy: d.HOURS_WORKED <= 0, True),
]


@st.cache_data(show_spinner=False)
def _deduction(key):
    """Extract → exclusions → what an analysis actually sees, and its split.

    Returns (rows, split, kept) where rows and split are lists of
    (label, tickets, hours) and kept is the surviving (tickets, hours).

    The three-way split is asserted exhaustive rather than trusted: a ticket
    that fell outside all three would silently shrink the table's own total,
    which is the one failure a reader cannot see.
    """
    df = pipeline.read_extract()
    fy = pd.Timestamp(pipeline.FY_START)

    rows, left = [], df
    for label, rule, _ in EXCLUSIONS:
        m = rule(left, fy)
        gone, left = left[m], left[~m]
        rows.append((label, -len(gone), -gone.HOURS_WORKED.sum()))

    # Labelled by the unit the master is held in, not by a paraphrase of it.
    # "pieces per hour" and "hours per load" are what PCS/HR and HRS/LOAD
    # literally expand to, so a reader can see straight off that the first is a
    # rate and the second a duration - which is the whole reason a correction
    # divides one and multiplies the other.
    is_run = left.LT_TYPE == "Run"
    parts = [
        ("Run master pieces per hour (PCS/HR)",
         is_run & (left.RUN_TYPE_MASTER == "PCS/HR")),
        ("Run master hours per load (HRS/LOAD)",
         is_run & (left.RUN_TYPE_MASTER == "HRS/LOAD")),
        ("Setup hours", left.LT_TYPE == "Setup"),
    ]
    covered = pd.concat([m for _, m in parts], axis=1).any(axis=1)
    assert not (~covered).any(), "the three-way split must be exhaustive"

    split = [(label, int(m.sum()), left.loc[m, "HOURS_WORKED"].sum())
             for label, m in parts]
    return (len(df), df.HOURS_WORKED.sum()), rows, split, \
        (len(left), left.HOURS_WORKED.sum())


def deduction():
    return _deduction(paths.cache_key(paths.CACHE))


@st.cache_data(show_spinner=False)
def _run_funnel(key):
    """The PCS/HR run funnel's first two bars, at the grain the analysis uses.

    The per-operation workbooks publish "Work orders in scope", which is
    nunique(WORK_ORDER) WITHIN an operation and summed across them - so a work
    order that meets the same operation at two sequences counts once, while the
    analysis tests it twice. That total (19,050) matches nothing else on the
    page: not the booking-line count above it, not the unit count below it.

    to_wo_level is the real grain - one row per standard per work order - and it
    lands within one row of the booking-line count, so the funnel can open where
    the
    deduction table closed instead of silently changing what it counts.
    """
    df = pipeline.read_extract()
    sc = df[(df.LT_TYPE == "Run") & (df.RUN_TYPE_MASTER == "PCS/HR")
            & ~df.OPERATION.str.upper().str.startswith("S RIL")
            & (df.LAST_TRANSACTION_DATE >= pd.Timestamp(pipeline.FY_START))
            & (df.RUN_MASTER > 0) & (df.HOURS_MASTER > 0)
            & (df.HOURS_WORKED > 0) & df.MASTER_OPS_ROWID.notna()]
    wo = pipeline.to_wo_level(sc)
    kept, tokens = pipeline.drop_token_bookings(wo)
    # "lines", not "tickets": len(sc) counts EXTRACT ROWS, each already the sum
    # of however many labour tickets the query folded into it. The old name is
    # what put "PCS/HR run tickets" under a bar that counts rows.
    return {"lines": len(sc), "at_a_standard": len(wo),
            "with_duration": len(kept), "tokens": len(tokens)}


def run_funnel():
    return _run_funnel(paths.cache_key(paths.CACHE))


@st.cache_data(show_spinner="Reading the family workbooks...")
def _family_funnel(key):
    """The second route to a decision: pools judged as a family.

    A part that cannot clear the 6-work-order floor alone is not dropped. Its
    work orders join the rest of its family at the same step, and the pool is
    put through the same six rules. That route produces most of the PCS/HR run
    decisions - the family route runs to roughly twice the part route - and
    the part-level funnel does not show it. No counts here: they move with
    every extract and the funnels on Methodology carry the live ones.

    Read from 01_FamilyRollup rather than recomputed. The pooling excludes
    parts already flagged individually, which is a rule of the family script
    and not something to reproduce here from the outside.
    """
    rows = []
    for f in paths.ROOT.glob("H0_v2_S_*_FAMILY.xlsx"):
        try:
            d = pd.read_excel(f, sheet_name="01_FamilyRollup")
        except Exception:
            continue
        if len(d):
            rows.append(d)
    if not rows:
        return None
    d = pd.concat(rows, ignore_index=True)

    v = d.FAMEX_VERDICT.astype(str)
    a = pipeline.ALPHA
    testable = d[d.FAMEX_WO >= pipeline.MIN_WO]
    different = testable[
        (testable.FAMEX_P_WILCOXON < a) & (testable.FAMEX_Q_VALUE < a)
        & ~((testable.FAMEX_CI95_LOW <= 1) & (testable.FAMEX_CI95_HIGH >= 1))]
    return {
        "pools": len(d),
        "testable": len(testable),
        "different": len(different),
        "material": int(v.str.startswith("UPDATE").sum()),
        "parts_in_pools": int(d.FAMEX_PARTS.sum()),
        "parts_excluded": int(d.PARTS_FLAGGED_UPDATE.sum()),
    }


def family_funnel():
    return _family_funnel(paths.cache_key(paths.UPDATE_LIST))


@st.cache_data(show_spinner=False)
def _reconciliation(key):
    """Every decision by route, tying the three headline figures together.

    Returns (rows, total). A row is (label, actions, parts, edits, hours);
    the total is (actions, DISTINCT parts across all routes, edits, hours).

    The parts column does NOT add down and the total is not its sum. A part
    corrected on its run standard and again on its setup is two rows here and
    one part in the total - 1,296 against 945 on this extract. Actions, edits
    and hours all add, so only the one column needs saying out loud.

    Hours are absolute and taken PER ACTION before summing, which is the same
    convention as everywhere else in the tool: an operation with one family
    running long and another running short is wrong twice, and netting them
    would report it as nearly right.

    Setup has no part-level route at all: setup units average under four worked
    hours over the whole window, so nothing clears a materiality gate alone. An empty row
    would look like a gap rather than a decision, so routes with nothing in
    them are dropped and the caption carries the reason.
    """
    a = pd.read_excel(paths.UPDATE_LIST, sheet_name="01_Actions")
    spec = [("02_RunUpdateList", "RUN", "PCS/HR", "Run `PCS/HR`"),
            ("04_LoadUpdateList", "RUN", "HRS/LOAD", "Run `HRS/LOAD`"),
            ("03_SetupUpdateList", "SETUP_HRS", None, "Setup")]

    rows, seen = [], set()
    total_actions = total_edits = 0
    total_hours = 0.0
    for sheet, target, run_type, label in spec:
        d = pd.read_excel(paths.UPDATE_LIST, sheet_name=sheet)
        seen |= set(d.PART_ID.astype(str).str.strip())
        for route in ("PART", "FAMILY"):
            sub = d[d.ROUTE.astype(str).str.upper() == route]
            act = a[(a.TARGET == target) & (a.LEVEL == route)]
            if run_type:
                act = act[act.RUN_TYPE == run_type]
            if not len(act) and not len(sub):
                continue
            hours = act.HOURS_DELTA.abs().sum()
            rows.append((f"{label} — {route.lower()}", len(act),
                         sub.PART_ID.astype(str).str.strip().nunique(),
                         len(sub), hours))
            total_actions += len(act)
            total_edits += len(sub)
            total_hours += hours
    return rows, (total_actions, len(seen), total_edits, total_hours)


def reconciliation():
    return _reconciliation(paths.cache_key(paths.UPDATE_LIST))


@st.cache_data(show_spinner=False)
def _keying(key):
    """What a reader actually has to type in, and what to be wary of.

    Three things the workbook knows and no page was saying:

    - HOW_TO_APPLY, which is not one instruction but six, writing to three
      different fields. A family row and a part row read almost alike and go to
      different places.
    - the family decisions carrying no single value, because the family holds
      several different RUN_MASTER values. Those show a blank where every other
      row shows a figure, and the instruction is to divide each part's own
      value by the ratio instead.
    - REVIEW_FLAG, which the pipeline sets on ratios outside 0.25-4.0. Sound
      by every one of the six rules and extreme enough to want a human first.
    """
    a = pd.read_excel(paths.UPDATE_LIST, sheet_name="01_Actions")
    run = pd.read_excel(paths.UPDATE_LIST, sheet_name="02_RunUpdateList")

    flagged = run[run.REVIEW_FLAG.notna()]
    no_value = a[a.SUGGESTED_VALUE.isna()]
    return {
        "how_to_apply": list(a.HOW_TO_APPLY.astype(str)
                             .value_counts().items()),
        "actions": len(a),
        "edits": len(run),
        "flagged": len(flagged),
        "flag_lo": flagged.RATIO.min() if len(flagged) else None,
        "flag_hi": flagged.RATIO.max() if len(flagged) else None,
        "no_value": len(no_value),
        "no_value_note": (no_value.HOW_TO_APPLY.astype(str).iloc[0]
                          if len(no_value) else ""),
        "fam_actions": int(((a.TARGET == "RUN") & (a.RUN_TYPE == "PCS/HR")
                            & (a.LEVEL == "FAMILY")).sum()),
        "fam_edits": int((run.ROUTE.astype(str).str.upper() == "FAMILY").sum()),
        # Run-only, to be compared against the run row count. "actions" is all
        # three lists and pairing it with the run row count compares a total
        # against a part of one.
        "run_actions": int(((a.TARGET == "RUN")
                            & (a.RUN_TYPE == "PCS/HR")).sum()),
    }


def keying():
    return _keying(paths.cache_key(paths.UPDATE_LIST))


@st.cache_data(show_spinner="Reading every operation's workbook...")
def _coverage(key):
    """Every operation examined, on every route, with what came of it.

    Replaces a table that counted only the PART-LEVEL PCS/HR run route. That
    one printed 0 in its Actions column for 13 operations that do have PCS/HR
    run actions, all of them family-level - a false zero on a table whose whole
    purpose is that a zero can be trusted and read.

    One row per operation, route AND LEVEL. Split by level because EXAMINED
    counts different things at each: a part-level pool is one part at one step,
    a family-level pool is one family at one step. Summing them, which this did
    at first, adds two units together and reports the result as one number -
    the same mistake the funnel's opening bar used to make.

    Setup appears at family level only. Setup units average under four worked
    hours over the whole window, so nothing clears a materiality gate alone.

    A zero in ACTIONS is readable off TESTABLE: testable pools and no action
    means tested and holding, no testable pools means there was not enough
    evidence either way.
    """
    a = pd.read_excel(paths.UPDATE_LIST, sheet_name="01_Actions")
    a["ROUTE"] = np.where(a.TARGET == "SETUP_HRS", "Setup",
                          "Run " + a.RUN_TYPE.astype(str))
    edits = {}
    for sheet, route in [("02_RunUpdateList", "Run PCS/HR"),
                         ("04_LoadUpdateList", "Run HRS/LOAD"),
                         ("03_SetupUpdateList", "Setup")]:
        edits[route] = pd.read_excel(paths.UPDATE_LIST, sheet_name=sheet)

    # (route, level, operation) -> [pools examined, pools testable]
    pools = {}

    # Run PCS/HR, part level: the per-operation workbooks already publish it.
    for _, r in operation_summaries().iterrows():
        pools[("Run PCS/HR", "Part", r.OPERATION)] = [int(r.UNITS),
                                                      int(r.TESTABLE)]

    # Run PCS/HR, family level: one rollup per operation workbook.
    for f in paths.ROOT.glob("H0_v2_S_*_FAMILY.xlsx"):
        try:
            d = pd.read_excel(f, sheet_name="01_FamilyRollup")
        except Exception:
            continue
        for op, g in d.groupby("OPERATION"):
            pools[("Run PCS/HR", "Family", str(op).strip())] = [
                len(g), int((g.FAMEX_WO >= pipeline.MIN_WO).sum())]

    # Setup and HRS/LOAD family pools, read off their verdict columns.
    for wb, sheet, route, verdict in [
            (paths.SETUP, "01_FamilyRollup", "Setup", "VERDICT"),
            (paths.LOAD, "02_FamilyRollup", "Run HRS/LOAD", "FAMEX_VERDICT")]:
        try:
            d = pd.read_excel(wb, sheet_name=sheet)
        except Exception:
            continue
        for op, g in d.groupby("OPERATION"):
            n_ins = int(g[verdict].astype(str).str.contains(
                "insufficient", case=False).sum())
            pools[(route, "Family", str(op).strip())] = [len(g),
                                                         len(g) - n_ins]

    # HRS/LOAD part units carry their own work-order count.
    try:
        d = pd.read_excel(paths.LOAD, sheet_name="01_PartUnits")
        for op, g in d.groupby("OPERATION"):
            pools[("Run HRS/LOAD", "Part", str(op).strip())] = [
                len(g), int((g.WO >= pipeline.MIN_WO).sum())]
    except Exception:
        pass

    # Part before Family within an operation, which alphabetical order gets
    # backwards. The two levels run in that order - a part is judged on its own
    # evidence first, and only what cannot clear the floor alone goes to its
    # family - so the rows should read the same way.
    _lvl = {"Part": 0, "Family": 1}
    rows = []
    for (route, level, op) in sorted(
            pools, key=lambda t: (t[2], t[0], _lvl.get(t[1], 9))):
        examined, testable = pools[(route, level, op)]
        act = a[(a.ROUTE == route) & (a.OPERATION == op)
                & (a.LEVEL.astype(str).str.title() == level)]
        ed = edits[route]
        ed = ed[(ed.OPERATION.astype(str).str.strip() == op)
                & (ed.ROUTE.astype(str).str.title() == level)]
        # Key order IS column order - pd.DataFrame keeps it. Narrowing first
        # (examined, testable, what it was worth, what came of it), then the
        # execution detail: how many masters to change and how much keying.
        rows.append({
            "OPERATION": op, "ROUTE": route, "LEVEL": level,
            "EXAMINED": examined, "TESTABLE": testable,
            "HOURS": act.HOURS_DELTA.abs().sum(),
            # Always says something. It used to print an em-dash wherever there
            # WERE actions, under a header reading "if none, why" - so the
            # commonest value in the column was a character the reader had to
            # decode as "question does not apply". Three states, one per row.
            "OUTCOME": ("changes proposed" if len(act) else
                        "tested and holds" if testable else
                        "not enough evidence"),
            "ACTIONS": len(act),
            "PARTS": ed.PART_ID.astype(str).str.strip().nunique(),
            "EDITS": len(ed),
        })
    return pd.DataFrame(rows)


def coverage():
    return _coverage(paths.cache_key(paths.UPDATE_LIST))


def all_units(operation):
    """Every part x sequence the run analysis looked at, verdict included.

    This is what answers "why is my part not on the list" - the sheet carries
    the units that came out clean and the ones that were never testable, and
    those are different answers.
    """
    return parts_book(operation, "05_AllUnits_WithEvidence")


@st.cache_data(show_spinner="Indexing the per-operation workbooks...")
def _run_index(key):
    """Which family appears at which operation and step, across the run
    analysis - the one thing the per-operation workbooks cannot answer alone.

    Setup and HRS/LOAD each have a single rollup covering every operation, so
    they need nothing like this. The PCS/HR run analysis writes one workbook per
    operation, so a picker that starts from the FAMILY has no list to offer
    until all of them have been read.

    47 reads, about 12 seconds, cached on the workbooks' own mtimes - the same
    trade operations() already makes for the summary sheets. Only the four key
    columns are kept, so what is held afterwards is roughly a thousand rows.

    Built from 05_AllUnits rather than from the extract: this sheet is exactly
    what the page can go on to show. Taking the combinations from the parquet
    instead would have offered families and steps that no unit exists for, and
    the reader would meet an empty page having chosen from a valid-looking list.
    """
    frames = []
    for op in operation_list():
        try:
            u = all_units(op)
        except (FileNotFoundError, KeyError, ValueError):
            continue
        if u is None or u.empty:
            continue           # an operation whose work orders were all tokens
        frames.append(u[["FAMILY", "PART_TYPE", SEQ]].assign(OPERATION=op))
    if not frames:
        return pd.DataFrame(columns=["FAMILY", "PART_TYPE", SEQ, "OPERATION"])
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def run_index():
    return _run_index(paths.cache_key(paths.UPDATE_LIST))
