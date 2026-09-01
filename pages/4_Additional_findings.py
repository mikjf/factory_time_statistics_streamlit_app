"""Real findings, additional to the standards work.

On their own page on purpose. Everything here is hours the schedule reserved and
the costing charged for work with no evidence it was performed. Mixed into the
review queue it would either be ignored or keyed in, and both are wrong.
"""

import pathlib
import sys

import streamlit as st

# parent.parent is streamlit_app/, where ftsapp lives. Every page inserts it
# itself rather than relying on Overview.py having run first: deep-link to a
# page in a fresh session and the import failed with ModuleNotFoundError:
# no module named 'ftsapp'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ftsapp import data, freshness, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="FTS · Additional findings",
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

    # The filters for the chosen finding, and nothing else.
    fam = op = rt = None

    def _pickers(frame, key):
        """Family, then the operations those families are actually routed
        through - the same cascade Inspect uses. Offering all 48 operations
        under a family with four steps sends a reader to an empty table by way
        of a valid-looking choice.

        Each placeholder carries how many options are behind it, the same way
        the Review queue's rail does. On Operation that figure is the cascade
        speaking: it drops from every operation this finding touches to just the
        chosen families' as soon as a family is picked, so the narrowing is
        visible without opening the box."""
        fams = sorted(frame.FAMILY.unique())
        f = st.multiselect("Family", fams,
                           placeholder=f"all families ({len(fams)})",
                           key=f"{key}fam")
        scope = frame[frame.FAMILY.isin(f)] if f else frame
        ops = sorted(scope.OPERATION.unique())
        o = st.multiselect("Operation", ops,
                           placeholder=f"all operations ({len(ops)})",
                           key=f"{key}op")
        return f, o

    if choice == MICRO:
        fam, op = _pickers(tok, "tok")
    elif choice == SETUPS:
        fam, op = _pickers(skip, "skip")
        rt = st.multiselect("Run type", sorted(skip.RUN_TYPE.unique()),
                            placeholder="both")
    else:
        # This finding used to carry no filters, on the grounds that
        # 04_MultiLoadGap is four rows. That was a fact about the sheet rather
        # than about the finding: rebuilt at the grain the other two use it is
        # 96 rows over 30 families, and the one family carrying 46% of the
        # hours could not be isolated. See data.multi_loads.
        fam, op = _pickers(data.multi_load_rows(), "gap")

# The title and the banner above never change - they are true of all three -
# so the section heading is what says which finding is on screen.
st.subheader(choice)

if choice == MICRO:
    # Heading, figures, explanation, evidence - the order Inspect already uses,
    # with the counts first and the two hour figures last.
    #
    # STANDARD CHARGED BESIDE HOURS BOOKED is the whole finding in two numbers:
    # thousands of allowed hours against a recorded figure in the tens says on
    # sight that the second is not a measurement, which no arrangement before
    # this one managed to say.
    #
    # STEPS IS EVERY STEP holding one of these work orders. It was briefly the
    # much smaller subset that fell under the floor afterwards - a different
    # fact, and several hundred steps short of what this label claims.
    #
    # THE 50 IS A CAPTION, NOT A TILE. It is the analytical damage rather than a
    # total of anything on screen - standards that would have been tested and
    # now never will be. As a tile it read as a fifth total; as a sentence it
    # can say "of those" and carry the 69 as the caveat that stops it being
    # overstated.
    #
    # THE FLOOR TOGGLE IS GONE. It returned every below-floor step, mixing the
    # ones the tokens broke with those already too small - the one set nobody
    # wants -
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
dropped before any standard is tested. `STANDARD_CHARGED` is the number to
look at. It is what those work orders carried: hours the schedule reserved and
the costing charged against jobs with no evidence they were performed.
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
                     # No width - sized to content, same as Family beside it.
                     "OPERATION": st.column_config.TextColumn("Operation"),
                     "RUN_TYPE_MASTER": st.column_config.TextColumn(
                         "Run type", width="small"),
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
                       file_name="fts_additional_findings_micro_duration.csv",
                       mime="text/csv", icon=":material/download:",
                       key="dl_tok")
    # NAMES WHAT IT ADDS AND WHY, the shape Inspect and the Review queue use.
    # It read "every column of the source sheet, including the ones not shown
    # here", which promises completeness and says nothing about whether the file
    # is worth opening. Two columns are missing from the screen and both matter:
    # the routing step is what makes a row identifiable at all, and
    # BELOW_FLOOR_AFTER is the analytical damage - the steps the token bookings
    # pushed under the six-work-order floor, which the caption above counts but
    # the table cannot show per row.
    st.caption("The download adds the routing step — without it a family and "
               "operation can appear twice — and BELOW_FLOOR_AFTER, which "
               "marks the steps these bookings pushed under the "
               "six-work-order floor. Those are the standards that will not "
               "be tested until real durations are booked.")

