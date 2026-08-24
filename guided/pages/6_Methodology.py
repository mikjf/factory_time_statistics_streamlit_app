"""The whole path from raw labour tickets to the decisions on the queue.

Was called "Dataset", back when it only described the extract. It grew the
deduction, the three steps, the six rules and the reconciliation, and at that
point the name undersold it. Named for what it is now: the word somebody
reaches for when they doubt a number. Its sibling kept the interpretive half -
how to read one recommendation once you have it - and is named for that.
"""

import pathlib
import sys

import pandas as pd
import streamlit as st

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import data, freshness, paths, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="Methodology · H0",
                   page_icon=":material/database:", layout="wide")
ui.inject()
st.title("Methodology")
# The joining of tickets to routings was said here and again, more fully, in
# text.WHERE_FROM directly below. Left to the one that defines the vocabulary.
st.caption("Every rule that turns raw labour tickets into the recommendations "
           "on this site. Read top to bottom.")
freshness.guard()

# Four tables stack down this page in two pairs, and each pair has to read as
# one object rather than two that nearly line up.
# 52%, not the 70% default: the reconciliation table below carries four numeric
# columns, and at 70% they get 61px each - too narrow for 10'966. The label
# columns on the other tables still have 420px, which their longest label uses
# about 340 of.
ui.align_table_columns(st, table_pct=52)

facts = data.extract_facts()
ops = data.operation_summaries()
acts = data.actions()

with st.sidebar:
    # What the analysis was built from, and when it was last built. Both facts
    # sit here rather than only in the body because the sidebar does not
    # scroll: on much the longest page in the app, the window the figures are
    # bounded by stays visible the whole way down, where the body caption
    # saying the same thing is off screen after the first table.
    #
    # This replaced five filenames and their modification times. Those said
    # "is it current?" in the language of the folder rather than the data -
    # nobody outside this project can place H0_v2_LOAD.xlsx - and five stamps
    # within half an hour of each other carried one fact between them.
    ui.kv(st, "Key dates", [
        ("First labour ticket", f"{facts['first']:%d %b %Y}"),
        ("Last labour ticket", f"{facts['last']:%d %b %Y}"),
        ("Last full analysis run", paths.stamp(paths.UPDATE_LIST)),
    ])
    # The run time is the third row of that block, not a separate caption under
    # it - all three are provenance, and a rule or a gap between them split one
    # idea into two. It comes off the update list, the last artefact the
    # pipeline writes, so the stamp is when the whole run finished rather than
    # when any one step did. Full stamp rather than the date alone: two runs on
    # one day are ordinary here and a date could not tell them apart.
    #
    # A divider HERE, where "How to read it" has one too, because what follows
    # IS a different idea: provenance above, the numbers the rules fire on
    # below.
    #
    # The thresholds sit on this page as well as on "How to read it" because
    # this is where the six rules are actually enumerated, a long scroll below.
    # Same helper, so the two cannot disagree.
    st.divider()
    ui.thresholds(st)

# ---- what is in it ----------------------------------------------------------
c = st.columns(5)
# NOT "labour tickets": one row is work order x routing step x Run/Setup x
# resource, and the query sums the tickets inside each one. 76'113 rows carry
# 120'570 tickets - 2.12x inside the run scope - so the two are nowhere
# interchangeable.
#
# The extract CAN say how many: LT_ROWS carries the count and is non-null on
# every row. Deliberately not published - nothing in the analysis tests at
# ticket grain, so the column would be a number no threshold ever uses.
c[0].metric("Labour booking lines", ui.num(facts["rows"]),
            help="One row per work order, routing step, run or setup, and "
                 "resource. Labour tickets are summed within each.")
c[1].metric("Work orders", ui.num(facts["work_orders"]))
c[2].metric("Parts", ui.num(facts["parts"]))
c[3].metric("Families", ui.num(facts["families"]))
c[4].metric("Operations", ui.num(facts["operations"]))

# Derived from FY_START rather than written down - see pipeline.FY_LABEL, where
# it now lives so that Inspect and the landing page print the same name.
_fy = pd.Timestamp(pipeline.FY_START)
FY_LABEL = pipeline.FY_LABEL

