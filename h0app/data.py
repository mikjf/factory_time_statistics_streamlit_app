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


def actions():
    """01_Actions, with the review flag recomputed.

    REVIEW_FLAG lives on the three execution sheets rather than here, but the
    rule is a plain band on the ratio and the reviewer wants to see it while
    scanning decisions, not only when keying them in.
    """
    a = update_list("01_Actions").copy()
    a["NEEDS_REVIEW"] = ((a.RATIO < pipeline.REVIEW_LO)
                         | (a.RATIO > pipeline.REVIEW_HI))
    return a


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


def all_units(operation):
    """Every part x sequence the run analysis looked at, verdict included.

    This is what answers "why is my part not on the list" - the sheet carries
    the units that came out clean and the ones that were never testable, and
    those are different answers.
    """
    return parts_book(operation, "05_AllUnits_WithEvidence")
