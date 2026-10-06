"""The queue: every standard proposed for change, narrowed to what you own.

Two things this does that a spreadsheet does not. Filters live in the left rail
so the table gets the whole width, and the totals follow the filter - so
"what is my family worth" is answered by the same control that finds it.

THE TABLE IS THE DECISION, THE DOWNLOAD IS THE RECORD. On screen every column
answers "what is being changed here and is it worth changing"; the CSV carries
all of 01_Actions, because a spreadsheet opened next week is where somebody
pivots on the confidence band or the level a pool was judged at, and a column
costs nothing in a file.
"""

import pathlib
import re
import sys

import pandas as pd
import streamlit as st

# parent.parent is streamlit_app/, where ftsapp lives. Every page inserts it
# itself rather than relying on Overview.py having run first: deep-link to a
# page in a fresh session and the import failed with ModuleNotFoundError:
# no module named 'ftsapp'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ftsapp import data, freshness, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="FTS · Review queue",
                   page_icon=":material/checklist:", layout="wide")
ui.inject()
st.title("Review queue")
# NO CAPTION UNDER THE TITLE. It said "one row per standard proposed for change",
# which three other things on the same screen already say: the banner below opens
# "Every standard HERE", the first tile counts "Standards to review", and the
# table has one row each. Title straight into the banner, the same shape
# Additional findings uses.
#
# It also carried "pick a row to open the evidence behind it", which is said
# again under the table - where a reader is actually looking at rows to pick.
freshness.guard()

# WHAT IS ABSENT, not what is present. The tiles and the columns below already
# say what a row is; nothing on the page said what never became one, and this is
# the page a reader lands on first from Overview.
#
# The misreading it exists to stop is that this list is everything wrong with the
# standards. It is everything the evidence could PROVE is wrong and is worth
# re-keying, which is a much smaller set.
#
# GREEN, and "act" rather than "caution", even though the sub-line is a caveat.
# The colour has one job in this tool and it is not tone: green means a rule was
# satisfied, and all six were, on every row here. Amber is spoken for - "do not
# act on this as it stands" - which is false of 230 of the 238 and would be a
# second meaning for the one colour the legend promises has only one.
#
# NO FIGURE IN IT, deliberately, and not only to keep it from going stale. There
# is no honest denominator to quote: EXAMINED counts one part at one step on the
# part route and one FAMILY at one step on the family route, so a summed
# "238 of N" would add two units together and report them as one. The tile below
# carries the 238 and follows the filter; this banner is true whatever is picked.
#
# THE TWO ABSENT OUTCOMES ARE NAMED IN THE APP'S OWN WORDS - "tested and held"
# and "not enough evidence" are data.py's two verdict strings, the ones
# Methodology prints in its Outcome column and By part quotes verbatim. A first
# draft of this line said "tested and found sound" and "never enough evidence to
# judge", which is a fourth and fifth phrasing of a distinction By part already
# carries a comment about having collapsed from three to two.
#
# Plain text, no markdown - verdict_banner escapes both halves, so asterisks
# would render as asterisks.
#
# NO IDIOM, AND NO BLANKET CLAIM. Two earlier drafts of this line failed
# differently and the second failure is the instructive one.
#
# "Absence is not a clean bill of health" was an English figure of speech in
# front of a room that does not read English figures of speech - decoration
# exactly where the sentence does its only real work.
#
# Its replacement, "missing from this list does not mean correct", was plain and
# WRONG, because it is true of only one of the two absent groups. A standard
# that was tested and held HAS been checked; one with not enough evidence never
# reached the test at all - 8'492 of the 9'120 units on the PCS/HR part route.
# Saying "missing does not mean correct" over both of them casts doubt on the
# first group and erases the distinction the very next clause points at.
#
# So the line names the two, and puts the warning only where it belongs: on the
# second.
#
# "(no change proposed)" GLOSSES THE VERDICT LABEL IN PLACE. "Held" is not
# ordinary English - it is a workbook verdict the reader meets again in
# Methodology's Outcome column and on By part - and an earlier draft left it to
# be recovered from the sentence after it. Said in the parenthesis, it is
# "(no change proposed)" IN THE PROSE, "Suggested" AS THE COLUMN HEADER, and
# they are not in conflict: the prose describes what the analysis DID - it
# proposed nothing for those units - while the header names WHERE THE NUMBER
# CAME FROM, which is the workbook's RM_SUGGESTED.
#
# The header read "Proposed" until 2026-08-27, on the argument that SUGGESTED
# and RECOMMENDED were two different workbook columns that disagreed, so
# borrowing either word would name the wrong one. They can no longer disagree:
# RM_RECOMMENDED IS RM_SUGGESTED on both routes since the family branch was
# corrected. The header now matches the column it displays.
#
# NOT "the standard is correct", which the gloss must not become. 183 of the
# units that tested and held ARE off the standard - they failed rule 5 or 6, the
# deviation and hours floors - so what they have in common is that no change was
# proposed, not that nothing is wrong.
#
# "Between the two" is not padding once the parenthesis is in: it puts "the
# first" back within reach of what it refers to.
#
# Plain text, no markdown - verdict_banner escapes both halves, so asterisks
# would render as asterisks.
ui.verdict_banner(
    st, "Every standard here passed all six rules", "act",
    "Two kinds of standard are not shown: tested and held (no change "
    "proposed), and not enough evidence to test. Between the two, only the "
    "first was actually checked. Inspect and By part tell them apart.")

acts = data.actions()
S = data.SEQ

# TWO COLUMNS DERIVED HERE, because 01_Actions states the action in its own
# schema rather than in the reader's.
#
# ANALYSIS replaces the two raw schema columns TARGET and RUN_TYPE, which a
# reader had to combine to know what a row was. It went through a wrong turn
# first: a "Field" column reading RUN (PCS/HR) / RUN (HRS/LOAD) / SETUP_HRS,
# which is not a field - RUN and SETUP_HRS are fields, and (PCS/HR) is a value of
# RUN_TYPE, so "RUN (PCS/HR)" names no column in any system.
#
# The analysis is the honest fact, it is what Overview and Methodology already
# show, and it loses nothing: both run analyses edit RUN and setup edits
# SETUP_HRS, so naming the analysis names the field. The tooltip says so.
#
# EFFECT drops the " the standard" DIRECTION repeats on all 238 rows - the column
# heading says it once. A plain string replace rather than a lookup, so a third
# direction added upstream passes through as itself instead of vanishing.
acts["ANALYSIS"] = [ui.analysis_name(t, r)
                    for t, r in zip(acts.TARGET, acts.RUN_TYPE)]
