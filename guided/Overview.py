"""H0 master-time review - guided version. Start here.

    streamlit run streamlit_app/guided/Overview.py --server.address localhost

Keep the address flag. Streamlit binds every interface by default, and this
shows part numbers, customer family names, work order numbers and real job
durations with no authentication in front of them.

This version differs from streamlit_app/Overview.py in one idea: the six rules
that decide whether a standard changes are the spine of the analysis, so they
are the spine of the interface too. They sit in the left rail, colour-coded,
wherever a unit is selected.

Reads the workbooks and the parquet. Writes nothing, anywhere.
"""

import pathlib
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from h0app import (charts, data, evidence, freshness, paths,  # noqa: E402
                   pipeline, text, ui)

st.set_page_config(page_title="H0 master-time review",
                   page_icon=":material/timer:", layout="wide")
ui.inject()

# ---- sidebar ----------------------------------------------------------------
with st.sidebar:
    # The six rules used to be listed here too. They belong on Inspect, where
    # they fill in with a unit's own figures and mean something; repeated on the
    # landing page as six static ticks they were a legend for a verdict nobody
    # had asked for yet.
    st.caption("**Statistical analysis built from**")
    for p in (paths.EXTRACT, paths.CACHE, paths.UPDATE_LIST, paths.SETUP,
              paths.LOAD):
        st.caption(f"`{p.name}` · {paths.stamp(p)}")

# ---- header -----------------------------------------------------------------
st.title("Overview")
st.caption("Where the master standards disagree with what the shop floor "
           "actually books (real job durations), from FY26 onwards.")

freshness.guard()

acts = data.actions()
total = data.update_list("00_Summary")
total = total[total.OPERATION == "TOTAL"].iloc[0]
edits = data.edits()

n_pcs = int(((acts.TARGET == "RUN") & (acts.RUN_TYPE == "PCS/HR")).sum())
n_hrl = int(((acts.TARGET == "RUN") & (acts.RUN_TYPE == "HRS/LOAD")).sum())
n_set = int((acts.TARGET == "SETUP_HRS").sum())

c = st.columns(4)
c[0].metric("Standards to review", ui.num(len(acts)),
            help=f"{n_pcs} run PCS/HR, {n_hrl} run HRS/LOAD, {n_set} setup.")
c[1].metric("Distinct parts affected", ui.num(edits.PART_ID.nunique()),
            help="Parts have multiple operations and each one could need an "
                 "edit.")
c[2].metric("Operations rows to edit", ui.num(len(edits)),
            help="Higher than distinct parts affected as each part has "
                 "multiple operations.")
c[3].metric("Absolute misstated hours",
            ui.hrs(total.HOURS_DELTA_ABSOLUTE),
            # "per standard" pins the absolute to the right level. Without it,
            # "absolute hours delta" reads as the absolute of each work order's
            # delta, which is a different and much larger number - taken over
            # every in-scope work order it comes to 24,622 h against the 10,966
            # here - because it counts ordinary job-to-job variation as
            # misstatement. Within one standard the deltas cancel; across
            # standards they do not.
            help="Total absolute hours delta (actual − master) per standard, "
                 "of standards to review only.")

st.divider()

# ---- the four panels --------------------------------------------------------
# A 2x2, each panel titled in its own right rather than under one section
# heading: they answer four separate questions and a reader arrives at whichever
# one is theirs.
#
# The top-left table is the only panel covering every kind of standard, and it
# says so by naming them; the other three are RUN ONLY and say so first thing.
# Setup is judged on a different population against a different floor, so a
# ranking that mixes it in cannot be compared against run hours - and the
# "% of master" panel does exactly that comparison.
#
# "By family" sits beside "Most wrong family" on the bottom row so the two
# family cuts read together: same entities, one ranked by size, one by degree.
#
# Net appears once, in that table, beside its own gross where it cannot be
# misread. It is absent from all three charts: per family it misleads at a
# glance - the largest family nets to roughly a third of its gross, so a small
# bar beside a large one invites "so that one is fine".
g1, g2 = st.columns(2)

with g1:
    st.subheader("Hours by labor ticket type and run type")
    st.caption("What is actually being edited, and how much of the "
               "misstatement cancels out within each.")
    kind = np.where(acts.TARGET == "SETUP_HRS", "Setup",
                    "Run " + acts.RUN_TYPE)
    by_kind = (acts.assign(KIND=kind).groupby("KIND")
               .agg(ACTIONS=("HOURS_DELTA", "size"),
                    ABS_H=("HOURS_DELTA", lambda s: s.abs().sum()),
                    NET_H=("HOURS_DELTA", "sum"))
               .reindex(["Run PCS/HR", "Run HRS/LOAD", "Setup"])
               .reset_index())
    by_kind = pd.concat([by_kind, pd.DataFrame([{
        "KIND": "Total", "ACTIONS": len(acts),
        "ABS_H": acts.HOURS_DELTA.abs().sum(),
        "NET_H": acts.HOURS_DELTA.sum()}])], ignore_index=True)
    # st.table, not st.dataframe: this is a four-row summary that nobody sorts,
    # and st.table renders HTML, so the column headers can be right-aligned over
    # their numbers. st.dataframe draws headers to a canvas where neither CSS
    # nor column_config can move them. The Styler still supplies the apostrophe.
    st.table(
        ui.swiss_grid(
            by_kind.rename(columns={
                "KIND": " ", "ACTIONS": "Actions",
                "ABS_H": "Absolute misstated (h)", "NET_H": "Net (h)"}),
            {"Actions": ",.0f", "Absolute misstated (h)": ",.0f",
             "Net (h)": "+,.0f"}).hide(axis="index"))
    # Rewritten from a one-liner that named the three ERP fields and said the
    # correction "divides" or "multiplies" without saying what by. The rows of
    # the table above are exactly the three cases, so this is the place to say
    # it - and it is the single most costly thing to get backwards.
    st.caption(
        "**The three rows are corrected in opposite directions.** PCS/HR holds "
        "a **rate** — pieces per hour — so a job running 25% longer needs a "
        "*lower* number (`RUN_MASTER`, divided by the ratio). Setup and "
        "HRS/LOAD hold a **duration** in hours, so the same job needs a "
        "*higher* one (`SETUP_HRS` and `RUN`, multiplied by it). Reversed, the "
        "figures still look plausible but wrong.")

