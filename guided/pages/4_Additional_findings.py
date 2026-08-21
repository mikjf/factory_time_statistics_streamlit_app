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

# The three findings, named once. Every place that prints one of them - the
# rail's cost rows, the radio, the heading over the body - reads these, so the
# rail and the selector cannot end up calling the same finding two things.
MICRO = "Work orders with micro durations"
SETUPS = "Setups charged but not performed"
LOADS = "Runs with multiple loads"

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
    rows = [(MICRO, ui.hrs(tok.STANDARD_CHARGED.sum()))]
    if skip is not None:
        rows.append((SETUPS, ui.hrs(skip.STANDARD_CHARGED_SKIPPED.sum())))
    if gap is not None:
        rows.append((LOADS, ui.hrs(gap.OVER_RESERVED_HOURS.sum())))
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
with st.sidebar:
    st.divider()
    ui.side_title(st, "What to look at")
    choices = [MICRO] + ([SETUPS] if skip is not None else [])         + ([LOADS] if gap is not None else [])
    choice = st.radio("Finding", choices, label_visibility="collapsed")

    # The filters for the chosen finding, and nothing else. "Runs with multiple
    # loads" is four rows of one column each and carries none - a filter over
    # four rows is furniture.
    fam = op = rt = None

    def _pickers(frame, key):
        """Family, then the operations those families are actually routed
        through - the same cascade Inspect uses. Offering all 48 operations
        under a family with four steps sends a reader to an empty table by way
        of a valid-looking choice."""
        f = st.multiselect("Family", sorted(frame.FAMILY.unique()),
                           placeholder="all families", key=f"{key}fam")
        scope = frame[frame.FAMILY.isin(f)] if f else frame
        o = st.multiselect("Operation", sorted(scope.OPERATION.unique()),
                           placeholder="all operations", key=f"{key}op")
        return f, o

    if choice == MICRO:
        fam, op = _pickers(tok, "tok")
    elif choice == SETUPS:
        fam, op = _pickers(skip, "skip")
        rt = st.multiselect("Run type", sorted(skip.RUN_TYPE.unique()),
                            placeholder="both")

# The title and the banner above never change - they are true of all three -
# so the section heading is what says which finding is on screen.
st.subheader(choice)