acts["EFFECT"] = acts.DIRECTION.astype(str).str.replace(
    " the standard", "", regex=False)
# STATUS, from 01_Actions' ACTION_STATUS (2026-10-06): whether today's master
# already holds the value proposed - see fts_update_list.action_progress. An
# action stays an action when it is done; this says so beside it. Blank on an
# update list written before the column existed.
if "ACTION_STATUS" not in acts.columns:
    acts["ACTION_STATUS"] = ""
acts["STATUS"] = acts.ACTION_STATUS.map(ui.status_name)


def applies_to(part_id, level):
    """PART_ID as a table cell rather than as a sentence.

    01_Actions writes a phrase in this column wherever the unit is judged on the
    family, and the longest of them - "every part of this family that performs
    the setup", 49 characters - was setting the width of the widest column on
    the page. It appears on the SETUP_HRS rows and nowhere else, so every
    character of it restates the Analysis column beside it.

    What the phrases actually carry, once Analysis and Parts are on the row, is
    one bit and one number: whole family or one part, and how many parts were
    left out of the pool. Both survive here; the setup wording does not, because
    Analysis already says Setup on precisely those rows.

    (This docstring said "the Field column" until 2026-08-27. That column was
    renamed to Analysis when Field turned out to name nothing - RUN and
    SETUP_HRS are fields, PCS/HR is a value of RUN_TYPE - and the rename did not
    reach here. It also quoted a row count, which went stale the next time the
    extract moved; the count is gone rather than refreshed.)

    ANYTHING UNRECOGNISED IS PASSED THROUGH UNCHANGED rather than flattened to
    the family phrase. A seventh wording added upstream would then be visibly
    itself - and visibly wide - instead of being silently reported as something
    it might not be. Same fallback rule as ui.part_tag.
    """
    if str(level).upper() == "PART":
        return str(part_id)
    n = re.search(r"except the (\d+)", str(part_id))
    if n:
        return f"{ui.WHOLE_INLINE} excl. {n.group(1)}"
    if re.match(r"(all|every) parts? of this family", str(part_id)):
        return ui.WHOLE_INLINE
    return str(part_id)

# ---- filters, in the rail ---------------------------------------------------
# "What to look at", the same heading Inspect and Additional findings put over
# their rails. This one said "Narrow it down", which is what it does and not what
# the other two call it.
with st.sidebar:
    ui.side_title(st, "What to look at")

    # FIRST IN THE RAIL, above the pickers it does not filter - the same place
    # Inspect puts "Only where a change is proposed". Both are the rail's
    # bigger fork: they decide the SHAPE of what follows rather than narrowing
    # it, so they read before the boxes that narrow it and not among them.
    #
    # It sat last, under the two filters, where it looked like a third filter.
    # NAMES THE COLUMN IT SORTS. It read "Biggest hours first" while the column
    # was called Hours; the column became Δ Hours on 2026-08-27 and this did not
    # follow.
    #
    # AND IT SORTS ON THE ABSOLUTE VALUE - d.HOURS_DELTA.abs() below - which the
    # label alone cannot convey. 110 of the 238 actions are negative, and the
    # largest gap in the whole list is -422 h, so "biggest" read as "largest
    # signed" puts the wrong row at the top of the reader's expectation. The
    # help says so with the case that proves it.
    # OFF BY DEFAULT. Left on, the queue opens scrambled relative to its own
    # leftmost columns: 01_Actions is sorted family, part type, level, part,
    # step, so untouched it groups every decision for one family together -
    # which is the set they will be applied as, and the order FAMILY /
    # PART_TYPE / OPERATION at the head of the table already promises. Sorting
    # by size breaks that grouping and is a question the reader should have to
    # ask ("what is worth most?"), not the one they are answered before asking.
    big_first = st.toggle(
        "Biggest Δ Hours first", value=False,
        help="By the SIZE of the gap, not its direction — a standard 400 "
             "hours under ranks above one 300 hours over. Both are equally "
             "wrong and equally worth fixing; the Effect column says which "
             "way each one goes.")


    def narrow(frame, label, col, placeholder, fmt=str, count=False):
        """One filter, offering only what the filters above it left standing.

        THE CASCADE IS THE POINT. Flat, Operation offered all 31 whatever family
        was chosen, and most of those combinations led to "Nothing matches those
        filters" by way of a valid-looking choice. Inspect and Additional
        findings both narrow their pickers this way already.

        Streamlit drops a selection whose option disappears, so widening a
        filter above cannot leave a stale value pinned below it.

        count=True puts how many options are on offer into the placeholder, and
        because the list is already narrowed by everything above it, that figure
        MOVES: Operation reads "all operations (31)" on an unfiltered rail and
        "all operations (4)" once a family is chosen. That is the cascade saying
        out loud what it did, without the reader having to open the box.
        """
        vals = sorted(frame[col].dropna().unique().tolist())
        if count:
            placeholder = f"{placeholder} ({len(vals)})"
        sel = st.multiselect(label, vals, placeholder=placeholder,
                             format_func=fmt)
        return frame[frame[col].isin(sel)] if sel else frame

    # Placeholders name what "no selection" means AND how much it covers. It
    # used to say only the count - "all (31)" - which is the half a reader can
    # get by opening the box, and left out the half they cannot: what the list
    # would show if they left it alone.
    #
    # THE COUNT IS ONLY ON THESE TWO. Part type, Analysis and Judged at offer two
    # or three options and their placeholders already enumerate the whole set,
    # so "both (2)" would be the box counting to two in front of the reader.
    d = narrow(acts, "Family", "FAMILY", "all families", count=True)
    d = narrow(d, "Operation", "OPERATION", "all operations", count=True)
    # ADV / ANDV in the picker and in the column, the same abbreviation the
    # Overview rankings and Inspect's subtitle use. "Articolo non di vendita" is
    # 23 characters carrying one bit and does not fit a sidebar.
    d = narrow(d, "Part type", "PART_TYPE", "both",
               lambda v: ui.part_tag(v, with_title=False))
    # ONE FILTER WHERE THERE WERE TWO. "Field it edits" offered RUN / SETUP_HRS
    # and "Run type" offered PCS/HR / HRS/LOAD / -, so the rail could be put into
    # states that cannot exist - setup and PCS/HR together. One analysis picker
    # can only ever offer the three combinations that do exist.
    d = narrow(d, "Analysis", "ANALYSIS", "all analyses")
    d = narrow(d, "Judged at", "LEVEL", "part and family", str.title)

    only_review = st.toggle(
        "Only flagged for manual review", value=False,
        help=f"Ratio outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI}. The "
             f"test is on the ratio, not the percentage change: a rate that "
             f"quadruples reads +300% but one cut to a quarter reads −75% and "
             f"can never pass −100%, so flagging on the change would catch "
             f"only increases.")

    # OFF BY DEFAULT, so the counts above the table keep matching Overview's
    # until somebody asks otherwise. Hides ALREADY done only: a partly done
    # decision still has parts to key, so it stays.
    hide_done = st.toggle(
        "Hide already done", value=False,
        help="Hides the decisions today's master already carries: every part "
             "holds a value within 10% of the one proposed. Partly done stays "
             "- some of its parts are still to key.")

