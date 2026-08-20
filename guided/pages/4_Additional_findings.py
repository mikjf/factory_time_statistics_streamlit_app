"""Real findings, additional to the standards work.

On their own page on purpose. Everything here is hours the schedule reserved and
the costing charged for work with no evidence it was performed. Mixed into the
review queue it would either be ignored or keyed in, and both are wrong.
"""

import pathlib
import sys

import streamlit as st

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import data, freshness, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="Additional findings · H0",
                   page_icon=":material/flag:", layout="wide")
ui.inject()
st.title("Additional findings")
ui.verdict_banner(st, text.NOT_A_STANDARD, "caution",
                  text.NOT_A_STANDARDS_CHANGE)
freshness.guard()

S = data.SEQ
tok = data.update_list("07_TokenBookings")
skip = data.setup_book("03_SkipRate") if data.has_setup() else None
gap = data.load_book("04_MultiLoadGap") if data.has_load() else None

with st.sidebar:
    # ui.kv, not three st.metric calls. The metrics gave 36px numbers to a
    # column whose job is provenance, and an "### " heading put an 18px h3 above
    # them - four type sizes in one rail, which is exactly what side_title and
    # kv were built to end. Overview and Methodology already read this way.
    #
    # The labels are the tab names, so the rail and the tab bar name the same
    # three findings in the same words.
    rows = [("Work orders with micro duration",
             ui.hrs(tok.STANDARD_CHARGED.sum()))]
    if skip is not None:
        rows.append(("Setups charged but not performed",
                     ui.hrs(skip.STANDARD_CHARGED_SKIPPED.sum())))
    if gap is not None:
        rows.append(("Runs with multiple loads",
                     ui.hrs(gap.OVER_RESERVED_HOURS.sum())))
    ui.kv(st, "What this costs", rows)

# ---- the selector, in the rail ---------------------------------------------
# A RADIO, NOT TABS, and the reason is the filters rather than the findings.
# Streamlit renders every tab on every run, so filters moved to this rail would
# all show at once - "Run type", which only means anything for setups, sitting
# above a table of micro-duration tickets. A radio renders one finding, so the
# controls under it can only ever be the ones that apply to what is on screen.
#
# It also makes this page work the way the rest of the tool does: the rail is
# what to look at, the body is what was found. Inspect, Review queue and By part
# all read that way already; this page was the last one that did not.
#
# An analysis whose workbook was not produced is left out of the options rather
# than offered and then apologised for.
MICRO = "Work orders with micro duration"
SETUPS = "Setups charged but not performed"
LOADS = "Runs with multiple loads"

with st.sidebar:
    st.divider()
    ui.side_title(st, "What to look at")
    choices = [MICRO] + ([SETUPS] if skip is not None else [])         + ([LOADS] if gap is not None else [])
    choice = st.radio("Finding", choices, label_visibility="collapsed")

    # The filters for the chosen finding, and nothing else. "Runs with multiple
    # loads" is four rows of one column each and carries none - a filter over
    # four rows is furniture.
    fam = only = rt = None
    if choice == MICRO:
        fam = st.multiselect("Family", sorted(tok.FAMILY.unique()),
                             placeholder="all families")
        only = st.toggle("Only steps left untestable")
    elif choice == SETUPS:
        fam = st.multiselect("Family", sorted(skip.FAMILY.unique()),
                             placeholder="all families", key="skipfam")
        rt = st.multiselect("Run type", sorted(skip.RUN_TYPE.unique()),
                            placeholder="both")

# The title and the banner above never change - they are true of all three -
# so the section heading is what says which finding is on screen.
st.subheader(choice)

if choice == MICRO:
    # THE NUMBERS FIRST, then what they mean. The prose explains why the
    # finding exists and runs to a paragraph or three, and a reader who
    # came for the size of it had to scroll past all of it to reach three
    # figures. Heading, figures, explanation, evidence - the order Inspect
    # already uses.
    c = st.columns(3)
    c[0].metric("Work orders", ui.num(tok.WO_TOKEN.sum()))
    c[1].metric("Standard charged", ui.hrs(tok.STANDARD_CHARGED.sum()))
    c[2].metric("Steps left untestable",
                ui.num(tok.BELOW_FLOOR_AFTER.sum()))
    st.markdown(f"""
A few thousand labour tickets carry a flat hundredth of an hour whatever the
quantity — one piece or five hundred, the same 0.01 h. That is a ticket closed
to move the order along, not a measurement, so anything at or under
**{pipeline.TOKEN_HOURS} h** is dropped before testing.

They are not merely noise. Where they are the majority of a pool they *become*
its centre, and the outlier filter then discards the real work orders as the
exceptions — on one step 60 of 63 work orders were tokens, and a confident
suggestion ended up resting on three real jobs.

**`STANDARD_CHARGED` is the number to look at.** It is what those work orders
carried: hours the schedule reserved and the costing charged against jobs with
no evidence they were performed. `BELOW_FLOOR_AFTER` marks the steps where
dropping them left too little to judge the standard at all — those standards may
be badly wrong and this analysis will never say so.
""")
    d = tok[tok.FAMILY.isin(fam)] if fam else tok
    if only:
        d = d[d.BELOW_FLOOR_AFTER]
    # TOKEN_RATE is deliberately absent from the Styler: it drives a
    # ProgressColumn, which needs the raw number to size its bar.
    st.dataframe(ui.swiss_grid(d, {"PARTS": ",.0f", "WO_ALL": ",.0f",
                                   "WO_TOKEN": ",.0f", "WO_REAL": ",.0f",
                                   "PIECES": ",.0f", "HOURS_BOOKED": ",.2f",
                                   "STANDARD_CHARGED": ",.1f"}),
                 hide_index=True, width="stretch", height=380,
                 column_config={
                     S: st.column_config.NumberColumn("SEQ", format="%d"),
                     "TOKEN_RATE": st.column_config.ProgressColumn(
                         "TOKEN RATE", min_value=0, max_value=1,
                         format="%.0f%%"),
                 })
    st.download_button("Download as CSV", d.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_micro_duration.csv", mime="text/csv",
                       icon=":material/download:", key="dl_tok")