# The window is still stated by its dates as well as its name: bookings run from
# the start of the fiscal year to the day the extract was taken, which is not
# twelve months, and every hours total on the site is bounded by it.
st.caption(
    f"Fiscal year from {FY_LABEL} onwards. Bookings in this extract run "
    f"{facts['first']:%d %b %Y} to {facts['last']:%d %b %Y}. Every hours "
    f"figure in this tool is what has already been registered in this time "
    f"window.")

# Moved here from "How to read it", which is about reading one recommendation.
# This is the question the whole page answers, and it carries the only place the
# tool defines its own two words: a recommendation names "actual" and "master"
# on every screen, and nothing else says what they are or that their ratio IS
# the analysis.
st.markdown(text.WHERE_FROM)

st.divider()

# ---- what is in scope -------------------------------------------------------
# Directly above the funnel, because these exclusions are what its first two
# bars are counting. Moved here from the method page: every row is a statement
# about which labour tickets exist in the data, not about how they are judged.
st.subheader("What is deliberately left out", anchor="left-out")
st.caption("Applied before anything is measured. Each of these removes rows "
           "that cannot support a conclusion about a master standard.")

# Built from data.EXCLUSIONS rather than written out, so this table and the
# deduction table below always name the same rules in the same words. They used
# to be two hand-written lists: this one said "steps not in the current master
# routing" where the other said "the step is no longer in the master routing",
# and only two of seven rows corresponded at all.
#
# Rules flagged not-described are skipped - see data.EXCLUSIONS for the one that
# is. A described rule with no reason written for it would render a blank cell,
# so the assert turns a silent gap into a loud one the moment a rule is added.
_described = [(label, text.WHY_EXCLUDED.get(label, ""))
              for label, _, describe in data.EXCLUSIONS if describe]
assert all(why for _, why in _described), \
    "every described exclusion needs a reason in text.WHY_EXCLUDED"
st.markdown(
    "| Excluded | Why |\n|---|---|\n" +
    "\n".join(f"| {label} | {why} |" for label, why in _described))

# ---- the same exclusions, counted ------------------------------------------
# The prose above says which rules exist; this says what they cost. Directly
# below it so the two read as one statement, and above the funnel because the
# surviving total IS the funnel's first bar.
#
# Every booking line is counted against the FIRST rule it meets, so the column
# subtracts down to the total instead of overshooting - see data.EXCLUSIONS
# for why the order is what it is.
st.subheader("What that leaves to analyse", anchor="leaves")
st.caption("The scope rules above, counted — not the ones applied later inside "
           "an analysis, which act on what survives here and cannot be added "
           "to the same column. Every booking line is charged to the first "
           "rule it meets, so the column subtracts down to the total.")

(n0, h0), rows, split, (n1, h1) = data.deduction()

# "Booking lines", not "Tickets" - the same word the metric above uses. Both
# count ROWS, and a row is one work order at one step on one resource with its
# tickets already summed inside it. "Tickets" understated the true count by
# 2.12x on the run scope and contradicted this page's own metric.
tbl = [{"": "Every booking line in the extract",
        "Booking lines": ui.num(n0), "Hours": ui.num(h0)}]
for label, n, h in rows:
    # A rule that catches nothing is dropped from the table rather than shown
    # at zero. The fiscal-year bound is the case: the query now applies it at
    # source, so the row was permanently empty and read as clutter.
    #
    # DROPPED FROM THE DISPLAY, NOT FROM THE COMPUTATION - the rule still runs
    # in data.EXCLUSIONS. If a future extract ever carries pre-year bookings
    # again the row reappears on its own, which a hard-coded deletion here
    # would not do. Subtracting nothing changes no total, so the column
    # reconciles either way.
    if n == 0:
        continue
    # "+ 0.0" normalises negative zero. The zero-hour tickets sum to exactly
    # 0.0, negating gives -0.0, and "+,.0f" renders that as "-0" - which reads
    # as a rounding artefact hiding a real number rather than the true nothing
    # it is.
    h = h + 0.0
    # BACKSLASH-ESCAPED, and it has to be. st.table renders each cell as
    # markdown, so a leading "- " is list syntax: the row came out as a bulleted
    # <li> with the hyphen swallowed, showing "Rework" where it should have read
    # "- Rework". The escape produces a literal ASCII hyphen, which is also the
    # character the number formatter puts on the values in the same row.
    tbl.append({"": f"\\- {label}",
                "Booking lines": ui.num(n),
                # Reversals carry negative hours, so removing them ADDS to the
                # running total. Signed explicitly, because a "+" in a column
                # of deductions is the one entry a reader will assume is a bug.
                "Hours": "0" if abs(h) < 0.5 else ui.fmt(h, "+,.0f")})