if only_review:
    d = d[d.NEEDS_REVIEW]
if hide_done:
    d = d[d.STATUS != "already done"]
if big_first:
    d = d.reindex(d.HOURS_DELTA.abs().sort_values(ascending=False).index)

# ---- what the current filter is worth ---------------------------------------
# "Standards to review", the label Overview uses for the same 238, with the
# breakdown tooltip it carries too - both now following the filter. It read
# "Decisions shown", which was a third word for the row and hid the fact that
# this tile and Overview's leftmost one count exactly the same thing.
# THE THREE SHARED TILES KEEP OVERVIEW'S ORDER. Standards to review, then
# operations rows to edit, then absolute misstated hours - the same sequence,
# under the same labels, one click apart. They were second and third the other
# way round here, which is the kind of difference a reader does not consciously
# notice and does re-read.
#
# The page's own tile goes last rather than being slotted among them. Overview's
# fourth is "Distinct parts affected", which cannot be shown here: on the 167
# family-level rows PART_ID holds a sentence - "all parts of this family" - so
# 01_Actions alone has no part numbers to count distinct. "Need a human first"
# takes the slot because it is what this page adds: it pairs with the rail's
# toggle and the Check? column, neither of which Overview has.
m = st.columns(4)
m[0].metric("Standards to review", ui.num(len(d)),
            delta=f"of {ui.num(len(acts))}" if len(d) != len(acts) else None,
            # NOT the inline-delta container Inspect uses. See ui.py: this
            # delta is a denominator, not a qualifier on the value, so it
            # belongs under the count rather than beside it.
            delta_color="off",
            # Counted off TARGET/RUN_TYPE, not off the derived display column.
            # Comparing against display strings meant this silently returned
            # zero for both run analyses the moment that column's wording
            # changed - which it then did twice.
            help=f"{int(((d.TARGET == 'RUN') & (d.RUN_TYPE == 'PCS/HR')).sum())}"
                 f" run PCS/HR, "
                 f"{int(((d.TARGET == 'RUN') & (d.RUN_TYPE == 'HRS/LOAD')).sum())}"
                 f" run HRS/LOAD, "
                 f"{int((d.TARGET == 'SETUP_HRS').sum())} setup.")
# N_PARTS summed is a count of FIELD EDITS, not of parts: a part is edited once
# per operation it runs, so summing it across actions counts the same part
# several times. It sat one click from Home's distinct-part count under a
# near-identical label, reading as a contradiction.
m[1].metric("Operations rows to edit", ui.num(d.N_PARTS.sum()),
            help=text.ROWS_TO_EDIT_HELP)
m[2].metric("Absolute misstated hours", ui.hrs(d.HOURS_DELTA.abs().sum()),
            help=text.ABSOLUTE_MISSTATED_HELP)
# "Flagged for manual review", following How to read it, whose section on this
# state is headed "Flagged for review" - and matching the workbook, which writes
# NEEDS REVIEW into a column called REVIEW_FLAG. It read "Need a human first"
# here, "Only the ones needing a human" in the rail and "Check?" on the column:
# three names for one state, on one page.
#
# "MANUAL" IS NOT PADDING. Plain "Flagged for review" collides on this page and
# nowhere else - the page is the Review queue and the first tile counts
# "Standards to review", so a reader meets "flagged for review" and reasonably
# asks how it differs from the other 230. Manual is the difference: the six rules
# cleared those automatically, these want a person.
m[3].metric("Flagged for manual review", ui.num(d.NEEDS_REVIEW.sum()),
            help=f"Ratio outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI}. "
                 f"These passed all six rules, but the change is large enough "
                 f"that a person should check it before it is keyed in.")

if d.empty:
    st.info("Nothing matches those filters.", icon=":material/filter_alt_off:")
    st.stop()

detail = st.toggle("Show the statistics columns", value=False,
                   help="The ratio and its 95% band. Hidden by default to keep "
                        "the decision columns easy to read. The download "
                        "always carries them.")

# WHICH STANDARD, then WHAT TO DO, then HOW MUCH IT IS WORTH. Three groups, read
# left to right, and the middle one is the page's whole purpose - it used to be
# two raw schema columns (TARGET, RUN_TYPE) with the plain-English direction
# hidden behind the toggle.
#
# TWO COLUMNS DROPPED FROM THE SCREEN and kept in the download. LEVEL said
# PART / FAMILY beside an "Applies to" column already saying "all parts of this
# family" or a part number, in words; RUN_TYPE is now inside Analysis, which
# reads Run PCS/HR / Run HRS/LOAD / Setup and so carries both facts in one
# column.
# ---- COLUMN ORDER, settled 2026-08-27 --------------------------------------
# Reads left to right as the reviewer's own sequence:
#
#   WHICH ROUTING ROW   Family, Part type, Operation, Step
#   WHAT KIND           Analysis
#   HOW WIDE, HOW BIG   Applies to, Parts, Work orders, Δ Hours
#   WHAT TO DO          Now, Suggested, Effect, Change %
#
# APPLIES TO SITS BESIDE PARTS because they are ONE FACT AT TWO GRAINS, and the
# data makes that exact: where Applies to is a part number, Parts is 1 on all 70
# such rows without exception; where it says "whole family", Parts runs 2 to 73.
# Read together they explain each other - "whole family · 73", or one part
# number against a 1.
# Seven columns apart, which is where Applies to sat until 2026-08-27, "Parts: 1"
# is a bare number the reader has to decode by remembering the rule.
#
# The cost, accepted: Applies to is the second-widest column at 20 characters,
# so moving it left leaves less room for the identity columns that get scanned
# most. It does not change the total width - the grid fits its columns to the
# space either way - so this trades a little truncation on the left for a pair
# that reads on sight.
#
# Δ HOURS SITS WITH THE MAGNITUDE BLOCK, not at the far right, because it is
# the SORT KEY the rail toggle reaches for. It is off by default, but the moment
# it goes on the column driving the order has to be visible without scanning to
# the end of the row.
#
# EFFECT COMES BEFORE CHANGE %, AND AFTER BOTH VALUES. The sign of Change %
# means OPPOSITE THINGS by analysis: a PCS/HR rate falling 11.7% SLOWS the
# standard down (+324 h on one row), while a setup duration falling 72% SPEEDS
# it up (-5 h). Both print a minus.
#
# Effect used to sit AFTER Change %, where it corrected the misreading. Ahead of
# it, the reader meets "slow down" and only then the -11.7% - primed rather than
# corrected, and a wrong impression is harder to undo than to prevent.
#
# It was briefly BETWEEN Now and Suggested, reading as the arrow in
# "3.00 -> slow down -> 2.65". That put a word column between two number columns
# and broke the numeric run for no gain: Effect precedes Change % either way, so
# the priming works from here too and Now/Suggested stay adjacent, which is the
# comparison a reader actually makes.
#
# Effect is strictly redundant with the SIGN of Δ Hours - they agree on all 238
# rows, checked - but Δ Hours is a quantity three columns away, not a direction
# at the point of confusion. The redundancy is the feature.
#
# NEEDS_REVIEW IS NOT HERE. It was False on 230 of 238 rows; the rail toggle,
# the tile and ui.review_warning on the detail card all still carry it.
#
# STATUS LAST, after Change %: the decision first, then whether the ERP already
# carries it. It qualifies the whole WHAT TO DO block rather than any one value
# in it, and at the end it never splits the Now / Suggested comparison.
base = ["FAMILY", "PART_TYPE", "OPERATION", S, "ANALYSIS",
        "PART_ID", "N_PARTS", "N_WO", "HOURS_DELTA",
        "CURRENT_VALUE", "TO_KEY", "EFFECT", "TO_KEY_CHANGE_PCT", "STATUS"]