if choice == MICRO:
    # Heading, figures, explanation, evidence - the order Inspect already uses,
    # with the counts first and the two hour figures last.
    #
    # STANDARD CHARGED BESIDE HOURS BOOKED is the whole finding in two numbers.
    # 2'418 h allowed against 16.81 h recorded says on sight that the second is
    # not a measurement, which no arrangement before this one managed to say.
    #
    # STEPS IS 346 - every step holding one of these work orders. It was nearly
    # 119, which is the subset that fell under the floor afterwards: a different
    # fact, and 227 steps short of what this label claims.
    #
    # THE 50 IS A CAPTION, NOT A TILE. It is the analytical damage rather than a
    # total of anything on screen - standards that would have been tested and
    # now never will be. As a tile it read as a fifth total; as a sentence it
    # can say "of those" and carry the 69 as the caveat that stops it being
    # overstated.
    #
    # THE FLOOR TOGGLE IS GONE. It returned all 119, mixing the 50 the tokens
    # broke with the 69 that were already too small - the one set nobody wants -
    # and it could not change the two counts above it, because they described
    # exactly the rows it selected. WO_ALL, WO_REAL and BELOW_FLOOR_AFTER are
    # columns in the table and in the CSV for anyone who wants to slice it.
    #
    # Every figure comes from the filtered frame, so the row always describes
    # the table under it; the standing plant-wide totals are in the rail.
    d = tok[tok.FAMILY.isin(fam)] if fam else tok
    if op:
        d = d[d.OPERATION.isin(op)]
    c = st.columns(4)
    c[0].metric("Work orders", ui.num(d.WO_TOKEN.sum()))
    c[1].metric("Steps", ui.num(len(d)),
                help="Every family, part type and routing step holding at "
                     "least one of these work orders.")
    # THE TWO HOUR FIGURES ARE QUOTED DIFFERENTLY, deliberately. Standard
    # charged is a large allowance where decimals are noise, and whole hours
    # keeps it equal to the same figure in the rail - the two sit on one screen
    # and 2'418 beside 2'417.69 is a discrepancy a reader has to resolve.
    # Hours booked is a near-zero value where the decimals ARE the finding:
    # at dec=0 it rounds to 17 h, which could pass for a small real duration,
    # and the point is that it is not one.
    c[2].metric("Standard charged", ui.hrs(d.STANDARD_CHARGED.sum()),
                help="What the routing allowed for them, which the schedule "
                     "reserved and the costing charged.")
    c[3].metric("Hours booked", ui.hrs(d.HOURS_BOOKED.sum(), 2),
                help="What was actually recorded against them. The gap is not "
                     "a measured overrun — the real time is simply not "
                     "known.")
    st.markdown(f"""
Micro durations refer to bookings at or under **{pipeline.TOKEN_HOURS} h**.
These are work orders closed to move them along, not a measurement, so they are
dropped before any standard is tested.

**`STANDARD_CHARGED`** is the number to look at. It is what those work orders
carried: hours the schedule reserved and the costing charged against jobs with
no evidence they were performed.
""")

    # THE COLUMNS ON SCREEN, NAMED. Everything here used to render its raw
    # database name - RUN_TYPE_MASTER, WO_ALL, STANDARD_CHARGED - which is an
    # identifier shown to a reader who has no schema. Identity first, then the
    # work orders, then what it cost.
    #
    # BELOW_FLOOR_AFTER is not among them: it is a flag whose meaning takes a
    # sentence, and the page no longer spends one on it. It stays in the CSV,
    # where a reader who wants it has the columns to work it out.
    _show = ["FAMILY", "PART_TYPE", S, "OPERATION", "RUN_TYPE_MASTER", "PARTS",
             "WO_ALL", "WO_TOKEN", "WO_REAL", "TOKEN_RATE", "PIECES",
             "STANDARD_CHARGED", "HOURS_BOOKED"]
    _t = d[_show].copy()
    # ADV / ANDV on screen, the same abbreviation the rest of the tool uses.
    # The CSV keeps the full wording - a spreadsheet is where somebody filters
    # on it, and "ADV" is not what the ERP calls it.
    _t["PART_TYPE"] = _t.PART_TYPE.map(
        lambda v: ui.part_tag(v, with_title=False))
    # SCALED TO 0-100. ProgressColumn's printf format is applied to the RAW
    # value, so "%.0f%%" over a rate of 0.733 printed "1%" on every row while
    # the bar beside it - which reads min_value/max_value - was correctly at
    # 73%. A number and its own bar disagreeing is worse than either alone.
    # The CSV keeps the 0-1 rate, which is what the sheet stores.
    _t["TOKEN_RATE"] = _t.TOKEN_RATE * 100
    # TOKEN_RATE is deliberately absent from the Styler: it drives a
    # ProgressColumn, which needs the raw number to size its bar.
    st.dataframe(ui.swiss_grid(_t, {"PARTS": ",.0f", "WO_ALL": ",.0f",
                                    "WO_TOKEN": ",.0f", "WO_REAL": ",.0f",
                                    # Both hour columns at the precision the
                                    # pipeline stores them in - it rounds each
                                    # to 2 - so the column, the metric above it
                                    # and the CSV all quote one figure.
                                    "PIECES": ",.0f", "HOURS_BOOKED": ",.2f",
                                    "STANDARD_CHARGED": ",.2f"}),
                 hide_index=True, width="stretch", height=380,
                 column_config={
                     "FAMILY": st.column_config.TextColumn("Family",
                                                           width="medium"),
                     "PART_TYPE": st.column_config.TextColumn("Part type",
                                                              width="small"),
                     S: st.column_config.NumberColumn("Step", format="%d"),
                     "OPERATION": st.column_config.TextColumn("Operation"),
                     "RUN_TYPE_MASTER": st.column_config.TextColumn("Run type"),
                     "PARTS": st.column_config.NumberColumn("Parts"),
                     "WO_ALL": st.column_config.NumberColumn("Work orders"),
                     "WO_TOKEN": st.column_config.NumberColumn("Micro"),
                     "WO_REAL": st.column_config.NumberColumn("Real"),
                     "TOKEN_RATE": st.column_config.ProgressColumn(
                         "Micro rate", min_value=0, max_value=100,
                         format="%.0f%%"),
                     "PIECES": st.column_config.NumberColumn("Pieces"),
                     "STANDARD_CHARGED": st.column_config.NumberColumn(
                         "Standard charged h"),
                     "HOURS_BOOKED": st.column_config.NumberColumn("Booked h"),
                 })
    st.download_button("Download as CSV", d.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_micro_duration.csv",
                       mime="text/csv", icon=":material/download:",
                       key="dl_tok")
    st.caption("The download carries every column of the source sheet, "
               "including the ones not shown here.")

