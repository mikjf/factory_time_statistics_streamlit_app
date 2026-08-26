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

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import data, freshness, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="Review queue · H0",
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
# act on this as it stands" - which is false of 230 of the 237 and would be a
# second meaning for the one colour the legend promises has only one.
#
# NO FIGURE IN IT, deliberately, and not only to keep it from going stale. There
# is no honest denominator to quote: EXAMINED counts one part at one step on the
# part route and one FAMILY at one step on the family route, so a summed
# "237 of N" would add two units together and report them as one. The tile below
# carries the 237 and follows the filter; this banner is true whatever is picked.
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
# reached the test at all - 8'490 of the 9'118 units on the PCS/HR part route.
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
# understood on first read. "Proposed" rather than "suggested": the workbook's
# own strings read "no change - not significant", and Proposed is the column
# header a few inches to the right.
#
# NOT "the standard is correct", which the gloss must not become. 157 of the
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
# EFFECT drops the " the standard" DIRECTION repeats on all 237 rows - the column
# heading says it once. A plain string replace rather than a lookup, so a third
# direction added upstream passes through as itself instead of vanishing.
acts["ANALYSIS"] = [ui.analysis_name(t, r)
                    for t, r in zip(acts.TARGET, acts.RUN_TYPE)]
acts["EFFECT"] = acts.DIRECTION.astype(str).str.replace(
    " the standard", "", regex=False)


def applies_to(part_id, level):
    """PART_ID as a table cell rather than as a sentence.

    01_Actions writes a phrase in this column wherever the unit is judged on the
    family, and the longest of them - "every part of this family that performs
    the setup", 49 characters - was setting the width of the widest column on
    the page. It appears on exactly the 37 SETUP_HRS rows and nowhere else, so
    every character of it restates the Field column beside it.

    What the phrases actually carry, once Field and Parts are on the row, is one
    bit and one number: whole family or one part, and how many parts were left
    out of the pool. Both survive here; the setup wording does not, because
    Field already says SETUP_HRS on precisely those rows.

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
    # THE COUNT IS ONLY ON THESE TWO. Part type, Field and Judged at offer two
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
    big_first = st.toggle("Biggest hours first", value=True)

if only_review:
    d = d[d.NEEDS_REVIEW]
if big_first:
    d = d.reindex(d.HOURS_DELTA.abs().sort_values(ascending=False).index)

# ---- what the current filter is worth ---------------------------------------
# "Standards to review", the label Overview uses for the same 237, with the
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
# fourth is "Distinct parts affected", which cannot be shown here: on the 160
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
            # 0, 0 and 37 the moment that column's wording changed - which it
            # then did twice.
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
# asks how it differs from the other 217. Manual is the difference: the six rules
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
# family" or a part number, in words; RUN_TYPE is now inside Field, since
# RUN_MASTER is PCS/HR by definition and RUN is HRS/LOAD by definition.
base = ["FAMILY", "PART_TYPE", "OPERATION", S, "PART_ID", "ANALYSIS", "EFFECT",
        "CURRENT_VALUE", "TO_KEY", "TO_KEY_CHANGE_PCT", "N_PARTS",
        "HOURS_DELTA", "N_WO", "NEEDS_REVIEW"]
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
        "FAMILY": st.column_config.TextColumn("Family", width="medium"),
        "PART_TYPE": st.column_config.TextColumn(
            "Part type", width="small",
            help="ADV finished, ANDV semi-finished. Both are analysed, never "
                 "in the same pool — same family, different physical job."),
        # No width - sized to content, same as Family, and the same treatment
        # Additional findings gives its operation columns.
        "OPERATION": st.column_config.TextColumn("Operation"),
        S: st.column_config.NumberColumn("Step", format="%d"),
        "PART_ID": st.column_config.TextColumn(
            "Applies to", width="small",
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
        "CURRENT_VALUE": st.column_config.NumberColumn("Now"),
        # RM_RECOMMENDED from the execution sheets, which is what a reviewer
        # actually keys. Since 2026-08-26 it equals 01_Actions' SUGGESTED_VALUE
        # on every part row - a part that passed the six rules keeps its own
        # figure - so this is a consistency check, not a correction. See
        # data.actions for what changed and why.
        "TO_KEY": st.column_config.NumberColumn(
            "Proposed",
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
        "N_PARTS": st.column_config.NumberColumn(
            "Parts",
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
        # page rather than about this column. The sign on every value, and the
        # neighbours either side, say it is a difference.
        "HOURS_DELTA": st.column_config.NumberColumn(
            "Hours",
            help=f"Actual minus master for this standard, from the start of "
                 f"{pipeline.FY_LABEL} to the last booking in the extract. "
                 f"Positive means the jobs take longer than the master "
                 f"allows."),
        "N_WO": st.column_config.NumberColumn(
            "Work orders",
            help="How many work orders the figure is based on."),
        # "Flagged?", not "Check?" - the third name this page had for the state
        # its own tile and rail now both call flagged. Still one word wide.
        "NEEDS_REVIEW": st.column_config.CheckboxColumn(
            "Flagged?",
            help=f"Ratio outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI}. It "
                 f"passed all six rules, but the change is large enough that "
                 f"a person should check it before it is keyed in."),
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
_no_value = int(d.TO_KEY.isna().sum())
if _no_value:
    st.caption(f"**{_no_value}** of these have no single value to key. Their "
               f"family runs several different current values, so the "
               f"instruction is to apply the ratio to each part's own value. "
               f"Click one to see it.")

# WHY PROPOSED IS NOT WHAT THIS PART MEASURED, on the rows where it is not.
# These are judged at PART level - the rail says a part number, not the family -
# so nothing else on the row hints that the value came from the family pool, and
# a reader who notices the gap has every reason to read it as a display fault.
# Counted, never written down, and silent on the other rows.
# AN INTEGRITY CHECK, NOT AN EXPLANATION - and it used to be the opposite.
# Until 2026-08-26 a rule in h0_v2_update_list overrode a part's own figure
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
    # two placeholders are mutually exclusive: the 20 rows carrying no single
    # value are exactly the 20 whose instruction names RATIO instead.
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
    # "Carry it into Inspect" was both a figure of speech and, since the row
    # card grew, no longer the whole truth - clicking now shows the instruction
    # here as well as offering the link. Says what happens, in plain words.
    st.caption("Click any row for the instruction, and a link to the evidence "
               "behind it.")

# THE DOWNLOAD CARRIES MORE THAN THE SCREEN, the same break Inspect makes. It
# used to export exactly the visible columns, so the toggle above silently
# decided whether the file had a confidence interval in it.
#
# The two derived columns are the only things left out, and both because the
# file already holds what they were made from: EFFECT is DIRECTION with three
# words removed, ANALYSIS is TARGET and RUN_TYPE glued together. A spreadsheet
# is where somebody pivots, and pivoting wants the two source columns.
_dl = d.drop(columns=["EFFECT", "ANALYSIS"])
st.download_button(
    "Download this view as CSV", _dl.to_csv(index=False).encode("utf-8"),
    file_name="h0_review_queue.csv", mime="text/csv",
    icon=":material/download:")
# Opens the same way Additional findings' download caption does - "carries every
# column ... including the ones not shown" - so the two pages describe the same
# promise in the same words.
st.caption("The download carries every column of `01_Actions` for these rows, "
           "including the ones not shown in the table — the confidence band, "
           "the level each pool was judged at, and the instruction as the "
           "workbook writes it.")