extra = ["RATIO", "CI95_LOW_PER_WO", "CI95_HIGH_PER_WO"]
cols = base + (extra if detail else [])

show = d[cols].copy()
show["PART_TYPE"] = show.PART_TYPE.map(
    lambda v: ui.part_tag(v, with_title=False))
# Mapped on the display frame, not on `acts`, so the download keeps the
# workbook's own PART_ID text - the same split the PART_TYPE line above makes.
show["PART_ID"] = [applies_to(p, lv) for p, lv in zip(d.PART_ID, d.LEVEL)]

event = st.dataframe(
    # Both signed figures carry their sign, the same way Overview's Net column
    # does: a change and a delta printed bare read as totals.
    ui.swiss_grid(show, {"N_WO": ",.0f", "N_PARTS": ",.0f",
                         "CURRENT_VALUE": ",.2f", "TO_KEY": ",.2f",
                         "TO_KEY_CHANGE_PCT": "+,.1f",
                         "HOURS_DELTA": "+,.0f",
                         "RATIO": ",.3f", "CI95_LOW_PER_WO": ",.3f",
                         "CI95_HIGH_PER_WO": ",.3f"}),
    hide_index=True, width="stretch", height=430,
    on_select="rerun", selection_mode="single-row",
    # EVERY COLUMN NAMED. Four of them - OPERATION, RUN_TYPE, N_PARTS and
    # DIRECTION - used to fall through this dict and render their raw database
    # name to a reader who has no schema.
    column_config={
        # NO FIXED WIDTHS ON ANY COLUMN (user, 2026-10-06): every column is
        # auto-sized, as the starting point for deciding the table's widths
        # column by column. Family, Part type, Applies to and Status each had
        # one until then. Set since, in pixels, by the user: Part type 60,
        # Step, Parts, Δ Hours and Now 55; Family "medium" put back as it was;
        # Applies to and Status 125.
        "FAMILY": st.column_config.TextColumn("Family", width="medium"),
        "PART_TYPE": st.column_config.TextColumn(
            "Part type", width=60,
            help="ADV finished, ANDV semi-finished. Both are analysed, never "
                 "in the same pool — same family, different physical job."),
        # No width - sized to content, same as Family, and the same treatment
        # Additional findings gives its operation columns.
        "OPERATION": st.column_config.TextColumn("Operation"),
        S: st.column_config.NumberColumn("Step", format="%d", width=55),
        "PART_ID": st.column_config.TextColumn(
            "Applies to", width=125,
            help="A part number, where the part had enough work orders to be "
                 "judged on its own. Otherwise the whole family, and how many "
                 "of its parts were flagged on their own and so left out of "
                 "the pool. The download carries the workbook's own wording."),
        # WHICH ANALYSIS, which also says which field - see ui.analysis_name.
        # The help is the one thing that must not be got backwards, so it states
        # both directions rather than leaving the reader to infer the second
        # from the first.
        "ANALYSIS": st.column_config.TextColumn(
            "Analysis",
            help="The three analyses, never pooled with each other. Both run "
                 "analyses edit the ERP's RUN column and setup edits "
                 "SETUP_HRS. Under PCS/HR that value is a rate in pieces per "
                 "hour, so the correction divides; the other two are "
                 "durations, so the correction multiplies."),
        # "Effect", not "Effect on the standard". The header was 22 characters
        # over a column whose widest value is 9, and a dataframe column is as
        # wide as the longer of the two - so the full phrase was buying nothing
        # and costing the width of a real column. The tooltip says what the
        # effect is on.
        "EFFECT": st.column_config.TextColumn(
            "Effect",
            help="What the change does to the time the standard allows, which "
                 "is not the direction the field's own number moves. Slowing "
                 "down a PCS/HR standard means a lower rate."),
        # No `format` on these: the Styler above owns the display, and a
        # NumberColumn format would override it and put the commas back.
        "CURRENT_VALUE": st.column_config.NumberColumn("Now", width=55),
        # RM_RECOMMENDED from the execution sheets, which is what a reviewer
        # actually keys. Since 2026-08-27 it equals 01_Actions' SUGGESTED_VALUE
        # on EVERY row, part and family alike - RM_RECOMMENDED is RM_SUGGESTED
        # on both routes - so this is a consistency check, not a correction.
        # The part branch was corrected on the 26th and the family branch on
        # the 27th; see data.actions and fts_update_list for why.
        "TO_KEY": st.column_config.NumberColumn(
            "Suggested",
            help="The value to key, as the execution sheets carry it. A part "
                 "judged on its own evidence keeps its own figure; the family "
                 "value applies to the parts that could not be judged alone. "
                 "Blank where the family runs several different current "
                 "values: there is no single number to key, and the "
                 "instruction is to divide each part's own value by the "
                 "ratio."),
        "TO_KEY_CHANGE_PCT": st.column_config.NumberColumn(
            "Change %",
            help="How much the field's own number changes, which is not how "
                 "the hours change. A PCS/HR rate that falls by 70% means the "
                 "standard allows more time, not less. The Effect on the "
                 "standard column says which direction."),
        "STATUS": st.column_config.TextColumn(
            "Status", width=125,
            help="Whether today's master already holds the value proposed. "
                 "Already done: every part is within 10% of it. Partly done: "
                 "some parts are, the rest are still to key — By part shows "
                 "which. To key: none is. Now is what the work orders ran "
                 "with, not necessarily what the master holds today."),
        "N_PARTS": st.column_config.NumberColumn(
            "Parts", width=55,
            help="How many parts this one decision covers. Each needs the "
                 "value keyed against its own routing row, so adding this "
                 "column up gives the operations rows to edit above."),
        # "Hours", with the window in the tooltip. It read "Hours a year", which
        # was wrong - the window opens at FY_START and never closes, so it is
        # the fiscal year TO DATE, about ten months today, and "a year" invited
        # reading a part-year total as an annual one. Inspect's metric fixed
        # that by saying "Hours since FY26 start" and this column copied it,
        # which is right for a metric label and 22 characters over a column
        # whose widest value is 7.
        #
        # A bare "Hours" makes no claim about the period, so it cannot be wrong
        # the way "a year" was; and the fiscal window is a fact about the whole
        # page rather than about this column.
        #
        # THE DELTA SIGN IS IN THE HEADER, added 2026-08-27. A bare "Hours"
        # reads as a TOTAL - "+324" under it invites "324 hours of work" rather
        # than "324 hours MORE than the standard allows". The sign on the value
        # was doing that job alone and it is not enough, because a signed total
        # is also a perfectly ordinary thing.
        #
        # SAME HEADER ON By part, which called this "Δ h". Three names for one
        # column across three surfaces was the actual problem; the symbol is
        # the smaller half of the fix. Inspect keeps a metric label rather than
        # a header - it has room to name the window, and the slower/faster word
        # under the figure says which direction without a symbol.
        "HOURS_DELTA": st.column_config.NumberColumn(
            "Δ Hours", width=55,
            # LEADS WITH THE PERIOD, because the header now carries the rest.
            # It opened "Actual minus master for this standard", which the Δ
            # says in one character - so the tooltip spent its first line
            # restating the header and its last line on the one thing nobody
            # can infer: how far back this runs. Reversed.
            help=f"From the start of {pipeline.FY_LABEL} to the last booking "
                 f"in the extract — a running total, not a rate, and it keeps "
                 f"growing while the standard stays wrong. Positive means the "
                 f"jobs take longer than the master allows."),
        "N_WO": st.column_config.NumberColumn(
            "Work orders",
            help="How many work orders the figure is based on."),
        # NEEDS_REVIEW IS NOT A COLUMN HERE. It is False on 230 of the 238 rows,
        # so as a checkbox column it carried almost no information per row while
        # costing a column of width. The state is reachable three other ways:
        # the rail's "Only flagged for manual review" toggle, the tile that
        # counts them, and - the one that matters - ui.review_warning on the
        # detail card, which fires when a flagged row is CLICKED, before anyone
        # keys anything. It is still in the CSV.
        "RATIO": st.column_config.NumberColumn(
            "Ratio", help="Actual hours divided by master hours, across the "
                          "work orders that counted."),
        # "Band", the word Inspect's own result table uses for this pair.
        "CI95_LOW_PER_WO": st.column_config.NumberColumn(
            "Band low", help="Low end of the 95% range for the ratio."),
        "CI95_HIGH_PER_WO": st.column_config.NumberColumn(
            "Band high", help="High end of the 95% range for the ratio."),
    })