# No "=" prefix: the bold already says this is the result, and a third prefix
# state alongside "" and "-" made the label column noisier than the arithmetic
# it was meant to clarify.
#
# Bold has to be applied per cell rather than to the row: st.table renders each
# cell as its own markdown block, so there is no row-level markup to hang it on.
tbl.append({"": "**Carried into the analysis**",
            "Booking lines": f"**{ui.num(n1)}**",
            "Hours": f"**{ui.num(h1)}**"})

st.table(pd.DataFrame(tbl).set_index(""))
# Booking lines first, hours second, so the sentence runs in the same order as
# columns above it. The bold stays on hours: that is the figure the rest of the
# tool is denominated in.
st.caption(
    f"That is {n1 / n0:.0%} of the booking lines in the window, and "
    f"**{h1 / h0:.0%} of the hours** booked — the two differ because most of "
    f"what is removed is many small lines rather than many hours. Rows are "
    f"counted against the first rule they meet, so the column subtracts down to the "
    f"total; the rules overlap, and counted independently they would sum to "
    f"more than the extract holds.")

st.subheader("Carried hours split per type", anchor="split")
st.caption("Each is analysed separately, and the split is exhaustive — nothing "
           "carried in falls outside these three.")
sp = [{"": label, "Booking lines": ui.num(n), "Hours": ui.num(h)}
      for label, n, h in split]
st.table(pd.DataFrame(sp).set_index(""))
st.caption(
    "They are kept apart because the arithmetic differs. A master held in "
    "pieces per hour is a rate, so a correction divides it; setup hours and a "
    "master held in hours per load are durations, and a correction multiplies. "
    "One pooled ratio across all three would be wrong in both directions at "
    "once.")

# ---- exclusions that happen later, per analysis ----------------------------
# These are real exclusions too, but they act on what SURVIVED the count above,
# inside one analysis rather than across all three, so they cannot be added to
# the same column. Placed after the split rather than before the deduction,
# where it used to sit: there it interrupted the two sections that belong
# together - the rules, then the count of those rules - and offered a second,
# uncountable list before the reader reached the first total.
#
# "an analysis" rather than "the analysis" because the split directly above
# just showed three of them, and each row here names which one it applies to.
st.subheader("What is set aside inside an analysis", anchor="set-aside")
st.caption("Applied after everything above, by one analysis rather than all "
           "three. These act on the hours that survived, so they are not part "
           "of the count.")
st.markdown(text.WHAT_IS_EXCLUDED_LATER)

st.divider()

# ---- what makes one pool ----------------------------------------------------
# Directly above Step 1, whose heading is "one row per WO x standard" - forming
# the pool IS that step, so the rule that decides what lands in one belongs
# immediately before it rather than buried in the method summary.
#
# NO COUNTS HERE, on purpose. The first draft carried four - 657 pools spanning
# a revision, 32 split, 216 left whole, 0 of those acted on - and every one of
# them was defending a design decision rather than reporting a finding. A reader
# meeting "216 pools, of which 0 produce an action" goes looking for 216
# problems. The rule is the point; the tallies belong to whoever maintains it,
# and data.pooling() went with them.
st.subheader("What counts as one pool", anchor="one-pool")
st.markdown("""
One part, one operation, one routing step — every work order matching those
three is judged together. The routing revision is not part of it: a revision is
bumped for any edit anywhere in the routing, so it says nothing about this
step's time.

What does separate work orders is the standard itself changing during the year.
Only those run under the current value are tested — the earlier ones measured a
standard that has since been replaced. Where too few ran under the new value to
judge it, nothing is proposed for that step.
""")

st.divider()

# ---- the funnel -------------------------------------------------------------
# Full width, and the explanation lives on the bars rather than in a column
# beside them. It used to be a five-paragraph panel headed "Why the two halves
# cannot be added"; most of it was answering a question raised one bar earlier,
# so it now sits on that bar. Two of its paragraphs had also gone stale - the
# funnel labels its own units in the section headings, which it did not when
# they were written.
fn = data.run_funnel()
_booked = fn["with_duration"]
_units = int(ops.UNITS.sum())
_per_unit = _booked / max(_units, 1)

