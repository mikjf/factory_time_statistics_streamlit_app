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
             f"short by that much. Check that the date in `fts.sql` still "
             f"matches `FY_START` in the analysis scripts; they are two ends of "
             f"the same setting and have to be changed together.")]


# THE WINDOW HAS NO UPPER BOUND. Every scope filter in the pipeline is
# `LAST_TRANSACTION_DATE >= FY_START` and nothing closes it, by design - so the
# span grows with every extract and will cross a year on the first pull taken
# after 1 Oct 2026.
#
# That is fine for the six rules, which only gain sample. It is not fine for
# MIN_HOURS_IMPACT, which is an ABSOLUTE 20 h: over 10 months it selects units
# worth 23 h a year, over 18 months units worth 13 h, over 24 months units worth
# 10 h. Nothing on the floor changes and the bar halves, so each rerun proposes
# more actions than the last and nobody can say why.
#
# Thirteen months rather than twelve, so an extract that lands a few weeks into
# the new fiscal year does not fire it on its first day.
WINDOW_LONG_MONTHS = 13
DAYS_PER_MONTH = 30.44


def _window_length_problem():
    """Warn once the span is long enough that the hours gate has drifted.

    A tripwire, not a fix. The remedy is a decision about the pipeline -
    annualise HOURS_DELTA against the span, or close the window - and both
    change which units qualify, so neither belongs in a viewer. What belongs
    here is making sure the day it starts to matter is not a day nobody
    noticed.
    """
    try:
        from . import data, pipeline
        first, last = data.extract_span()
    except Exception:
        return []
    if last is None or pd.isna(last):
        return []
    fy = pd.Timestamp(pipeline.FY_START)
    months = (last - fy).days / DAYS_PER_MONTH
    if months < WINDOW_LONG_MONTHS:
        return []
    effective = pipeline.MIN_HOURS_IMPACT * 12 / months
    return [("warn",
             f"**The window is now {months:.1f} months, and the materiality "
             f"gate has drifted with it.** Bookings run from "
             f"{fy:%d %b %Y} to {last:%d %b %Y}, and no filter closes the "
             f"window at a year. `MIN_HOURS_IMPACT` is an absolute "
             f"{pipeline.MIN_HOURS_IMPACT} h, so over this span it now selects "
             f"units worth about {effective:.0f} h a year rather than "
             f"{pipeline.MIN_HOURS_IMPACT} h — the bar falls as the window "
             f"grows, and each rerun will propose more actions than the last "
             f"without anything having changed on the floor. Decide whether to "
             f"annualise the gate before relying on the next update list.")]


def problems():
    """Every ordering violation, worst first. Empty means the chain is sound."""
    out = []
    if paths.mtime(paths.CACHE) is None:
        out.append(("stop", f"`{paths.CACHE.name}` is missing from "
                            f"`{paths.ROOT}`. Nothing can be shown until the "
                            "pipeline has been run there."))
        return out
    if paths.mtime(paths.UPDATE_LIST) is None:
        out.append(("stop", f"`{paths.UPDATE_LIST.name}` is missing. Run "
                            "`python fts_update_list.py`."))
        return out

    if _older(paths.CACHE, paths.EXTRACT):
        out.append((
            "stop",
            f"`{paths.EXTRACT.name}` is newer than `{paths.CACHE.name}` "
            f"({paths.stamp(paths.EXTRACT)} against "
            f"{paths.stamp(paths.CACHE)}). A new extract has landed and the "
            "analysis has not been re-run against it, so everything below "
            "would describe the previous one.\n\n"
            # NAMING THE COMMAND, since 2026-09-02. This said "Re-run the
            # pipeline" and stopped, while the missing-update-list message two
            # branches up has always named `python fts_update_list.py`. The
            # reader of this screen is the one least likely to know: it fires
            # when an extract has been put in place by hand, which is not the
            # route the analysis repo documents.
            #
            # BOTH COMMANDS, because which one is right depends on how the file
            # got here and this side cannot tell. new_extract.py looks for
            # fts_new.xlsx; once somebody has renamed it to fts.xlsx that route
            # is closed and run_all.py is the one that works.
            "In the analysis folder, `python new_extract.py` if the export is "
            "still sitting there as `fts_new.xlsx`, or `python run_all.py` if "
            "it has already been renamed into place."))

    if _older(paths.UPDATE_LIST, paths.CACHE):
        out.append((
            "stop",
            f"`{paths.UPDATE_LIST.name}` is older than `{paths.CACHE.name}` "
            f"({paths.stamp(paths.UPDATE_LIST)} against "
            f"{paths.stamp(paths.CACHE)}). The update list predates the data "
            "it claims to describe. Re-run every operation, then "
            "`python fts_update_list.py`."))

    out += _window_problems()
    out += _window_length_problem()

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
    """Render the problems and halt on anything fatal. Call it on every page.

    It also brings the pipeline's code up to date first (pipeline.refresh),
    so a page never renders under rules older than the files on disk - the
    cache keys do the same for every cached figure, see paths.cache_key.
    """
    from . import pipeline
    pipeline.refresh()
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