# COUNTED, NOT WRITTEN DOWN, and only said when there is something to say - the
# same shape as the "not on the chart" caption on Inspect. These rows show three
# dashes where every other row shows figures, and without this the reader has to
# click one to find out that is deliberate.
# NOW AND SUGGESTED ARE BLANK ON THESE, CHANGE % IS NOT - and the caption has
# to say which, or the reader sees three dashes and assumes the row is empty.
#
# The percentage is well defined even where the absolute values are not: every
# part in the family is corrected by the same ratio, so they all move by the
# same proportion from different starting points. data.actions derives it from
# RATIO on exactly these rows.
#
# IT DOES NOT TELL ANYONE TO KEY OFF THE PERCENTAGE. That figure is rounded to
# one decimal; the workbook's instruction divides by the unrounded ratio, and
# the detail card prints it with the ratio substituted in. The percentage is
# here to size the change, not to be arithmetic.
_no_value = int(d.TO_KEY.isna().sum())
_note = ""
if _no_value:
    # TWO CLAUSES EARN THEIR KEEP AND THE REST WAS TRIMMED, 2026-08-27:
    # naming *Now* and *Suggested* is what connects the sentence to the dashes
    # the reader can see, and "every part moves by the same proportion" is why
    # a Change % on a row with no other numbers is trustworthy rather than a
    # leftover. Without that second clause it reads as a bare assertion.
    _note = (f"**{_no_value} rows** show no *Now* or *Suggested* — their family "
             f"runs several current values, so there is no single number to "
             f"key. *Change %* still holds: every part moves by the same "
             f"proportion. ")

# WHY PROPOSED IS NOT WHAT THIS PART MEASURED, on the rows where it is not.
# These are judged at PART level - the rail says a part number, not the family -
# so nothing else on the row hints that the value came from the family pool, and
# a reader who notices the gap has every reason to read it as a display fault.
# Counted, never written down, and silent on the other rows.
# AN INTEGRITY CHECK, NOT AN EXPLANATION - and it used to be the opposite.
# Until 2026-08-26 a rule in fts_update_list overrode a part's own figure
# with its family's on 17 rows, and this caption explained why. The rule was
# removed: a part that clears the six rules on its own evidence keeps its own
# value, on all three analyses.
#
# So this block now fires only if that guarantee has broken, and it says so
# instead of explaining it away. Do NOT restore the old wording if it ever
# appears - it would present the removed rule as if it were current.
_from_fam = d[(d.SUGGESTED_VALUE - d.TO_KEY).abs() > 0.101]
if len(_from_fam):
    st.warning(
        f"**{len(_from_fam)} row(s) propose a value that is not the part's "
        f"own measurement.** Every part here cleared all six rules on its own "
        f"evidence, so the two should match. They do not, which means the "
        f"workbook and this page disagree about what to key. Check "
        f"`02_RunUpdateList` before keying these, and report it. The workbook "
        f"records the basis as *{_from_fam.TO_KEY_BASIS.iloc[0]}*.",
        icon=":material/error:")