# The heading names the unit this step STARTS in. Safe to do only because the
# bar that crosses into the other unit spells its own out - without that, a
# single unit up here would read as covering all three bars, and the last one
# counts something else.
st.subheader("Step 1 — from work orders to standards — the `PCS/HR` run "
             "analysis — one row per WO × standard", anchor="step-1")
st.caption("Shown for `PCS/HR` run because it is the biggest of the three and "
           "the one the method was built on. Setup and `HRS/LOAD` narrow the "
           "same way on their own share. Nothing here judges a standard yet — "
           "this is only getting the evidence into the shape a standard can be "
           "judged in.")

# SPLIT IN TWO, with the six rules between the halves. They were one funnel, and
# the join was where every question landed: the count more than halves at the
# regrouping without anything being removed, and the three bars after it are
# six rules wearing three labels. Cutting there lets the first half be about
# preparing evidence and the second about testing it, and lets the rules be
# stated before the reader watches them fire.
#
# Two sections inside this half, because the unit changes: one part-and-step is
# however many work orders happened to run it. Drawn on a single scale the drop
# read as ten thousand work orders being thrown away.
#
# COUNTED IN WORK ORDERS, NOT BOOKING LINES, and the distinction is not pedantic
# here. ops.WORK_ORDERS is the workbooks' "Work orders in scope", which is
# nunique per operation - so a work order visiting ten operations counts ten
# times, and the figure is really work-order x operation. Booking lines for the
# same scope come to 20,618, which is what the deduction table above reports on
# its Run PCS/HR row.
ui.funnel(st, [
    # ui.funnel prepends "counted in", so the unit string must not repeat it
    ("What the shop floor booked", "work orders at one standard", [
        # Opens where the deduction table closed. It used to open on 19,050,
        # the workbooks' per-operation distinct work orders, which is a grain
        # nothing else on the page uses - lower than the booking lines above
        # it for a reason no reader could infer.
        # No backticks in a bar note - ui.funnel escapes them rather than
        # rendering markdown, so they come out as literal characters.
        # The gap between the line count and this bar is explained only when
        # there IS one. Today it is a single row; it is not structurally always
        # one, and a note describing a difference of zero would send a reader
        # hunting for it.
        ("Carried into this analysis", fn["at_a_standard"],
         f"the {ui.num(fn['lines'])} PCS/HR run booking lines above, one "
         f"row per work order per standard"
         + (f" (more lines than rows means the same part, operation, "
            f"sequence and work order ran on more than one machine)"
            if fn["lines"] > fn["at_a_standard"] else "")),
        ("With a duration actually recorded",
         _booked,
         f"{ui.num(fn['tokens'])} were closed at ≤ "
         f"{pipeline.TOKEN_HOURS} h — a booking that records a closure, "
         f"not a job timed"),
    ]),
    ("What a master is judged on", "part × routing step", [
        # THE ONE BAR THAT NEEDS DEFENDING. The count falls by more than half
        # here and nothing has been discarded - the unit changed.
        ("Standards examined (part × sequence × operation)", _units,
         f"the level a master actually lives at — the same work orders "
         f"grouped into standards, about {_per_unit:.0f} each. Nothing is "
         f"discarded here; the unit changes"),
    ]),
], scale_to=fn["at_a_standard"])

st.divider()

# ---- the six rules ----------------------------------------------------------
# Rendered from text.rules(), the same source the sidebar rail and the method
# page use, so a page carrying its own copy cannot drift from the rail a reader
# checks it against.
st.subheader("The six rules", anchor="six-rules")
st.caption("Applied in this order to every one of those standards. All six must "
           "pass before a change is proposed — and every unit's page shows "
           "which of them it passed, including the ones left alone.")
ui.rule_cards(st, text.rules())

st.divider()

# ---- the funnel, second half ------------------------------------------------
# Reopens on the same 8,749 the first half closed on, so the drop to 607 stays
# visible. Repeating the number is the join.
# The unit goes in this heading and NOT in step 1's. Every bar here is one
# part x sequence x operation. Step 1 crosses from work orders to standards, so
# a single unit in its heading would contradict its own last bar.
st.subheader("Step 2 — from standards to decisions — the `PCS/HR` run "
             "analysis — part × sequence × operation", anchor="step-2")
