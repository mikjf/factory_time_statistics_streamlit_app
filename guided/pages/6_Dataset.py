"""What the analysis is computed over: the extract, its reach, and how much of
it survives to become a decision.

Split out from the Overview and from How it works so the two questions stop
sharing a page. This one answers "what data is this?"; How it works answers
"how is a conclusion drawn from it?". The funnel lives here because it is a
statement about the data - most of what was measured cannot support a verdict -
rather than about the method.
"""

import pathlib
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from h0app import data, freshness, paths, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="Dataset · H0", page_icon=":material/database:",
                   layout="wide")
ui.inject()
st.title("Dataset")
st.caption("Every labour ticket the ERP recorded, joined to the master routing "
           "in force for it. This page is what the numbers are computed over.")
freshness.guard()

facts = data.extract_facts()
ops = data.operation_summaries()
acts = data.actions()

with st.sidebar:
    st.caption("**Statistical analysis built from**")
    for p in (paths.EXTRACT, paths.CACHE, paths.UPDATE_LIST, paths.SETUP,
              paths.LOAD):
        st.caption(f"`{p.name}` · {paths.stamp(p)}")
    st.divider()
    st.caption("These timestamps are not decoration — every page checks them "
               "for order before rendering, and refuses to show results built "
               "from a superseded extract.")

# ---- what is in it ----------------------------------------------------------
c = st.columns(5)
# NOT "labour tickets": one row is work order x routing step x Run/Setup x
# resource, and the query sums the tickets inside each one. There are more
# tickets than rows and the extract cannot say how many - the aggregation has
# already happened by the time it reaches here.
c[0].metric("Labour booking lines", ui.num(facts["rows"]),
            help="One row per work order, routing step, run or setup, and "
                 "resource. Labour tickets are summed within each.")
c[1].metric("Work orders", ui.num(facts["work_orders"]))
c[2].metric("Parts", ui.num(facts["parts"]))
c[3].metric("Families", ui.num(facts["families"]))
c[4].metric("Operations", ui.num(facts["operations"]))

# The window is stated by its dates rather than called "a year": bookings run
# from the start of the fiscal year to the day the extract was taken, which is
# not twelve months, and every hours total on the site is bounded by it.
st.caption(
    f"Fiscal year from {pipeline.FY_START}. Bookings in this extract run "
    f"{facts['first']:%d %b %Y} to {facts['last']:%d %b %Y}. Every hours "
    f"figure in this tool is what has already been registered in this time "
    f"window.")

st.divider()

# ---- what is in scope -------------------------------------------------------
# Directly above the funnel, because these exclusions are what its first two
# bars are counting. Moved here from the method page: every row is a statement
# about which labour tickets exist in the data, not about how they are judged.
st.subheader("What is deliberately left out")
st.caption("Applied before anything is measured. Each of these removes rows "
           "that cannot support a conclusion about a master standard.")
st.markdown(text.WHAT_IS_EXCLUDED)

st.divider()

# ---- the funnel -------------------------------------------------------------
left, right = st.columns([1.15, 1])

with left:
    st.subheader("From labour tickets to decisions")
    st.caption("Each stage removes what cannot support a conclusion. Most of "
               "what was measured never becomes an action — that is the design "
               "working, not something missing.")
    # Two sections, because the unit changes and there is no conversion between
    # them: one part-and-step is however many tickets happened to run it. Drawn
    # on a single scale, the drop from 19,447 tickets to 8,783 part-steps read
    # as ten thousand work orders being thrown away.
    ui.funnel(st, [
        ("What the shop floor booked", "labour tickets", [
            ("In scope", int(ops.WORK_ORDERS.sum()),
             "current fiscal year · step still in the master routing · not "
             "rework"),
            ("With a duration actually recorded",
             int(ops.WORK_ORDERS.sum() - ops.TOKENS.sum()),
             f"{ui.num(ops.TOKENS.sum())} were closed at ≤ "
             f"{pipeline.TOKEN_HOURS} h — a ticket closed, not a job timed"),
        ]),
        ("What a master is judged on", "part × routing step", [
            ("Combinations examined", int(ops.UNITS.sum()),
             "the level a master actually lives at — those tickets, grouped"),
            (f"Enough evidence to judge ({pipeline.MIN_WO}+ work orders)",
             int(ops.TESTABLE.sum()),
             "below this no test can reach significance, whatever the evidence"),
            ("Genuinely different from the master",
             int(ops.SIGNIFICANT.sum()),
             "and not just different by chance"),
            ("Big enough to be worth changing", int(ops.MATERIAL.sum()),
             f"at least {pipeline.MIN_EFFECT:.0%} off and "
             f"{pipeline.MIN_HOURS_IMPACT:g} h a year"),
        ]),
    ])
    st.caption(
        f"Those {int(ops.MATERIAL.sum())} are the PCS/HR run analysis. Setup "
        f"and HRS/LOAD run through the same six rules separately and add the "
        f"rest, giving **{len(acts)} decisions** in total.")