rows = event.selection["rows"] if event and event.selection else []
if rows:
    r = d.iloc[rows[0]]
    st.session_state["unit"] = {
        "TARGET": r.TARGET, "RUN_TYPE": r.RUN_TYPE, "OPERATION": r.OPERATION,
        "FAMILY": r.FAMILY, "PART_TYPE": r.PART_TYPE, "SEQ": int(r[S]),
        "LEVEL": r.LEVEL,
        "PART_ID": r.PART_ID if r.LEVEL == "PART" else None,
    }
    # THE WORKBOOK'S INSTRUCTION WITH THE NUMBER IN IT. HOW_TO_APPLY names the
    # column beside it - "set RUN_MASTER to SUGGESTED_VALUE" - which is right in
    # a spreadsheet where that column is on the row, and one indirection too many
    # here, where the value is on screen and the reader is about to key it. The
    # two placeholders are mutually exclusive: the rows carrying no single
    # value are exactly the ones whose instruction names RATIO instead.
    # ui.keying_instruction, the same rendering "How to read it" gives these six
    # strings - so the instruction a reader is taught there and the one they act
    # on here name the RUN field the same way.
    _apply = ui.keying_instruction(r.HOW_TO_APPLY)
    if pd.notna(r.TO_KEY):
        _apply = _apply.replace("SUGGESTED_VALUE", ui.fmt(r.TO_KEY))
    if pd.notna(r.RATIO):
        _apply = _apply.replace("RATIO", ui.fmt(r.RATIO, ".3f"))
    with st.container(border=True):
        # The identity line in the order Inspect's subtitle uses - what it is,
        # then where - so the row you clicked and the page it opens name the
        # unit the same way. It said "FAMILY · OPERATION · seq N", which left out
        # the part type and the part, and called the step a third thing.
        st.markdown(
            f"**{r.FAMILY}** · {ui.part_tag(r.PART_TYPE)} · "
            f"{applies_to(r.PART_ID, r.LEVEL)} · "
            f"{r.OPERATION} · routing step {int(r[S])}",
            unsafe_allow_html=True)
        st.markdown(
            f"**Do this:** {_apply}"
            + (f" (it is {ui.fmt(r.CURRENT_VALUE)} now)"
               if pd.notna(r.CURRENT_VALUE) else "") + ".")
        # WHAT TODAY'S MASTER SAYS, only when it changes what to do. Inspect
        # carries the full picture - moved values, the check against today -
        # one click below.
        if r.STATUS == "already done":
            st.info("**Already done in today's master** — every part already "
                    "holds a value within 10% of this. Nothing left to key.",
                    icon=":material/task_alt:")
        elif r.STATUS.startswith("partly done"):
            _p = re.match(r"partly done \((\d+) of (\d+)\)", r.STATUS)
            st.info(f"**Partly done** — {_p.group(1)} of {_p.group(2)} parts "
                    f"already hold a value within 10% of this in today's "
                    f"master; the rest are still to key. The master row "
                    f"updater below marks each.", icon=":material/task_alt:")
        # Caption, matching Inspect: the same sentence should not be body text
        # on one page and a note on the next.
        st.caption(ui.direction_note(r.TARGET, r.RUN_TYPE))
        # The same banner Inspect raises on the same condition. This page is
        # where somebody first meets an extreme row, and it used to hand them
        # the instruction with nothing suggesting a second look.
        if bool(r.NEEDS_REVIEW):
            ui.review_warning(st, r.CURRENT_VALUE, r.TO_KEY, r.RATIO,
                              pipeline.REVIEW_LO, pipeline.REVIEW_HI)
        st.page_link("pages/2_Inspect.py",
                     label="Open the evidence behind this",
                     icon=":material/query_stats:")
else:
    # ONE CAPTION, NOT TWO. The blank-value note and the click affordance used
    # to be separate st.caption calls with nothing between them on first load -
    # two elements, two blocks of vertical space, and both ending in "click".
    # Joined into one paragraph: the note explains why those rows are empty,
    # the tail says what clicking does, and there is no gap between them.
    #
    # _note is "" when no row lacks a value, so the affordance still renders on
    # its own rather than disappearing with the thing it was appended to.
    #
    # "Carry it into Inspect" was both a figure of speech and, since the row
    # card grew, no longer the whole truth - clicking now shows the instruction
    # here as well as offering the link. Says what happens, in plain words.
    st.caption(_note + "Click any row for the instruction and the evidence.")

# THE DOWNLOAD CARRIES MORE THAN THE SCREEN, the same break Inspect makes. It
# used to export exactly the visible columns, so the toggle above silently
# decided whether the file had a confidence interval in it.
#
# The two derived columns are the only things left out, and both because the
# file already holds what they were made from: EFFECT is DIRECTION with three
# words removed, ANALYSIS is TARGET and RUN_TYPE glued together. A spreadsheet
# is where somebody pivots, and pivoting wants the two source columns.
#
# STATUS joins them for the same reason: it is ACTION_STATUS shortened, and
# ACTION_STATUS (with N_PARTS_ALREADY_DONE) is already in the file.
_dl = d.drop(columns=["EFFECT", "ANALYSIS", "STATUS"])
st.download_button(
    "Download this view as CSV", _dl.to_csv(index=False).encode("utf-8"),
    file_name="fts_review_queue.csv", mime="text/csv",
    icon=":material/download:")
# NAMES WHAT YOU GET AND WHY, the shape Inspect's download caption uses. It
# used to open "carries every column of `01_Actions`" - a sheet name from a
# workbook the reader may never have opened, and a promise that says nothing
# about whether the file is worth downloading. Twelve of the twenty-one columns
# are not on screen; these are the ones somebody would actually go looking for.
#
# NEEDS_REVIEW IS NAMED FIRST because it is the only one that was a COLUMN here
# until 2026-08-27. Anyone who used it and finds it gone needs to know where it
# went, and the rail toggle only filters - it does not export.
st.caption("The download adds the flag for manual review, the ratio and its "
           "confidence band, whether each pool was judged at part or family "
           "level, and the workbook's own keying instruction — twelve columns "
           "the table leaves out, and the ones worth having when the file is "
           "the thing being worked from rather than the screen.")