st.caption("The same six rules, now as counts. This is where the analysis "
           "actually narrows: most standards never carry enough work orders to "
           "be judged at all, and that is the design working rather than "
           "something missing.")
ui.funnel(st, [
    ("What survives each rule", "part × routing step", [
        # Same label and same number as step 1's last bar, deliberately. This
        # bar exists only to be the join between the two funnels, and it can
        # only do that if it is recognisably the same thing.
        ("Standards examined (part × sequence × operation)", _units,
         "carried down from above"),
        (f"1 · Enough work orders ({pipeline.MIN_WO}+)",
         int(ops.TESTABLE.sum()),
         f"the real narrowing — only "
         f"{int(ops.TESTABLE.sum()) / max(_units, 1):.0%} clear it. Below "
         f"this no test can reach significance, whatever the evidence"),
        ("2–4 · Genuinely different from the master",
         int(ops.SIGNIFICANT.sum()),
         "the test itself, the correction for testing hundreds of pools at "
         "once, and the interval. Different, not just different by chance"),
        ("5–6 · Big enough to be worth changing", int(ops.MATERIAL.sum()),
         f"at least {pipeline.MIN_EFFECT:.0%} off and "
         f"{pipeline.MIN_HOURS_IMPACT:g} h a year"),
    ]),
], scale_to=fn["at_a_standard"])   # same scale as the first half, so 8'749
                                   # is drawn the same width in both
# WAS ARITHMETICALLY FALSE. It read "those 59 plus setup's and HRS/LOAD's own
# share give 230 decisions" - 59 + 44 + 21 is 124. The 59 is the PART-LEVEL
# path only, which is what these workbooks count; the other 107 PCS/HR run
# decisions come from the family path, where a part too thin to judge alone is
# pooled with its family at the same step. That path is not in this funnel at
# all, and it produces nearly twice as many decisions as the one that is.
_run_part = int(((_acts_run := acts[(acts.TARGET == "RUN")
                                    & (acts.RUN_TYPE == "PCS/HR")])
                 .LEVEL == "PART").sum())
_run_fam = int((_acts_run.LEVEL == "FAMILY").sum())
st.caption(
    f"Those {_run_part} are the parts judged **on their own evidence** — the "
    f"{int(ops.TESTABLE.sum())} that cleared rule 1. The "
    f"{ui.num(int(ops.UNITS.sum()) - int(ops.TESTABLE.sum()))} that did not "
    f"are not dropped; they take the second route below.")

st.divider()

# ---- the funnel, third half -------------------------------------------------
# The route the part-level funnel never showed, and it produces most of the
# decisions - 107 against 59. A part too thin to judge alone is pooled with its
# family at the same step and the pool is judged instead, which is the whole
# reason the analysis has two levels.
#
# SCALED TO 20,618 LIKE THE OTHER TWO. The unit differs - a family pool is
# neither a work order nor a standard - but steps 2 and 3 are parallel routes
# whose outputs get added together, 59 + 107, so they have to be measurable
# against each other. On its own scale this funnel drew 107 at 9% while step 2
# drew 59 at 0.3%, which read as the family route being thirty times the size
# of the part route rather than roughly twice.
ff = data.family_funnel()
if ff:
    st.subheader("Step 3 — from thin parts to family pools — the `PCS/HR` run "
                 "analysis — family × part type × sequence × operation",
                 anchor="step-3")
    st.caption(
        f"The other route to a decision, and the busier one. A part that "
        f"cannot clear rule 1 alone borrows its family's evidence: its work "
        f"orders join the rest of the family at that step and the pool faces "
        f"the same six rules. Parts already flagged individually are left out "
        f"of the pool, so no part is corrected twice.")
    ui.funnel(st, [
        ("What a family is judged on", "family × part type × sequence × "
                                       "operation", [
            ("Family pools formed", ff["pools"],
             f"the same {ui.num(ops.UNITS.sum())} standards regrouped by "
             f"family at each step, covering "
             f"{ui.num(ff['parts_in_pools'])} of them — the other "
             f"{ff['parts_excluded']} are the parts flagged on their own"),
            (f"1 · Enough work orders ({pipeline.MIN_WO}+)", ff["testable"],
             f"{ff['testable'] / max(ff['pools'], 1):.0%} clear it, against "
             f"{int(ops.TESTABLE.sum()) / max(int(ops.UNITS.sum()), 1):.0%} of "
             f"parts alone — pooling is what buys the evidence"),
            ("2–4 · Genuinely different from the master", ff["different"],
             "the same three rules, on the pooled ratio"),
            ("5–6 · Big enough to be worth changing", ff["material"],
             f"at least {pipeline.MIN_EFFECT:.0%} off and "
             f"{pipeline.MIN_HOURS_IMPACT:g} h a year"),
        ]),
    ], scale_to=fn["at_a_standard"])