with right:
    st.subheader("Why the two halves cannot be added")
    st.markdown(f"""
The first two bars count **labour tickets** — one row per person, per work
order, per step. The last four count **part × routing step combinations**, which
is the level a master standard actually lives at.

There is no conversion between them. One part-and-step is however many tickets
happened to run it this year: `S SEGARE` at sequence 1200 for one family is a
single master value covering **{int(ops.WORK_ORDERS.sum() / max(ops.UNITS.sum(), 1))}
tickets on average**.

So the drop from {ui.num(ops.WORK_ORDERS.sum() - ops.TOKENS.sum())} to
{ui.num(ops.UNITS.sum())} is **not** discarded work. It is the same evidence,
regrouped from *what was booked* into *what can be judged*.

The real narrowing happens after that: of {ui.num(ops.UNITS.sum())} combinations,
only {ui.num(ops.TESTABLE.sum())} carry enough work orders to test at all.
""")

st.divider()

# ---- coverage ---------------------------------------------------------------
st.subheader("Every operation examined, and what came out of it")
st.caption("Operations with zero actions are listed on purpose. 'Tested and it "
           "holds' and 'nothing was testable' are different statements, and "
           "without both on the page they look identical.")

show = ops[["OPERATION", "WORK_ORDERS", "TOKENS", "UNITS", "TESTABLE",
            "SIGNIFICANT", "MATERIAL", "NOTHING_TESTABLE"]]
st.dataframe(
    ui.swiss_grid(show, {"WORK_ORDERS": ",.0f", "TOKENS": ",.0f",
                         "UNITS": ",.0f", "TESTABLE": ",.0f",
                         "SIGNIFICANT": ",.0f", "MATERIAL": ",.0f"}),
    hide_index=True, width="stretch", height=460,
    column_config={
        "OPERATION": st.column_config.TextColumn("Operation", width="medium"),
        "WORK_ORDERS": st.column_config.NumberColumn("Work orders"),
        "TOKENS": st.column_config.NumberColumn(
            "Token bookings",
            help=f"Closed at ≤ {pipeline.TOKEN_HOURS} h — a ticket closed "
                 f"rather than a job timed. Dropped before testing."),
        "UNITS": st.column_config.NumberColumn("Part × step"),
        "TESTABLE": st.column_config.NumberColumn(
            f"{pipeline.MIN_WO}+ work orders",
            help="Below this no test can reach significance."),
        "SIGNIFICANT": st.column_config.NumberColumn("Different"),
        "MATERIAL": st.column_config.NumberColumn("Actions"),
        "NOTHING_TESTABLE": st.column_config.CheckboxColumn(
            "Nothing testable",
            help="Every work order was a token booking. No verdict is possible "
                 "either way — which is different from the master being fine."),
    })
st.caption("Run PCS/HR only — setup and HRS/LOAD are judged separately and do "
           "not appear in these counts.")
st.download_button("Download this coverage table as CSV",
                   show.to_csv(index=False).encode("utf-8"),
                   file_name="h0_operation_coverage.csv", mime="text/csv",
                   icon=":material/download:")

st.divider()

# ---- how it is kept honest --------------------------------------------------
s1, s2 = st.columns([1.15, 1])

with s1:
    st.subheader("Staying honest about staleness")
    st.markdown(f"""
A stale workbook looks completely normal — right columns, plausible numbers,
recent-looking date — and nothing in it says the data underneath has been
replaced. That has already cost this project once: an extract was re-run to fix
an arithmetic bug, came back with an **identical row count**, and was taken to
be the same data with the bug fixed. It was not. Ten families' routings had been
rebuilt in the ERP meanwhile and 8,549 hours had left scope. **Row counts are
not a check.**

So this tool does two things about it:

1. **It refuses to render** results whose files are out of order — if the
   extract is newer than the analysis, or the update list older than the
   extract, you get a stop rather than a warning.
2. **It rebuilds the evidence** for every unit you open, from
   `{paths.CACHE.name}`, and compares its own answer with the one stored in the
   workbook. Agreement is stated on the page. Disagreement is stated louder.
""")

with s2:
    st.subheader("The pipeline behind this")
    st.caption("These produce the files in the left rail. This tool only reads "
               "what they write — it never runs them, and it writes nothing.")
    st.code('''python h0_v2_analysis.py    "S LUCIDARE"    # run, part level
python h0_v2_family_view.py "S LUCIDARE"    # run, family level
python h0_v2_setup_view.py                  # setup, all operations
python h0_v2_load_view.py                   # HRS/LOAD, all operations
python h0_v2_update_list.py                 # consolidates - run it last, always
''', language="bash")

st.divider()
st.page_link("pages/5_How_it_works.py",
             label="How a conclusion is drawn from all this — the method",
             icon=":material/school:")