elif choice == SETUPS:
    c = st.columns(3)
    c[0].metric("Steps", ui.num(len(skip)))
    c[1].metric("Charged for setups never performed",
                ui.hrs(skip.STANDARD_CHARGED_SKIPPED.sum()))
    c[2].metric("Work orders skipped", ui.num(skip.WO_SKIPPED.sum()))
    st.markdown(f"""
When several work orders of one family run back to back on one machine, only the
first needs a full setup. That is normal and correct — but the ERP charges
`SETUP_HRS` on **every** work order whether a setup happened or not, so a family
skipping half its setups reserves roughly double the setup time it consumes.

A setup booked at or under **{pipeline.SKIP_CUT} h** did not happen. The booked
distribution has a clean gap there — the 20th percentile is 0.010 and the 25th
is 0.070 — so where in that gap the cut sits changes nothing.

This is the only view covering **both** run types. Skipping is a counting
question, so it needs no test and no minimum sample: HRS/LOAD setup carries a
standard on one operation only, with three performed setups in the whole year
against a floor of {pipeline.SETUP_MIN}. Untestable, but not unreportable.
""")

    # 03_SkipRate is filtered to pools with SETUP_MIN or more work orders,
    # so the figure above is SHORT of the true total - and the README and
    # the workbook both quote the unfiltered one. Two numbers for the same
    # thing in documents somebody will compare, with nothing on screen
    # saying why they differ.
    #
    # The unfiltered total comes from data.skip_hours_total(), which reads
    # the 00_Summary row the workbook and the README already quote, so the
    # three cannot drift apart. The banner at the top of this page quotes
    # the same figure. Printed only when the two actually differ.
    _all = data.skip_hours_total()
    _shown = float(skip.STANDARD_CHARGED_SKIPPED.sum())
    if abs(_all - _shown) >= 0.5:
        st.caption(
            f"The table below lists only steps with "
            f"{pipeline.SETUP_MIN}+ work orders, so the figure "
            f"above is short of the whole picture. Across every step, "
            f"including those too small to list, "
            f"**{ui.hrs(_all)}** was charged for setups never "
            f"performed — {ui.hrs(_all - _shown)} of it in steps that "
            f"do not appear here.")
    d2 = skip[skip.FAMILY.isin(fam)] if fam else skip
    if rt:
        d2 = d2[d2.RUN_TYPE.isin(rt)]
    st.dataframe(ui.swiss_grid(
        d2, {"PARTS": ",.0f", "WO_ALL": ",.0f", "WO_SKIPPED": ",.0f",
             "WO_REAL": ",.0f", "SETUP_HRS_CURRENT": ",.3f",
             "STANDARD_CHARGED_SKIPPED": ",.1f",
             "STANDARD_CHARGED_ALL_WO": ",.1f"}),
                 hide_index=True, width="stretch", height=380,
                 column_config={
                     S: st.column_config.NumberColumn("SEQ", format="%d"),
                     "SKIP_RATE": st.column_config.ProgressColumn(
                         "SKIP RATE", min_value=0, max_value=1,
                         format="%.0f%%"),
                 })
    st.download_button("Download as CSV",
                       d2.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_setups_not_performed.csv", mime="text/csv",
                       icon=":material/download:", key="dl_skip")

else:
    st.metric("Reserved and not used",
              ui.hrs(gap.OVER_RESERVED_HOURS.sum()))
    st.markdown("""
`HRS/LOAD` charges `CEILING(quantity ÷ load size) × RUN`. A job of 1,048 pieces
against a load size of 500 is charged three full machine cycles whatever the
last basket holds.

The model assumes the second basket costs the same as the first, and it does
not. Over the fiscal year single-load work orders run at a ratio of about 0.96 —
the standard is roughly right — while multi-load work orders run at about 0.57,
charged nearly double what they take.

No single multiplier fixes both. Fitting hours against load count puts the
marginal load anywhere from 0% to 156% of `RUN` depending on the operation, so
one corrected `RUN` cannot serve both regimes: tighten it to the pooled figure
and the single-load jobs that were already right get squeezed. Multi-load work
orders are therefore **excluded from the test and reported here**.

`MARGINAL_LOAD_B` is what a second load actually costs in hours;
`MARGINAL_AS_PCT_OF_RUN` compares that with what the standard charges for one.
""")
    st.dataframe(ui.swiss_grid(
        gap, {"WORK_ORDERS": ",.0f", "STEPS": ",.0f", "PARTS": ",.0f",
              "HOURS_MASTER": ",.0f", "HOURS_WORKED": ",.0f",
              "OVER_RESERVED_HOURS": ",.0f", "RATIO": ",.3f"}),
        hide_index=True, width="stretch")
    st.download_button("Download as CSV",
                       gap.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_multiple_loads.csv", mime="text/csv",
                       icon=":material/download:", key="dl_gap")