st.divider()

# ---- the reconciliation -----------------------------------------------------
# Where the three headline figures on the landing page come from. Every route
# that produces a decision, so the totals can be checked rather than taken.
st.subheader("Every route, and where the headline figures come from",
             anchor="routes")
st.caption("The six rules run separately down each of these routes. Nothing "
           "on this page is counted anywhere else on it.")

_rows, (_ta, _tp, _te, _th) = data.reconciliation()
rec = [{"": lab, "Standards": ui.num(n), "Parts": ui.num(p),
        "Rows to edit": ui.num(e), "Abs misstated h": ui.num(h)}
       for lab, n, p, e, h in _rows]
rec.append({"": "**Total**", "Standards": f"**{ui.num(_ta)}**",
            "Parts": f"**{ui.num(_tp)}**",
            "Rows to edit": f"**{ui.num(_te)}**",
            "Abs misstated h": f"**{ui.num(_th)}**"})
st.table(pd.DataFrame(rec).set_index(""))
_worst = max(_rows, key=lambda r: r[4])
# ui.num() per figure, NOT a .replace(",", "'") over the whole sentence. The
# blanket version turned every prose comma into an apostrophe too - "one
# MASTER_OPS_ROWID' one line in the routing" went live before it was spotted.
st.caption(
    f"**Standards** is one decision — what the landing page calls *standards "
    f"to review*. **Rows to edit** is one `MASTER_OPS_ROWID`, one line in the "
    f"routing; a family decision writes the same value to every part in its "
    f"pool, which is why {ui.num(_te)} rows carry only {ui.num(_ta)} "
    f"decisions. **Abs misstated h** is taken per decision before summing, so "
    f"a route running long and one running short do not cancel — and it is "
    f"where the work is: *{_worst[0]}* alone carries "
    f"{_worst[4] / _th:.0%} of it. **Parts** is the only column that does not "
    f"add down: a part corrected on its run standard and again on its setup "
    f"is two rows here and one part in the total, "
    f"{ui.num(sum(p for _, _, p, _, _ in _rows))} against {ui.num(_tp)}. "
    f"Setup has no part row because setup units average under four worked "
    f"hours in a year — nothing clears a materiality gate alone, so it is "
    f"judged at family level only.")

st.divider()

