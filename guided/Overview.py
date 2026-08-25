"""H0 master-time review. Start here.

    streamlit run streamlit_app/guided/Overview.py --server.address localhost

Keep the address flag. Streamlit binds every interface by default, and this
shows part numbers, customer family names, work order numbers and real job
durations with no authentication in front of them.

One idea runs through the whole app: the six rules that decide whether a
standard changes are the spine of the analysis, so they are the spine of the
interface too - named on Methodology, applied with a unit's own figures on
Inspect, and answered for on By part.

An earlier flat version sat beside this one for comparison while the design
settled. It was never published and has been deleted; this is the app.

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
    # had asked for yet. The thresholds they fire on are absent for the same
    # reason - on Methodology they sit above the rules themselves, here they
    # would be five numbers with nothing to attach to.
    #
    # Same block as Methodology, same helper. "Is this current?" is the first
    # question anybody has on a landing page, and the five filenames it replaced
    # answered it in the language of the folder rather than of the data.
    #
    # "Key dates" rather than "Analysis built from": all three rows ARE dates,
    # and a title naming the time span would have been wrong about the third -
    # a run timestamp is not part of the window the data covers.
    _facts = data.extract_facts()
    ui.kv(st, "Key dates", [
        ("First labour ticket", f"{_facts['first']:%d %b %Y}"),
        ("Last labour ticket", f"{_facts['last']:%d %b %Y}"),
        ("Last full analysis run", paths.stamp(paths.UPDATE_LIST)),
    ])

# ---- header -----------------------------------------------------------------
st.title("Overview")
st.caption(f"Where the master standards disagree with what the shop floor "
           f"actually books (real job durations), from {pipeline.FY_LABEL} "
           f"onwards.")

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
            # SHARED WITH THE REVIEW QUEUE, which carries this tile too and had
            # drifted to a second wording of the same fact. The two reach 2'337
            # by different routes - this counts rows in the execution sheets,
            # that sums N_PARTS over 01_Actions - and agree.
            help=text.ROWS_TO_EDIT_HELP)
c[3].metric("Absolute misstated hours",
            ui.hrs(total.HOURS_DELTA_ABSOLUTE),
            # SHARED WITH THE REVIEW QUEUE, which shows the same figure under
            # the same label one click away. text.ABSOLUTE_MISSTATED_HELP
            # carries the wording and the reasoning behind every clause of it.
            help=text.ABSOLUTE_MISSTATED_HELP)

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
    st.subheader("Hours by labour ticket type and run type")
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
        "*lower* number (`RUN`, divided by the ratio). Setup and "
        "HRS/LOAD hold a **duration** in hours, so the same job needs a "
        "*higher* one (`SETUP_HRS` and the same `RUN`, multiplied by it). "
        "Reversed, the figures still look plausible but wrong.")

with g2:
    # RUN ONLY, like the two panels below it. Setup is judged on a different
    # population against a different floor, so folding it into a ranking that
    # gets compared against run hours quietly changes what the ranking means.
    # PCS/HR + HRS/LOAD merged in for the tooltip only - S SABBIARE mixes both
    # despite sitting outside the top ten, so the split is shown on every bar
    # rather than assumed single-valued. See data._by_type.
    op_run = data.run_gross_by_operation().merge(
        data.run_gross_by_operation_by_type(), on="OPERATION", how="left")
    share = 100 * op_run.nlargest(10, "GROSS_HOURS").GROSS_HOURS.sum() \
        / op_run.GROSS_HOURS.sum()
    st.subheader("By operation")
    st.caption(f"`Run PCS/HR` and `Run HRS/LOAD` only. Which process. The "
               f"top ten carry {share:.0f}% of every misstated run hour.")
    st.altair_chart(charts.operation_bar(op_run), width="stretch")

g3, g4 = st.columns(2)

with g3:
    st.subheader("By family")
    # ADV / ANDV are expanded here because this is the one caption that already
    # tells the reader the two rows exist. Abbreviating them on the axis bought
    # space and cost meaning; nothing else on the page maps them.
    st.caption("`Run PCS/HR` and `Run HRS/LOAD` only. Which product line. "
               "Semi-finished (ANDV) and finished (ADV) are separate.")
    fam_run = data.run_gross_by_family().merge(
        data.run_gross_by_family_by_type(), on=["FAMILY", "PART_TYPE"],
        how="left")
    st.altair_chart(charts.family_misstated_bar(fam_run), width="stretch")

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
        "`Run PCS/HR` and `Run HRS/LOAD` only. "
        + ui.tinted("How much of this family's time is wrong?",
                    charts.MISSTATED) + " "
        + ui.tinted("How bad are the ones flagged to change?",
                    charts.MISSTATED_LIGHT)))
    st.altair_chart(charts.most_wrong_bar(wrong), width="stretch")

# No made-up figure. "10 h" was an illustration standing in a row of real ones,
# and the point does not need a number: it is about the sign, not the size.
st.info(
    "**Both directions count.** A master that over-allows and one that "
    "under-allows by the same number of hours are two problems, not zero — so "
    "totals add the size of each error, never cancel them.",
    icon=":material/functions:")

st.divider()
st.caption("Read-only. This tool opens no file for writing anywhere in the "
           "project. Downloads go to your browser.")