elif choice == SETUPS:
    # Filtered first, for the reason above: these describe the table, not the
    # plant.
    d2 = skip[skip.FAMILY.isin(fam)] if fam else skip
    if op:
        d2 = d2[d2.OPERATION.isin(op)]
    if rt:
        d2 = d2[d2.RUN_TYPE.isin(rt)]
    c = st.columns(3)
    c[0].metric("Work orders skipped", ui.num(d2.WO_SKIPPED.sum()))
    c[1].metric("Steps", ui.num(len(d2)))
    c[2].metric("Charged for setups never performed",
                ui.hrs(d2.STANDARD_CHARGED_SKIPPED.sum()))
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
    #
    # ONLY WHILE NOTHING IS FILTERED. The figure above now follows the rail, so
    # under a family or a run type it is that selection's total - and comparing
    # one family's hours against the plant's 591 h would read as though the
    # family were missing the difference. Unfiltered, the two are the same two
    # numbers this sentence has always compared.
    _all = data.skip_hours_total()
    _shown = float(skip.STANDARD_CHARGED_SKIPPED.sum())
    if not fam and not op and not rt and abs(_all - _shown) >= 0.5:
        st.caption(
            f"The table below lists only steps with "
            f"{pipeline.SETUP_MIN}+ work orders, so the figure "
            f"above is short of the whole picture. Across every step, "
            f"including those too small to list, "
            f"**{ui.hrs(_all)}** was charged for setups never "
            f"performed — {ui.hrs(_all - _shown)} of it in steps that "
            f"do not appear here.")
    # Same shape as the micro-durations table: identity, then the work orders,
    # then what it cost. SECTION is dropped - it is the plant area, which none
    # of the other tables carry and nothing on this page refers to.
    _show2 = ["FAMILY", "PART_TYPE", S, "OPERATION", "RUN_TYPE", "PARTS",
              "WO_ALL", "WO_SKIPPED", "WO_REAL", "SKIP_RATE",
              "SETUP_HRS_CURRENT", "STANDARD_CHARGED_SKIPPED",
              "STANDARD_CHARGED_ALL_WO"]
    _t2 = d2[_show2].copy()
    _t2["PART_TYPE"] = _t2.PART_TYPE.map(
        lambda v: ui.part_tag(v, with_title=False))
    _t2["SKIP_RATE"] = _t2.SKIP_RATE * 100          # see the note above
    st.dataframe(ui.swiss_grid(
        _t2, {"PARTS": ",.0f", "WO_ALL": ",.0f", "WO_SKIPPED": ",.0f",
              "WO_REAL": ",.0f", "SETUP_HRS_CURRENT": ",.3f",
              "STANDARD_CHARGED_SKIPPED": ",.1f",
              "STANDARD_CHARGED_ALL_WO": ",.1f"}),
                 hide_index=True, width="stretch", height=380,
                 column_config={
                     "FAMILY": st.column_config.TextColumn("Family",
                                                           width="medium"),
                     "PART_TYPE": st.column_config.TextColumn("Part type",
                                                              width="small"),
                     S: st.column_config.NumberColumn("Step", format="%d"),
                     "OPERATION": st.column_config.TextColumn("Operation"),
                     "RUN_TYPE": st.column_config.TextColumn("Run type"),
                     "PARTS": st.column_config.NumberColumn("Parts"),
                     "WO_ALL": st.column_config.NumberColumn("Work orders"),
                     "WO_SKIPPED": st.column_config.NumberColumn("Skipped"),
                     "WO_REAL": st.column_config.NumberColumn("Performed"),
                     "SKIP_RATE": st.column_config.ProgressColumn(
                         "Skip rate", min_value=0, max_value=100,
                         format="%.0f%%"),
                     "SETUP_HRS_CURRENT": st.column_config.NumberColumn(
                         "Setup h", help="SETUP_HRS as the routing holds it."),
                     "STANDARD_CHARGED_SKIPPED": st.column_config.NumberColumn(
                         "Charged, skipped h",
                         help="Setup hours charged on work orders where no "
                              "setup happened."),
                     "STANDARD_CHARGED_ALL_WO": st.column_config.NumberColumn(
                         "Charged, all h",
                         help="Setup hours charged across every work order at "
                              "this step, performed or not."),
                 })
    st.download_button("Download as CSV",
                       d2.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_setups_not_performed.csv", mime="text/csv",
                       icon=":material/download:", key="dl_skip")

