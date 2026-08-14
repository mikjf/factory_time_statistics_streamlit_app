"""Refuse to show results that were built from a different extract.

A stale workbook looks completely normal. It has the right columns, plausible
numbers and a recent-looking date, and nothing on screen says it describes data
that has since been replaced. That has already cost this project once: an
extract was re-run to fix an arithmetic bug, came back with an identical row
count, and was assumed to be the same data - while ten families' routings had
been rebuilt underneath it and 8,549 hours had silently left scope.

A dashboard multiplies that risk, because the people reading it will not be the
people who ran the pipeline. So the ordering is checked before anything renders
and the two orderings that cannot be recovered from are hard stops, not
warnings. The mtimes are shown on the overview whether or not the check passed:
a check you can only see when it fails is a check nobody trusts.
"""

import pandas as pd
import streamlit as st

from . import paths


def _older(a, b):
    """True when a is strictly older than b (and both exist)."""
    ta, tb = paths.mtime(a), paths.mtime(b)
    return ta is not None and tb is not None and ta < tb


# A gap this size at the start of a fiscal year is not a quiet fortnight, it is
# a window that opens in the wrong place. Real drift is a whole year, so the
# threshold has enormous margin and will not fire on an ordinary slow start.
WINDOW_GAP_DAYS = 45


def _window_problems():
    """Does the extract actually cover the year the analysis thinks it does?

    The query and the analysis scripts each carry the fiscal year start, and
    they have to agree. They used to disagree by construction: the query derived
    its window from GETDATE() while every script hard-coded a date, so on the
    first of October the extract would begin a year later than the filters
    applied to it - and the analysis would report on a few weeks of data as
    though it had a year. Nothing about that failure looks wrong on screen.

    Comparing the extract's earliest booking against FY_START catches it. Loud
    rather than fatal: unlike the file-ordering checks this is a heuristic, and
    a genuinely late first booking - a shutdown, a plant coming back on line -
    should not lock everybody out of the tool.
    """
    # The import sits INSIDE the try with the call it serves. This check is the
    # heuristic one - "loud rather than fatal", as above - and an import that
    # cannot resolve is no more fatal than a span that cannot be read. Outside
    # the try it made the whole guard, which runs before anything renders,
    # depend on the analysis scripts being importable.
    try:
        from . import data, pipeline
        first, last = data.extract_span()
    except Exception:
        return []
    if first is None or pd.isna(first):
        return []
    fy = pd.Timestamp(pipeline.FY_START)
    gap = (first - fy).days
    if gap <= WINDOW_GAP_DAYS:
        return []
    return [("warn",
             f"**The extract may not cover the year the analysis is filtering "
             f"for.** It starts {first:%d %b %Y}, which is {gap} days after "
             f"`FY_START` ({fy:%d %b %Y}) — so anything booked in between is "
             f"missing rather than excluded, and every hours total here is "
             f"short by that much. Check that the date in `h0_v2.sql` still "
             f"matches `FY_START` in the analysis scripts; they are two ends of "
             f"the same setting and have to be changed together.")]


def problems():
    """Every ordering violation, worst first. Empty means the chain is sound."""
    out = []
    if paths.mtime(paths.CACHE) is None:
        out.append(("stop", f"`{paths.CACHE.name}` is missing. Nothing can be "
                            "shown until the pipeline has been run."))
        return out
    if paths.mtime(paths.UPDATE_LIST) is None:
        out.append(("stop", f"`{paths.UPDATE_LIST.name}` is missing. Run "
                            "`python h0_v2_update_list.py`."))
        return out

    if _older(paths.CACHE, paths.EXTRACT):
        out.append((
            "stop",
            f"`{paths.EXTRACT.name}` is newer than `{paths.CACHE.name}` "
            f"({paths.stamp(paths.EXTRACT)} against "
            f"{paths.stamp(paths.CACHE)}). A new extract has landed and the "
            "analysis has not been re-run against it, so everything below "
            "would describe the previous one. Re-run the pipeline."))

    if _older(paths.UPDATE_LIST, paths.CACHE):
        out.append((
            "stop",
            f"`{paths.UPDATE_LIST.name}` is older than `{paths.CACHE.name}` "
            f"({paths.stamp(paths.UPDATE_LIST)} against "
            f"{paths.stamp(paths.CACHE)}). The update list predates the data "
            "it claims to describe. Re-run every operation, then "
            "`python h0_v2_update_list.py`."))

    out += _window_problems()

    for wb in (paths.SETUP, paths.LOAD):
        if paths.mtime(wb) is None:
            out.append(("note", f"`{wb.name}` is not there, so that analysis "
                                "is not shown. The pipeline treats it as an "
                                "optional input in the same way."))
        elif _older(wb, paths.CACHE):
            out.append(("warn", f"`{wb.name}` is older than the extract "
                                f"({paths.stamp(wb)}). Its figures are from an "
                                "earlier run."))
    return out


def guard():
    """Render the problems and halt on anything fatal. Call it on every page."""
    found = problems()
    for level, msg in found:
        if level == "stop":
            st.error(msg, icon=":material/block:")
        elif level == "warn":
            st.warning(msg, icon=":material/warning:")
        else:
            st.info(msg, icon=":material/info:")
    if any(level == "stop" for level, _ in found):
        st.stop()


def operation_is_stale(operation):
    """True when this operation's workbook predates the extract.

    Checked per operation rather than globally because re-running one operation
    is routine, and a blanket warning on all 47 would be ignored within a day.
    """
    from . import pipeline
    return _older(pipeline.parts_workbook(operation), paths.CACHE)