# ---- coverage ---------------------------------------------------------------
# COLLAPSED, because this is the appendix and the rest of the page is an
# argument. Its columns are the funnel's own stages broken out per operation, so
# a reader following the narrative has already been told this; a reader hunting
# for one operation is not reading the narrative at all and can open it.
#
# Not deleted. 15 of the 49 operations produced no action, and this is the only
# place in the tool that separates "tested and the standard holds" from "nothing
# was ever testable". Everywhere else both are a blank cell.
with st.expander("Every operation examined, and what came out of it — "
                 "including the ones that produced no action"):
    st.caption("Operations with zero actions are listed on purpose. 'Tested "
               "and it holds' and 'never enough evidence' are different "
               "statements, and from a blank list they look identical.")

    # ALL THREE ROUTES, not just part-level PCS/HR run. The old version counted
    # one route and printed 0 in its Actions column for 13 operations that do
    # have PCS/HR run actions - every one of them family-level. A false zero,
    # on the one table whose whole purpose is that a zero can be read.
    cov = data.coverage()
    st.dataframe(
        ui.swiss_grid(cov, {"ACTIONS": ",.0f", "PARTS": ",.0f",
                            "EDITS": ",.0f", "HOURS": ",.0f",
                            "EXAMINED": ",.0f", "TESTABLE": ",.0f"}),
        hide_index=True, width="stretch", height=460,
        column_config={
            "OPERATION": st.column_config.TextColumn("Operation",
                                                     width="medium"),
            "ROUTE": st.column_config.TextColumn(
                "Route",
                help="The three analyses. An operation can appear on more "
                     "than one — a milling step has both a run standard and "
                     "a setup standard, judged separately."),
            "LEVEL": st.column_config.TextColumn(
                "Level",
                help="Part — the part judged on its own evidence. Family — "
                     "parts too thin to judge alone, pooled with the rest of "
                     "their family at that step. Setup is family only: setup "
                     "units average under four worked hours in a year, so "
                     "nothing clears a materiality gate alone."),
            "EXAMINED": st.column_config.NumberColumn(
                "Pools examined",
                help="At part level, one part at one routing step. At family "
                     "level, one family at one step. The two are different "
                     "units, which is why the rows are split."),
            "TESTABLE": st.column_config.NumberColumn(
                f"Testable ({pipeline.MIN_WO}+ WO)",
                help="Pools carrying enough work orders to judge. Below this "
                     "no test can reach significance, whatever the evidence."),
            # The total is read off the table rather than written down. It said
            # 230 for as long as 230 was true, which is exactly how a figure
            # goes stale unnoticed: nothing recomputes a help string.
            "ACTIONS": st.column_config.NumberColumn(
                "Masters to review",
                help=f"Cleared all six rules. Sums to "
                     f"{int(cov.ACTIONS.sum()):,} across the table — the same "
                     f"figure the landing page shows."),
            "PARTS": st.column_config.NumberColumn("Parts"),
            "EDITS": st.column_config.NumberColumn(
                "Rows to edit",
                help="One MASTER_OPS_ROWID each. A family decision writes the "
                     "same value to every part in its pool."),
            "HOURS": st.column_config.NumberColumn(
                "Abs misstated h",
                help="Absolute, taken per decision before summing, so a "
                     "decision running long and one running short do not "
                     "cancel."),
            "OUTCOME": st.column_config.TextColumn(
                "Outcome",
                help="One of three. 'Changes proposed' — standards cleared "
                     "all six rules and are on the list. 'Tested and holds' — "
                     "pools cleared the work-order floor and nothing material "
                     "came out, so the standards are right. 'Not enough "
                     "evidence' — nothing cleared the floor, so there is no "
                     "verdict either way. The last two look identical from a "
                     "blank list, which is why they are named."),
        })
    st.caption(
        f"All three analyses at both levels, every operation each of them "
        f"examined — {len(cov)} rows. The counts sum to the totals above: "
        f"{ui.num(cov.ACTIONS.sum())} standards, {ui.num(cov.EDITS.sum())} "
        f"rows to edit, {ui.num(cov.HOURS.sum())} h. An operation appears once "
        f"per route and level it was judged on.")
    st.download_button("Download this coverage table as CSV",
                       cov.to_csv(index=False).encode("utf-8"),
                       file_name="h0_methodology_operations_examined.csv",
                       mime="text/csv",
                       icon=":material/download:")

st.divider()

# ---- how it is kept honest --------------------------------------------------
# Was a full section on staleness beside a block of shell commands. Both went.
#
# The commands were "The pipeline behind this" - five lines of python that only
# whoever runs the pipeline would ever type, on a page read by project
# management, finance and supply chain. They are in the README, where the person
# who needs them already looks.
#
# The staleness argument stays because it is a trust claim, but it does not need
# twenty lines: the timestamps are in the left rail on every page and the guard
# stops the render before anything is drawn. Saying it once, next to where it
# actually happens, is the whole of it.
# OUTSIDE the expander, deliberately. It is a claim about every figure on the
# page, not about the coverage table, and inside it a reader who never opened
# the expander would never meet it.
#
# Labelled with a bold lead rather than a subheader: one sentence set as a peer
# of "Step 1" and "The six rules" would carry weight it has not earned, but
# unlabelled at the foot of a long page it read as a stray afterthought.
st.caption(
    f"**Why the figures above can be trusted.** Every one is rebuilt from "
    f"`{paths.CACHE.name}` when you open a unit and checked against what the "
    f"workbook stored, and the file times in the left rail are verified in "
    f"order before any page renders — a newer extract than analysis is a stop, "
    f"not a warning. Row counts are not a check: an extract once came back "
    f"with an identical row count after ten families' routings had been "
    f"rebuilt underneath it.")

st.divider()
st.page_link("pages/5_How_to_read_it.py",
             label="How to read one of these recommendations",
             icon=":material/school:")
