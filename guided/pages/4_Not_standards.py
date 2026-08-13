"""Real findings that are not standards changes.

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

st.set_page_config(page_title="Not standards changes · H0",
                   page_icon=":material/flag:", layout="wide")
ui.inject()
st.title("Not standards changes")
ui.verdict_banner(st, "Nothing on this page is a standard to key in", "caution",
                  text.NOT_A_STANDARDS_CHANGE)
freshness.guard()

S = data.SEQ
tok = data.update_list("07_TokenBookings")
skip = data.setup_book("03_SkipRate") if data.has_setup() else None
gap = data.load_book("04_MultiLoadGap") if data.has_load() else None

with st.sidebar:
    st.markdown("### What this costs")
    st.metric("Charged for work with no duration recorded",
              ui.hrs(tok.STANDARD_CHARGED.sum()))
    if skip is not None:
        st.metric("Charged for setups never performed",
                  ui.hrs(skip.STANDARD_CHARGED_SKIPPED.sum()))
    if gap is not None:
        st.metric("Capacity reserved and not used",
                  ui.hrs(gap.OVER_RESERVED_HOURS.sum()))
    st.divider()
    st.caption("These go to routing, scheduling and booking discipline — not "
               "to whoever keys standards into the ERP.")

t1, t2, t3 = st.tabs(["Work orders closed without a duration",
                      "Setups charged but not performed",
                      "Multi-load capacity gap"])

with t1:
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
    c = st.columns(3)
    c[0].metric("Work orders", ui.num(tok.WO_TOKEN.sum()))
    c[1].metric("Standard charged", ui.hrs(tok.STANDARD_CHARGED.sum()))
    c[2].metric("Steps left untestable",
                ui.num(tok.BELOW_FLOOR_AFTER.sum()))
    f1, f2 = st.columns([2, 1])
    fam = f1.multiselect("Family", sorted(tok.FAMILY.unique()),
                         placeholder="all families")
    only = f2.toggle("Only steps left untestable")
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
                       file_name="h0_token_bookings.csv", mime="text/csv",
                       icon=":material/download:", key="dl_tok")

with t2:
    if skip is None:
        st.info("The setup analysis has not been run.", icon=":material/info:")
    else:
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
        c = st.columns(3)
        c[0].metric("Steps", ui.num(len(skip)))
        c[1].metric("Charged for setups never performed",
                    ui.hrs(skip.STANDARD_CHARGED_SKIPPED.sum()))
        c[2].metric("Work orders skipped", ui.num(skip.WO_SKIPPED.sum()))
        g1, g2 = st.columns([2, 1])
        fam2 = g1.multiselect("Family", sorted(skip.FAMILY.unique()),
                              placeholder="all families", key="skipfam")
        rt = g2.multiselect("Run type", sorted(skip.RUN_TYPE.unique()),
                            placeholder="both")
        d2 = skip[skip.FAMILY.isin(fam2)] if fam2 else skip
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
                           file_name="h0_skip_rate.csv", mime="text/csv",
                           icon=":material/download:", key="dl_skip")

with t3:
    if gap is None:
        st.info("The HRS/LOAD analysis has not been run.",
                icon=":material/info:")
    else:
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
        st.metric("Reserved and not used",
                  ui.hrs(gap.OVER_RESERVED_HOURS.sum()))
        st.dataframe(ui.swiss_grid(
            gap, {"WORK_ORDERS": ",.0f", "STEPS": ",.0f", "PARTS": ",.0f",
                  "HOURS_MASTER": ",.0f", "HOURS_WORKED": ",.0f",
                  "OVER_RESERVED_HOURS": ",.0f", "RATIO": ",.3f"}),
            hide_index=True, width="stretch")
        st.download_button("Download as CSV",
                           gap.to_csv(index=False).encode("utf-8"),
                           file_name="h0_multi_load_gap.csv", mime="text/csv",
                           icon=":material/download:", key="dl_gap")