with g2:
    # RUN ONLY, like the two panels below it. Setup is judged on a different
    # population against a different floor, so folding it into a ranking that
    # gets compared against run hours quietly changes what the ranking means.
    op_run = data.run_gross_by_operation()
    share = 100 * op_run.nlargest(10, "GROSS_HOURS").GROSS_HOURS.sum() \
        / op_run.GROSS_HOURS.sum()
    st.subheader("By operation")
    st.caption(f"Run only. Which process. The top ten carry {share:.0f}% of "
               f"every misstated run hour.")
    st.altair_chart(charts.operation_bar(op_run), width="stretch")

g3, g4 = st.columns(2)

with g3:
    st.subheader("By family")
    # ADV / ANDV are expanded here because this is the one caption that already
    # tells the reader the two rows exist. Abbreviating them on the axis bought
    # space and cost meaning; nothing else on the page maps them.
    st.caption("Run only. Which product line. Semi-finished (ANDV) and "
               "finished (ADV) are separate rows (different jobs).")
    st.altair_chart(charts.family_misstated_bar(data.run_gross_by_family()),
                    width="stretch")

with g4:
    wrong = data.most_wrong_families(charts.PCT_FLOOR_H)
    # The bar uses the WIDE denominator - all the family's master run hours,
    # including steps that were tested and held or were never testable. The
    # narrow one, over just the steps being changed, rides along in the tooltip
    # rather than getting its own bar: it is always the larger number, it
    # reorders the list, and it is computed over exactly the steps that failed,
    # which is close enough to circular that it should not lead.
    wrong = wrong.merge(
        evidence.flagged_master_hours(zip(wrong.FAMILY, wrong.PART_TYPE)),
        on=["FAMILY", "PART_TYPE"], how="left")
    wrong["PCT_FLAGGED"] = 100 * wrong.GROSS_HOURS / wrong.FLAGGED_MASTER_H

    st.subheader("Most wrong families")
    # The caption IS the legend: each question is written in its own series'
    # colour, so there is nothing to map from a swatch to a bar. Not st.caption
    # - that container's opacity would wash both blues to 60% and pull them
    # toward each other. See ui.caption_line.
    ui.caption_line(st, (
        "Run only. "
        + ui.tinted("How much of this family's master time is wrong?",
                    charts.MISSTATED) + " "
        + ui.tinted("How bad are the ones we flagged to change?",
                    charts.MISSTATED_LIGHT)))
    st.altair_chart(charts.most_wrong_bar(wrong), width="stretch")

st.info(
    "**Both directions count.** A master that over-allows by 10 h and one that "
    "under-allows by 10 h are two problems, not zero — so totals add the size "
    "of each error, never cancel them.",
    icon=":material/functions:")

st.divider()

# ---- where to go ------------------------------------------------------------
st.subheader("Where to go")
n1, n2, n3 = st.columns(3)
with n1:
    with st.container(border=True):
        st.markdown("#### :material/checklist: Review queue")
        st.caption("Every standard proposed for change. Filter to your family "
                   "or your operation, see what it is worth, pick one.")
        st.page_link("pages/1_Review_queue.py", label="Open the queue",
                     icon=":material/arrow_forward:")
with n2:
    with st.container(border=True):
        st.markdown("#### :material/query_stats: Inspect")
        st.caption("One recommendation opened up: the six rules with real "
                   "figures, every work order behind it, and where each sits "
                   "against the standard. **Use this when you disagree.**")
        st.page_link("pages/2_Inspect.py", label="Inspect a unit",
                     icon=":material/arrow_forward:")
with n3:
    with st.container(border=True):
        st.markdown("#### :material/qr_code: By part")
        st.caption("Everything proposed for one part — and every step of it "
                   "that was examined and left alone, with the reason.")
        st.page_link("pages/3_By_part.py", label="Look a part up",
                     icon=":material/arrow_forward:")

n4, n5, n6 = st.columns(3)
with n4:
    with st.container(border=True):
        st.markdown("#### :material/flag: Not standards changes")
        st.caption("Hours the schedule reserved and the costing charged for "
                   "work with no evidence it happened. Real, but a booking and "
                   "routing question — different people.")
        st.page_link("pages/4_Not_standards.py", label="See the findings",
                     icon=":material/arrow_forward:")
with n5:
    with st.container(border=True):
        st.markdown("#### :material/school: How it works")
        st.caption("The method: the six rules, part versus family, the two "
                   "directions of correction, and what this cannot tell you.")
        st.page_link("pages/5_How_it_works.py", label="Read the method",
                     icon=":material/arrow_forward:")
with n6:
    with st.container(border=True):
        st.markdown("#### :material/database: Dataset")
        st.caption("What the numbers are computed over: the extract, the "
                   "period it covers, and how much of it survives to become a "
                   "decision.")
        st.page_link("pages/6_Dataset.py", label="See the data",
                     icon=":material/arrow_forward:")

st.divider()
st.caption("Read-only. This tool opens no file for writing anywhere in the "
           "project; downloads go to your browser.")