else:
    st.metric("Allowed and not used",
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
    # Four rows, one per operation - no family here, so identity is the
    # operation alone.
    st.dataframe(ui.swiss_grid(
        gap, {"WORK_ORDERS": ",.0f", "STEPS": ",.0f", "PARTS": ",.0f",
              "HOURS_MASTER": ",.0f", "HOURS_WORKED": ",.0f",
              "OVER_RESERVED_HOURS": ",.0f", "RATIO": ",.3f"}),
        hide_index=True, width="stretch",
        column_config={
            "OPERATION": st.column_config.TextColumn("Operation"),
            "WORK_ORDERS": st.column_config.NumberColumn("Work orders"),
            "STEPS": st.column_config.NumberColumn("Steps"),
            "PARTS": st.column_config.NumberColumn("Parts"),
            "MEDIAN_LOADS": st.column_config.NumberColumn("Loads, median"),
            "MAX_LOADS": st.column_config.NumberColumn("Loads, max"),
            "HOURS_MASTER": st.column_config.NumberColumn("Master h"),
            "HOURS_WORKED": st.column_config.NumberColumn("Actual h"),
            "OVER_RESERVED_HOURS": st.column_config.NumberColumn(
                "Allowed, not used h"),
            "RATIO": st.column_config.NumberColumn("Actual ÷ master"),
            "FIXED_HOURS_A": st.column_config.NumberColumn(
                "Fixed h", help="The part of the job that does not repeat per "
                                "load - fitted, not stored."),
            "MARGINAL_LOAD_B": st.column_config.NumberColumn(
                "Per extra load h",
                help="What a second load actually costs in hours."),
            "MARGINAL_AS_PCT_OF_RUN": st.column_config.NumberColumn(
                "As % of RUN",
                help="That marginal load against what the standard charges "
                     "for one."),
        })
    st.download_button("Download as CSV",
                       gap.to_csv(index=False).encode("utf-8"),
                       file_name="h0_additional_findings_multiple_loads.csv", mime="text/csv",
                       icon=":material/download:", key="dl_gap")