# ---- SQL master updater -----------------------------------------------------
# ITS OWN SECTION SINCE 2026-09-01. It arrived as a second download button under
# the first one's caption, where it read as a variant of that file - a checkbox
# somebody forgot to add. It is not a variant: the file above is for READING and
# this one is for WRITING, into the ERP, and a heading is the cheapest way to
# stop the second from being clicked in the belief it is the first.
#
# THE DIVIDER AND THE HEADING DO THE SAME WORK the two headings on By part do:
# they say the thing below is a different kind of thing, not more of the thing
# above.
st.divider()
st.subheader("SQL master updater")
# ST.CAPTION, NOT ST.MARKDOWN. Every other explanation sitting under a heading
# in this tool is in the small grey - By part's two sections, the note under
# the table above. In body text this paragraph read as page content rather than
# as the heading's explanation, and it was the only one on any screen that did.
st.caption(
    "The file above is one row per **decision** — the right shape for reviewing "
    "and the wrong one for keying, because a single family decision can cover "
    "dozens of parts and each needs the value entered against its own routing "
    "row. This one is one row per **routing row**: every part a decision "
    "covers, with that part's own current and suggested value, the "
    "`MASTER_OPS_ROWID` it is keyed against, and a ready-made `UPDATE` "
    "statement for it. `TODAY` and `TODAY_STATUS` say what that row holds "
    "in today's master and whether the suggestion is already in it; rows "
    "marked *already done* carry no statement, since there is nothing left "
    "to key on them.\n\n"
    "The statement is a **spreadsheet formula**, not finished text — it reads "
    "the Suggested cell beside it, so correcting a value in the sheet corrects "
    "the statement with it. Nothing here runs anything: it produces the SQL and "
    "leaves running it to a person who has read it.")

# ADDED 2026-09-01. The file above is one row per DECISION, which is the
# right shape for reviewing and the wrong one for keying: a family decision is
# one line covering up to 73 parts, and each of those parts needs the value
# entered against its own routing row.
#
# This explodes each row into the parts it covers - see data.actions_by_part
# for why the join has to be level-aware. Applies to is left exactly as the
# screen shows it, so a reader can still see at a glance that these ten rows
# came from one family decision; PART_ID beside it says which part each is.
#
# NOW AND SUGGESTED COME FROM THE PART, not from the decision. On the 20 rows
# where a family runs several current values the decision has no single figure
# to give and the table above shows dashes; here each part carries its own,
# which is the entire reason for wanting this file.
#
# NO CHANGE %, dropped 2026-09-01 as confusing, and it was: it can mean the
# move in the FIELD or the move in the HOURS, and those go opposite ways on a
# PCS/HR rate. The two figures either side of it - Now and Suggested - are what
# gets keyed, and Effect says which way the standard moves. There was a second
# trap in it too: the screen's Change % comes from the unrounded ratio and a
# per-part one from the rounded values, so they disagreed on 420 rows by up to
# 0.5pp. Nothing to reconcile now.
_by_part = data.actions_by_part(d)
# MASTER_OPS_ROWID LEADS. It is the thing each line is keyed against, and
# every other column exists to say what to put in it and why - so it reads
# first, the way an id does. int64 with no nulls on all 2'468 rows, and
# ROWID_FOUND is true on every one of them.
#
# It is not unique down the column and should not be: 28 routing rows carry
# both a RUN and a SETUP_HRS edit, which are two FIELDS of one ERP line rather
# than two opinions about one field. Checked - no routing row is written twice
# for the same field, so (rowid, analysis) identifies a line exactly.
#
# RATIO SITS BETWEEN SUGGESTED AND EFFECT, the same place By part puts it: the
# measured number, then the word that says which way it points. From the
# decision, not the part row - the two agree to 0.0005, the execution sheet's
# rounding, and the decision carries the unrounded one.
# HOW_TO_APPLY LAST, because it is a sentence: six wordings, up to 83
# characters, and putting it among the numbers would push them off the screen
# in any spreadsheet. It is the workbook's own instruction, exported as the
# workbook writes it and not reworded here.
#
# ON ONE OF THE SIX IT IS ALREADY DONE. "family holds several RUN_MASTER
# values - divide each part's own RUN_MASTER by RATIO" is the instruction for
# the rows the screen shows dashes on - and dividing is exactly what this file
# has carried out: NOW is that part's own value and SUGGESTED is the result.
# Read as an instruction it asks for arithmetic already in the row beside it;
# read as a description of where SUGGESTED came from, it is exact. Kept rather
# than reworded, because the other file and the workbook both say it this way.
# TARGET rides along unrendered - it is dropped again once the statement
# below is built. It is the ERP COLUMN NAME, "RUN" or "SETUP_HRS", which is
# exactly what that statement has to name.
#
# TODAY AND TODAY_STATUS, after EFFECT (2026-10-06): this routing row's value
# in today's master, and whether the suggestion is already in it - so whoever
# keys from this file can skip the rows that are done. NOW stays what the work
# orders ran with. On a row already done the statement is left empty (user,
# 2026-10-06) - see SQL_UPDATE below; the row itself stays in the file.
#
# THE PART BEFORE THE STEP (user, 2026-10-06): routing row, family, part number,
# what the part is, part type - then operation, step and the rest as before.
# PART_DESCRIPTION is the extract's, through data.part_index - the same line By
# part shows under its title.
_cols = ["MASTER_OPS_ROWID", "FAMILY", "PART_ID", "PART_DESCRIPTION",
         "PART_TYPE", "OPERATION", S, "ANALYSIS", "APPLIES_TO",
         "CURRENT", "RECOMMENDED", "RATIO", "EFFECT",
         "STANDARD_TODAY", "TODAY_STATUS", "HOW_TO_APPLY", "TARGET"]
_by_part["PART_DESCRIPTION"] = _by_part.PART_ID.map(
    data.part_index().set_index("PART_ID").PART_DESCRIPTION)
_RENAME = {"CURRENT": "NOW", "RECOMMENDED": "SUGGESTED",
           "STANDARD_TODAY": "TODAY"}
_by_part["APPLIES_TO"] = [applies_to(p, lv)
                          for p, lv in zip(_by_part.PART_ID_DECISION,
                                           _by_part.LEVEL)]