elif choice == SETUPS:
    # Filtered first, for the reason above: these describe the table, not the
    # plant.
    d2 = skip[skip.FAMILY.isin(fam)] if fam else skip
    if op:
        d2 = d2[d2.OPERATION.isin(op)]
    if rt:
        d2 = d2[d2.RUN_TYPE.isin(rt)]
    # FOUR FIGURES, the same shape as micro durations, and "Work orders" means
    # the same thing in both: the ones with the issue. There it is the 1'579
    # booked at or under the cut; here it is the 1'893 whose setup did not
    # happen. A reader who learns the word on one section keeps it on the next.
    #
    # CHARGED, ALL IS LAST, deliberately apart from the three beside it. Those
    # three describe the skipped work orders; this one spans every work order
    # at these steps, and it is here only as the denominator that gives 540 h a
    # size - one setup hour in five. Sitting between them it read as another
    # figure about the 1'893.
    c = st.columns(4)
    c[0].metric("Work orders", ui.num(d2.WO_SKIPPED.sum()),
                help=f"Setup tickets booked at or under {pipeline.SKIP_CUT} h, "
                     f"which means the setup did not happen. A work order with "
                     f"no setup ticket at all cannot be counted either way.")
    c[1].metric("Steps", ui.num(len(d2)),
                help="Every family, part type and routing step with a setup "
                     "standard here. Not all of them have a skip.")
    # THE UNFILTERED TOTAL LIVES HERE NOW. 03_SkipRate lists only steps with
    # SETUP_MIN or more work orders, so this figure is 540 h against a true
    # 591 h - and the paragraph that used to say so has gone. Without it the
    # page under-reports the finding by 51 h with nothing on screen admitting
    # it, so the caveat moves to the tooltip on the number it qualifies.
    _all = data.skip_hours_total()
    _shown = float(skip.STANDARD_CHARGED_SKIPPED.sum())
    _short = (f" The table lists only steps with {pipeline.SETUP_MIN}+ work "
              f"orders, so this is short of the whole picture: across every "
              f"step, including those too small to list, {ui.hrs(_all)} was "
              f"charged for setups never performed."
              if abs(_all - _shown) >= 0.5 else "")
    c[2].metric("Standard skipped",
                ui.hrs(d2.STANDARD_CHARGED_SKIPPED.sum()),
                help="Setup hours charged on work orders where no setup took "
                     "place." + _short)
    c[3].metric("Out of total standard",
                ui.hrs(d2.STANDARD_CHARGED_ALL_WO.sum()),
                help="Setup hours charged across every work order at these "
                     "steps, performed or not — what the figure beside it is "
                     "a share of.")
    st.markdown(f"""
Charged but not performed refers to bookings at or under **{pipeline.SKIP_CUT} h**.
That may be normal and correct: when several work orders of one family run back
to back on one machine, only the first needs a full setup. The standard in the
ERP charges `SETUP_HRS` on **every** work order whether a setup happened or
not.
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
    # Same shape as the micro-durations table: identity, then the work orders,
    # then what it cost. SECTION is dropped - it is the plant area, which none
    # of the other tables carry and nothing on this page refers to.
    # RUN_TYPE IS FILTERABLE BUT NOT SHOWN. It separates two regimes - HRS/LOAD
    # setups are skipped on 638 of 641 work orders against 26% for PCS/HR - but
    # that is one operation, S RICOTTURA, where a furnace load carries many work
    # orders and one setup serves all of them. The page makes nothing of the
    # distinction, so on screen the column reads "PCS/HR" on 246 of 285 rows.
    # It stays in the rail, where isolating the 39 HRS/LOAD steps is one click,
    # and in the CSV.
    _show2 = ["FAMILY", "PART_TYPE", S, "OPERATION", "PARTS",
              "WO_ALL", "WO_SKIPPED", "WO_REAL", "SKIP_RATE",
              "SETUP_HRS_CURRENT", "STANDARD_CHARGED_SKIPPED",
              "STANDARD_CHARGED_ALL_WO"]
    _t2 = d2[_show2].copy()
    _t2["PART_TYPE"] = _t2.PART_TYPE.map(
        lambda v: ui.part_tag(v, with_title=False))
    _t2["SKIP_RATE"] = _t2.SKIP_RATE * 100          # see the note above
    st.dataframe(ui.swiss_grid(
        # ALL THREE HOUR COLUMNS AT TWO DECIMALS, which is what the ERP holds
        # and what the sibling table already uses.
        #
        # The charged pair was at one decimal and losing real figures - 41 and
        # 73 of their values carry a second decimal, so 0.17 and 2.25 were
        # printing as 0.2 and 2.3.
        #
        # SETUP_HRS was at three and showing nothing for it: the only values
        # are 0.2, 0.25, 0.5, 0.5001, 1.0, 2.0001 and 4.0, and at three
        # decimals 0.5001 renders as "0.500" - identical to a plain 0.5. Those
        # .0001s are ERP rounding artefacts, not a measurement to a thousandth.
        _t2, {"PARTS": ",.0f", "WO_ALL": ",.0f", "WO_SKIPPED": ",.0f",
              "WO_REAL": ",.0f", "SETUP_HRS_CURRENT": ",.2f",
              "STANDARD_CHARGED_SKIPPED": ",.2f",
              "STANDARD_CHARGED_ALL_WO": ",.2f"}),
                 hide_index=True, width="stretch", height=380,
                 column_config={
                     # No width: Streamlit sizes the column to its contents,
                     # which here runs to 42 characters. The five numeric
                     # columns are pinned below, so what this takes comes out
                     # of the ones still on stretch rather than out of them.
                     "FAMILY": st.column_config.TextColumn("Family"),
                     "PART_TYPE": st.column_config.TextColumn("Part type",
                                                              width="small"),
                     S: st.column_config.NumberColumn("Step", format="%d"),
                     # No width - sized to content, same as Family above.
                     "OPERATION": st.column_config.TextColumn("Operation"),
                     "PARTS": st.column_config.NumberColumn("Parts"),
                     "WO_ALL": st.column_config.NumberColumn("Work orders"),
                     "WO_SKIPPED": st.column_config.NumberColumn("Skipped"),
                     # PIXEL WIDTHS on these two. Left to width="stretch" the
                     # surplus went to the last column - "Total h" ended up
                     # 200px wide for a value like 24.5 - while "Performed"
                     # truncated to "Perforn" and the skip bar was squeezed to
                     # half the width of the same bar on micro durations.
                     "WO_REAL": st.column_config.NumberColumn("Performed",
                                                              width=95),
                     "SKIP_RATE": st.column_config.ProgressColumn(
                         "Skip rate", min_value=0, max_value=100,
                         format="%.0f%%", width=150),
                     # THE THREE HOUR COLUMNS DO NOT MULTIPLY OUT, on about
                     # half the rows, and the tooltips say why: Setup h comes
                     # from correctly-staffed tickets only, while the other two
                     # sum every ticket, mismatched crews included. A crew that
                     # does not match the routing gets excluded from "what the
                     # standard is" but stays in "what got charged" - which is
                     # the right call (skip_rate has to count what the ERP
                     # charged whether or not the standard describes it), but
                     # it means Setup h x Work orders can run above or below
                     # Total h.
                     "SETUP_HRS_CURRENT": st.column_config.NumberColumn(
                         "Setup h", width=95,
                         help="SETUP_HRS as the routing holds it, taken only "
                              "from tickets whose crew matched the routing. "
                              "Skipped h and Total h count every ticket "
                              "regardless, so this will not always multiply "
                              "out to either."),
                     # Short headers on purpose - see the note below the
                     # table config. The tiles above carry the full wording.
                     "STANDARD_CHARGED_SKIPPED": st.column_config.NumberColumn(
                         "Skipped h", width=95,
                         help="Setup hours charged on work orders where no "
                              "setup happened — every such ticket, including "
                              "any whose crew did not match the routing."),
                     "STANDARD_CHARGED_ALL_WO": st.column_config.NumberColumn(
                         "Total h", width=95,
                         help="Setup hours charged across every work order at "
                              "this step, performed or not — including any "
                              "whose crew did not match the routing."),
                 })
    st.download_button("Download as CSV",
                       d2.to_csv(index=False).encode("utf-8"),
                       file_name=("fts_additional_findings_setups_not_"
                                  "performed.csv"), mime="text/csv",
                       icon=":material/download:", key="dl_skip")
    # Same shape as the download caption above. Three columns are off screen
    # here: the routing step, the analytic section, and the run type - the last
    # separating two regimes the page deliberately makes nothing of, since
    # HRS/LOAD skipping is one furnace operation where a single setup serves
    # many work orders.
    st.caption("The download adds the routing step — without it a family and "
               "operation can appear twice — the analytic section, and the "
               "run type, which separates the two regimes this table pools: "
               "HRS/LOAD skipping is one furnace operation where a single "
               "setup serves many work orders.")

else:
    # Rebuilt at family grain rather than read off 04_MultiLoadGap, so the two
    # pickers in the rail have something to pick. data.multi_loads carries the
    # reason the sheet cannot serve this.
    d3r = data.multi_load_rows()
    if fam:
        d3r = d3r[d3r.FAMILY.isin(fam)]
    if op:
        d3r = d3r[d3r.OPERATION.isin(op)]
    d3 = data.multi_loads(d3r)

    # FOUR FIGURES, the same shape as the two sections above: two counts, the
    # finding in hours, and the whole it came out of. "Work orders" means here
    # what it means there - the ones with the issue.
    #
    # IT IS NOT THE SUM OF 04_MultiLoadGap's WORK_ORDERS COLUMN. That sheet is
    # per operation, and some work orders meet two HRS/LOAD operations, so the
    # column sums to 369 against 277 distinct. Counting a work order once is
    # the only reading that survives the family filter as well.
    c = st.columns(4)
    c[0].metric("Work orders", ui.num(d3r.WORK_ORDER.nunique()),
                help="Work orders whose master charged for more than one load.")
    c[1].metric("Steps", ui.num(len(d3r)),
                help="One work order at one routing step. A work order meeting "
                     "the same operation at two sequences counts twice, which "
                     "is why this runs ahead of the count beside it.")
    c[2].metric("Standard allowed but not used",
                ui.hrs((d3r.HOURS_MASTER - d3r.HOURS_WORKED).sum()),
                help="Master hours minus hours worked: capacity the schedule "
                     "reserved and the costing charged, and nobody used.")
    # THE DENOMINATOR, and the tile that moves most under the pickers. Left off,
    # 1'032 h could be a fiftieth of the exposure or half of it; it is a third.
    # And the share is flat only in aggregate - the worst family loses 53% of
    # what it is charged, while another with MORE work orders loses 21%, which
    # an absolute figure alone hides completely.
    # SAME LABEL AS THE SETUPS SECTION, because it is the same idea: the whole
    # the figure beside it is a share of. The scope differs - there it widens
    # to every work order at the step, here it stays inside the multi-load
    # population - which is what the tooltips are for.
    c[3].metric("Out of total standard", ui.hrs(d3r.HOURS_MASTER.sum()),
                help="Master hours across every multi-load work order at these "
                     "steps — what the figure beside it is a share of.")

    # EVERY FIGURE IN THIS TEXT IS READ, NOT WRITTEN DOWN. It used to quote a
    # single-load ratio of 0.96 against a multi-load 0.57, and a marginal load
    # "from 0% to 156%". Every one of those had drifted, and the 0.96 carried
    # the clause "the standard is roughly right" - which, once the live ratio
    # crossed 1.0, was not merely stale but backwards. Hardcoding a figure next
    # to a tile that reads its own is how a page ends up arguing with itself.
    #
    # THE REPLACEMENT FIGURES ARE NOT WRITTEN DOWN HERE EITHER, for the same
    # reason: this comment quoted them once and they went stale too.
    f = data.multi_load_facts()
    # THE DIRECTION WORD IS DERIVED, NOT TYPED. "12% more" and "35% less" are
    # the point of saying it this way, and they are also exactly the clause
    # that went stale before: the page called the standard "roughly right"
    # long after the figure behind it had crossed 1.0. Read the sign off the
    # number and the sentence cannot contradict the table under it.
    _p1 = abs(f["RATIO_ONE"] - 1) * 100
    _w1 = "more" if f["RATIO_ONE"] >= 1 else "less"
    _p2 = abs(f["RATIO_MULTI"] - 1) * 100
    _w2 = "more" if f["RATIO_MULTI"] >= 1 else "less"
    st.markdown(f"""
`HRS/LOAD` charges `CEILING(quantity ÷ load size) × RUN`. A job of 510 pieces
against a load size of 500 is charged two full machine cycles. One-basket jobs
take about **{_p1:.0f}% {_w1}** time than the standard allows; jobs needing
several take about **{_p2:.0f}% {_w2}** (ratios of {f["RATIO_ONE"]:.3f} and
{f["RATIO_MULTI"]:.3f}). Correcting `RUN` cannot fix both at once, so multi-load
work orders are excluded from the test and reported here.
""")

    # The columns on screen, named - same pattern as the two sections above.
    #
    # PART GRAIN, NOT FAMILY. A family row could pool parts that basket
    # differently: one step showed "Loads, median 9 / max 14" because two
    # parts basket at 40 pieces and two at 25, and another pooled parts at
    # 0.33 h a basket with parts at 0.66. RUN_MASTER and LOAD_SIZE are
    # per-part routing fields, so at this grain every row carries exactly one
    # of each - 0 of 240 rows mix either - and both are read straight off the
    # part rather than averaged.
    #
    # THE STANDARD ITSELF IS ON THE ROW. One family's three steps at a single
    # operation used to look like the same finding at three sizes; HRS/LOAD
    # shows them as one standard at 12 h a basket, one at 5 and one at 2 - and
    # only the first two are too generous, the third runs OVER.
    # TWO COLUMNS DROPPED FROM SCREEN, kept in the CSV's raw work-order rows
    # (recomputable there from LOADS_CHARGED and HOURS_MASTER): Loads, max and
    # Avg master h/WO answer "how big is this job", not "why is it
    # over-charged".
    #
    # TOTAL ACTUAL H STAYS, unlike the first pass at this cut. Actual ÷ master
    # names both HOURS_MASTER and HOURS_WORKED in its own header - the same
    # reasoning 2_Inspect.py's evidence table gives for that header - so
    # hiding one of the two named columns broke the thing the header promises:
    # reading the formula off the row without a tooltip.
    _show3 = ["FAMILY", "PART_TYPE", "PART_ID", S, "OPERATION", "WORK_ORDERS",
              "RUN_EFF", "LOAD_SIZE", "MEDIAN_LOADS", "HOURS_WORKED",
              "OVER_RESERVED_HOURS", "HOURS_MASTER", "RATIO"]
    _t3 = d3[_show3].copy()
    _t3["PART_TYPE"] = _t3.PART_TYPE.map(
        lambda v: ui.part_tag(v, with_title=False))
    st.dataframe(ui.swiss_grid(
        # Every hour column at two decimals, ratio at three - the same split
        # the setups table uses. LOAD_SIZE and the load count are piece and
        # basket counts, not hours, so they stay whole numbers.
        _t3, {"WORK_ORDERS": ",.0f", "RUN_EFF": ",.2f", "LOAD_SIZE": ",.0f",
              "MEDIAN_LOADS": ",.0f", "HOURS_MASTER": ",.2f",
              "HOURS_WORKED": ",.2f",
              "OVER_RESERVED_HOURS": ",.2f", "RATIO": ",.3f"}),
        hide_index=True, width="stretch", height=380,
        column_config={
            "FAMILY": st.column_config.TextColumn("Family"),
            "PART_TYPE": st.column_config.TextColumn("Part type",
                                                     width="small"),
            S: st.column_config.NumberColumn("Step", format="%d"),
            # No width - sized to content, same as Family. Only 4 operations
            # appear on this page and their names run from 13 to 16
            # characters, so a fixed width was either cramped on the long
            # ones or wasted space on the short ones.
            "OPERATION": st.column_config.TextColumn("Operation"),
            "PART_ID": st.column_config.TextColumn("Part", width=130),
            # Sums to 557 rather than to the 258 in the tile above: a work
            # order at three sequences is three rows here and one there.
            "WORK_ORDERS": st.column_config.NumberColumn(
                "Work orders",
                help="Multi-load work orders for this part at this step. A "
                     "work order meeting the same operation at another "
                     "sequence is counted again on that row, so this column "
                     "sums to more than the figure above."),
            # HRS/LOAD IN FULL CAPS, not house-styled, because it is a value
            # the app never re-cases anywhere else - RUN_TYPE_MASTER holds it
            # verbatim, and 2_Inspect.py's own tab labels write "Run — PCS/HR"
            # / "Run — HRS/LOAD" rather than lowercasing it. Setup h and
            # Master h translate ERP FIELD NAMES into house style; this is an
            # ERP VALUE, treated the way every other appearance of it is.
            "RUN_EFF": st.column_config.NumberColumn(
                "HRS/LOAD", width=100,
                help="RUN as the routing holds it: hours for one load of "
                     "this part."),
            "LOAD_SIZE": st.column_config.NumberColumn(
                "Load size",
                help="Pieces of this part that fit in one basket - a "
                     "physical fact about the part and the machine, not a "
                     "measurement this analysis can move."),
            # STILL VARIES, even with one part per row: Load size is fixed
            # but the order quantity is not, so CEILING(quantity ÷ load size)
            # moves work order to work order for the same part - 39 of 240
            # parts see it vary, from 3 loads on a 65-piece order to 14 on a
            # 330-piece one at load size 25. Loads, max is in the CSV for
            # whoever wants the largest single order rather than the middle.
            "MEDIAN_LOADS": st.column_config.NumberColumn(
                "Loads median",
                help="Baskets charged per work order for this part - varies "
                     "with the order quantity, not with the part."),
            "HOURS_MASTER": st.column_config.NumberColumn("Total master h",
                                                          width=100),
            "HOURS_WORKED": st.column_config.NumberColumn("Total actual h",
                                                          width=100),
            "OVER_RESERVED_HOURS": st.column_config.NumberColumn(
                "Total unused h", width=100),
            "RATIO": st.column_config.NumberColumn("Actual ÷ master",
                                                   width=130),
        })
    st.download_button("Download as CSV",
                       d3r.to_csv(index=False).encode("utf-8"),
                       file_name="fts_additional_findings_multiple_loads.csv",
                       mime="text/csv",
                       icon=":material/download:", key="dl_gap")
    st.caption("The download is one row per work order rather than the "
               "summary above it, and carries the part, the quantity and the "
               "load size behind every line.")

    # THE FIT STAYS PER OPERATION, on its own below, and does not follow the
    # Family picker. It is one straight line through both regimes of a whole
    # operation, so there is no family-level version of it to show - repeated
    # down 96 rows it would read as 96 measurements rather than as four.
    #
    # DIVIDER + SUBHEADER, not a raw markdown heading - the pattern every
    # other secondary section in the app uses (2_Inspect.py three times,
    # 3_By_part.py once). A bare "#### " here was the one place that skipped
    # it, which is also why it read smaller than every other section title.
    st.divider()
    st.subheader("What a second load actually costs")
    # THE METHOD, STATED, not just one of its outputs named. This used to say
    # only what Fixed h was and left the fit itself unexplained.
    st.caption("Each row fits a line built through a regression:\n\n"
               "`worked hours = fixed amount (intercept) + per-basket "
               "amount (slope) × additional baskets`\n\n"
               "through every work order at that operation, single-load and "
               "multi-load together - filtered by the Operation picker only, "
               "not Family. `Fixed h` is what a single basket costs; the "
               "slope is added once for every basket after that.")
    # RUN H AND ACTUAL ÷ MASTER ADDED, so the two right-hand columns stop
    # asking to be trusted. RATIO was already sitting unused in 04_MultiLoadGap
    # - no new computation, just widening the column list. RUN itself is not
    # stored there, only the percentage against it, so it is read fresh from
    # the parquet rather than back-derived from two already-rounded sheet
    # columns, which would drift from what MARGINAL_AS_PCT_OF_RUN actually used.
    _fit = gap[gap.OPERATION.isin(op)] if op else gap
    _fit = _fit.merge(data.run_by_operation().rename("RUN_MEDIAN"),
                      on="OPERATION", how="left")
    # FIXED_HOURS_A, RECAST. 04_MultiLoadGap stores the raw regression
    # intercept - the line's value at ZERO baskets, which no work order ever
    # has, and which came out negative for S RICOTTURA (-0.69 h). Adding the
    # slope shifts the same line to read its value at ONE basket instead: an
    # algebraically exact rewrite (worked = a + b×loads = (a+b) +
    # b×(loads-1)), not a different fit. S RICOTTURA becomes 1.67 h - a real
    # basket cost instead of a math artifact needing its own footnote.
    _fit["ONE_BASKET_H"] = _fit.FIXED_HOURS_A + _fit.MARGINAL_LOAD_B
    st.dataframe(ui.swiss_grid(
        _fit[["OPERATION", "RUN_MEDIAN", "ONE_BASKET_H", "MARGINAL_LOAD_B",
              "MARGINAL_AS_PCT_OF_RUN", "RATIO"]],
        {"RUN_MEDIAN": ",.2f", "ONE_BASKET_H": ",.2f",
         "MARGINAL_LOAD_B": ",.2f", "MARGINAL_AS_PCT_OF_RUN": ",.1%",
         "RATIO": ",.3f"}),
        hide_index=True, width="stretch",
        column_config={
            # No width - sized to content, same as the table above it.
            "OPERATION": st.column_config.TextColumn("Operation"),
            "RUN_MEDIAN": st.column_config.NumberColumn(
                "HRS/LOAD median", width=140,
                help="Median RUN among this operation's multi-load parts - "
                     "what As % of HRS/LOAD median is measured against."),
            "ONE_BASKET_H": st.column_config.NumberColumn(
                "Fixed h (intercept + first basket)", width=270,
                help="What this line predicts the first basket costs - the "
                     "intercept, shifted from zero baskets to one."),
            "MARGINAL_LOAD_B": st.column_config.NumberColumn(
                "Per extra load h (slope = per additional basket)", width=310,
                help="What a second load actually costs in hours."),
            "MARGINAL_AS_PCT_OF_RUN": st.column_config.NumberColumn(
                "As % of HRS/LOAD median", width=190,
                help="Per extra load h against HRS/LOAD median beside it."),
            "RATIO": st.column_config.NumberColumn(
                "Actual ÷ master", width=130,
                help="Multi-load work orders only, for this operation: "
                     "actual hours over master hours."),
        })