_by_part["TODAY_STATUS"] = _by_part.TODAY_STATUS.map(ui.status_name)
_by_part = _by_part[_cols].rename(columns={S: "STEP", **_RENAME})
# BY THE WORK, NOT BY THE PART. Family and part type first, then the routing
# step - so every part going through one step sits in a single block, which is
# how the change actually gets keyed: one step at a time, down the list of
# parts that share it. Sorting by part first scattered each step across the
# file.
#
# STEP BEFORE OPERATION. The step number is the routing sequence, so ordering
# on it walks the part through its process in the order the work happens;
# operation is the name of what is done at that step and only breaks ties.
# Sorting on the name first put the process in alphabetical order, which is no
# order at all.
#
# ANALYSIS DESCENDING PUTS SETUP FIRST, before the run at the same step, which
# is the order the shop floor does them in. It works because "Setup" sorts
# after "Run ..." alphabetically, and descending then also leaves Run PCS/HR
# ahead of Run HRS/LOAD. That is the alphabet doing what is wanted rather than
# an order stated outright - if ui.analysis_name is ever reworded, check this
# still comes out setup-first.
#
# APPLIES TO BEFORE PART ID separates the two kinds of row within a step: the
# parts judged on their own evidence, then the block covered by one family
# decision. Part numbers sort ahead of "whole family" because they are
# uppercase.
_by_part = _by_part.sort_values(
    ["FAMILY", "PART_TYPE", "STEP", "OPERATION", "ANALYSIS", "APPLIES_TO",
     "PART_ID"],
    ascending=[True, True, True, True, False, True, True])

# THE APP'S OWN PRECISION, carried into the file: two decimals on the two
# values, three on the ratio - the same as every table on every screen. Rounded
# as NUMBERS rather than formatted as text, so a spreadsheet still treats them
# as numbers and nothing has to be converted back before it can be summed.
#
# WHAT THIS CHANGES, measured rather than assumed.
#
# RATIO: nothing. All 2'468 are already at three decimals.
#
# SUGGESTED: 154 values, by at most 0.15%, and every one an HRS/LOAD row. That
# analysis is the only one writing three decimals - setup and run PCS/HR are
# already at two, setup because fts_setup_view rounds them on the way out. The
# ERP field takes two, so 5.926 was never keyable as written and whoever keyed
# it was rounding by hand; this rounds it the same way every screen already
# does.
#
# NOW: 12 values, none by more than 0.02%, and all of them setup. These are NOT
# float noise, which is what this comment said until it was checked: the stored
# value is exactly 0.5001 on 114 setup units and 0.9999 on one more, repeated
# to the digit, so it is data somebody entered rather than a representation
# artefact. Rounding it to 0.50 matches every screen in this tool and the two
# decimals that get keyed - but it does mean NOW reads 0.50 where the master
# holds 0.5001. It is a display of the current value, not a figure anybody
# keys, so the consistency is worth more than the fourth decimal.
_by_part = _by_part.round({"NOW": 2, "SUGGESTED": 2, "TODAY": 2, "RATIO": 3})

# ---- the statement, as a live spreadsheet formula ---------------------------
# NOT THE FINISHED TEXT. This wrote the statement out fully rendered until
# 2026-09-01; it now writes the formula that BUILDS it, so the cell recomputes
# when somebody edits the value beside it. Editing Suggested and having the
# statement still carry the old number is the failure this avoids.
#
# BRANCHED ON TARGET, NOT ON ANALYSIS. Analysis is a display string built by
# ui.analysis_name, and this page has already been bitten twice by comparing
# against those: reword one and the comparison silently stops matching, here by
# writing the wrong ERP column into an UPDATE. TARGET is the column name
# itself - "RUN" on both run analyses, "SETUP_HRS" on setup - so the mapping
# the statement needs IS the data. It is the one part baked in as text rather
# than referenced, because it is not a cell.
#
# THE COLUMN LETTERS ARE DERIVED, NOT TYPED. A formula saying J and A is right
# only for one column order, and this file's order has already been rearranged
# several times; a reorder would leave the formula quietly pointing at the
# wrong columns - Ratio instead of Suggested - and still looking plausible.
# Taking the letters from the position of the columns it actually means keeps
# the formula correct through any future reshuffle.
#
# THE ROW NUMBER IS POSITIONAL, counted after the sort and off the row's place
# in the file rather than off the frame's index, which the sort left unordered.
# Row 1 is the header, so the first data row is 2.
_out = [c for c in _cols if c != "TARGET"]
_out = ["STEP" if c == S else _RENAME.get(c, c) for c in _out]
assert len(_out) <= 26, "past column Z - the letters below need two characters"
_val, _rid = (chr(ord("A") + _out.index("SUGGESTED")),
              chr(ord("A") + _out.index("MASTER_OPS_ROWID")))
# A NaN would leave the formula building "SET RUN = ''", a live statement that
# blanks a standard. There are none today on any of the 2'468 rows; the cell is
# left empty rather than trusted, because an empty cell is a visible nothing.
#
# EMPTY ON AN ALREADY-DONE ROW TOO (user, 2026-10-06). Today's master is within
# 10% of SUGGESTED there, so the statement would only nudge a value already
# keyed; left in, it is one more live line for somebody to run by accident. The
# row stays in the file with TODAY_STATUS saying why its statement is blank.
_by_part["SQL_UPDATE"] = [
    "" if pd.isna(v) or pd.isna(rid) or s == "already done" else
    f'''="UPDATE OPERATION SET {t} = '"&{_val}{n}&"' WHERE ROWID = "&{_rid}{n}&";"'''
    for n, (t, v, rid, s) in enumerate(zip(_by_part.TARGET, _by_part.SUGGESTED,
                                           _by_part.MASTER_OPS_ROWID,
                                           _by_part.TODAY_STATUS), start=2)]
_by_part = _by_part.drop(columns=["TARGET"])
st.download_button(
    "Download master row updater as CSV",
    _by_part.to_csv(index=False).encode("utf-8"),
    file_name="fts_review_queue_sql_master_updater.csv", mime="text/csv",
    icon=":material/download:")
# THE COUNT IS THE CHECK. This file must have exactly as many rows as the
# "Operations rows to edit" tile at the top of the page, under every filter -
# both count the same thing from different ends, so the day they disagree the
# join is wrong. Printed rather than asserted: a mismatch should be visible,
# not a crash on a page somebody is using.
# WHAT IS LEFT FOR THE CAPTION, once the paragraph above says what the file is:
# the one thing only true of THIS download, which is how many rows it has right
# now under the filter in force.
#
# IT SAID "TRIAL" until 2026-09-01. That was honest while the join was unproven
# and meaningless afterwards - a word on screen that told a reader to distrust
# the file without saying what to distrust or when it would stop being true.
# The check it stood for is in the sentence that follows it, which names a
# figure on this same page that this count has to equal.
st.caption(f"**{ui.num(len(_by_part))}** rows, which should match *Operations "
           f"rows to edit* at the top of the page — it follows the same "
           f"filters as the table.")
