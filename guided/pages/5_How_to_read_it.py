"""The flow, the exclusion rules and the limits - in plain language."""

import pathlib
import sys

import streamlit as st

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import (charts, data, evidence, freshness,  # noqa: E402
                   pipeline, text, ui)

st.set_page_config(page_title="How to read it · H0",
                   page_icon=":material/school:", layout="wide")
ui.inject()
st.title("How to read it")
freshness.guard()

with st.sidebar:
    # side_title/side_note rather than "### ..." and st.caption. This column had
    # four type sizes in it - an 18px h3, 14px captions, a 15.2px rail and the
    # 13.12px key/value blocks that Overview and Methodology settled on. One
    # size now, set in ui.
    ui.side_title(st, "Reading the colours")
    ui.side_note(st, "Colour means something here")
    # ui.legend rather than a hand-written gate_rail. The hand-written version
    # named three of the four states, in different words than Inspect uses for
    # the same thing - and the one it omitted was amber, the review flag. One
    # definition now, in ui.STATES, rendered two ways.
    ui.legend(st, explain=True)
    # TWO THINGS WERE CUT FROM UNDER HERE.
    #
    # A line explaining that every colour is paired with a symbol because
    # roughly one man in twelve cannot tell the green from the red. True, and
    # the reason the symbols exist - but the symbols are visibly there in the
    # panel above, so it explained a design decision to somebody who had not
    # asked. The rationale lives in ui.py's module docstring, where whoever
    # might remove the symbols will actually read it.
    #
    # And the thresholds panel, which Methodology carries. This page links to
    # the six rules rather than repeating them, on the grounds that Methodology
    # owns them; copying their NUMBERS while linking to the rules themselves
    # was the inconsistent half of that. The one threshold this page discusses,
    # the six-work-order floor, is stated inline in its own prose.

# Only the correction directions. "Where the numbers come from" is what the
# whole of Methodology answers, and gross-versus-net is on the landing page and
# again in Methodology's reconciliation. Both were rendered here as recently as
# an hour ago because all three live in one constant and I rendered the block
# whole after cutting the six rules out from under it.
st.markdown(text.TWO_DIRECTIONS)

# THE SIX RULES ARE NOT REPEATED HERE. Methodology shows them at the point they
# fire, between step 1 and step 2, where the counts either side make them mean
# something. A second copy is a second thing to keep in step, and this project
# has already paid for that once - v1 calls them gates, v2 calls them rules, and
# text.py uses both in its own docstrings.
st.page_link("pages/6_Methodology.py",
             label="The six rules, and where each one is applied",
             icon=":material/rule:")

st.divider()

# ---- ORDER OF THIS PAGE ------------------------------------------------------
# Follows what a reader does, not what the pipeline does. Somebody arrives here
# from Inspect holding one recommendation and asks, roughly in this order:
#
#   which way does the number move, and why      -> the two directions
#   why this part, or why the whole family       -> part or family
#   the chart's band and line disagree, is it broken -> two estimates
#   it says NEEDS REVIEW                         -> flagged for review
#   what can this not tell me                    -> cannot tell you
#   fine - what do I type, and where             -> what you are keying in
#
# Keying used to sit second, which put the last thing you do near the top.
_k = data.keying()

st.subheader("Part or family?")
st.markdown(f"""
A part gets its **own** standard only where it demonstrably differs from its
family. If the family's ratio falls inside the part's own 95% interval the two
are statistically indistinguishable, and giving the part a separate standard
would preserve sampling noise rather than a real process difference.

Where a part is too thin to judge alone — fewer than {pipeline.MIN_WO} work
orders — its family may still pool enough evidence. Parts already flagged
individually are **removed from the family pool before the family ratio is
computed**, so the two routes never both act on the same part, and the family
figure is not propped up by the parts already known to be off.

Both candidate values stay in the workbook, so any row can be overridden by eye.
""")

st.divider()

st.subheader("Two estimates, side by side")
_acts = data.actions()
_outside = int(((_acts.RATIO < _acts.CI95_LOW_PER_WO)
                | (_acts.RATIO > _acts.CI95_HIGH_PER_WO)).sum())
# Plain prose, not st.info. This one stays prose: it is the section's own
# content, the subheader above already announces it, and a box around a
# section's body says "aside" about the main point. That is the test the whole
# page now uses - box an aside, never a body - and it is why the two notes in
# "What you are keying in" went back into boxes while this one did not.
st.markdown(
    f"Every unit shows a **shaded band** and a **red line**, and they are "
    f"different estimates. The band is the range around the average of the "
    f"per-work-order ratios — every work order counts once, big job or small. "
    f"The line is the ratio across the whole pool weighted by hours, and that "
    f"is what drives the correction. Where big and small jobs behave "
    f"differently the two genuinely disagree, and in {_outside} of "
    f"{len(_acts)} decisions the line sits outside its own band. That is not a "
    f"mistake: the band is only ever used as a test — does it exclude 1.0? — "
    f"never as error bars on the line.")
# Says what to DO about it, which the paragraph above never did. A reader who
# spots the disagreement and is not told it changes nothing will assume it does.
st.caption("Nothing to act on. A unit whose line sits outside its band has "
           "still passed the same six rules as every other, and the value to "
           "key is the line either way.")

# A worked example, because the paragraph above names a band and a line to a
# reader who may not have opened Inspect yet.
#
# INSIDE AN EXPANDER because drawing it rebuilds the evidence from the parquet,
# which is the one expensive call in the app. Everything else on this page is
# text and a workbook read; paying for a chart nobody asked to see would make
# the cheapest page the slowest.
#
# ONE PART, WITH A VALUE TO KEY, best evidenced. A family pool is an abstraction
# to somebody meeting the chart for the first time - "all parts of this family"
# names nothing they can picture - and a decision carrying no single value has
# an empty suggested column, which is a second thing to explain before the first
# has landed.
#
# The cost, and it is real: NO part-level decision has its line outside its band
# - every one that does is a family pool - so this example shows the two estimates
# AGREEING. It teaches what the chart is; it cannot demonstrate the disagreement
# the paragraph above describes.
_ex_pool = _acts[(_acts.LEVEL == "PART") & _acts.SUGGESTED_VALUE.notna()]
if len(_ex_pool):
    _ex = _ex_pool.nlargest(1, "N_WO").iloc[0]
    # Everything needed to find the row in the workbook: which part, whose
    # family, which step, and which of the three analyses judged it. The last
    # one also decides the unit the standard is held in, below.
    _route = ("Setup" if _ex.TARGET == "SETUP_HRS"
              else f"Run {_ex.RUN_TYPE}")
    _unit = ("hours" if _ex.TARGET == "SETUP_HRS"
             else "hours per load" if _ex.RUN_TYPE == "HRS/LOAD"
             else "pieces per hour")
    with st.expander(f"See one — Part {_ex.PART_ID} · {_ex.FAMILY} · "
                     f"{_ex.OPERATION} sequence {int(_ex.SEQUENCE)} · "
                     f"{_route}"):
        try:
            if _ex.TARGET == "SETUP_HRS":
                _rows, _stats = evidence.setup(
                    _ex.OPERATION, _ex.FAMILY, _ex.PART_TYPE, _ex.SEQUENCE)
            elif _ex.RUN_TYPE == "HRS/LOAD":
                _rows, _stats = evidence.load(
                    _ex.OPERATION, _ex.FAMILY, _ex.PART_TYPE, _ex.SEQUENCE,
                    _ex.PART_ID if _ex.LEVEL == "PART" else None)
            elif _ex.LEVEL == "PART":
                _rows, _stats = evidence.run_part(
                    _ex.OPERATION, _ex.FAMILY, _ex.PART_TYPE, _ex.PART_ID,
                    _ex.SEQUENCE)
            else:
                _rows, _stats = evidence.run_family(
                    _ex.OPERATION, _ex.FAMILY, _ex.PART_TYPE, _ex.SEQUENCE)
            # legend=False: ui.chart_key() below replaces it with the complete
            # one. The chart's own legend lists only the statuses present here,
            # and the two overlapped on four rows.
            _chart = charts.distribution(_rows, _stats, height=300,
                                         legend=False)
            if _chart is not None:
                st.altair_chart(_chart, width="stretch")
                # Says what the standard IS, in its own unit, before saying
                # what it becomes. "10 -> 8.48" means nothing without "pieces
                # per hour", and the sign only makes sense once you know a
                # rate falls when a job takes longer.
                st.caption(
                    f"{int(_ex.N_WO)} work orders on one part. The standard "
                    f"here is **{_ex.CURRENT_VALUE:g} {_unit}**. The "
                    f"**dashed grey line at 1.0** is that standard as it "
                    f"stands; every dot right of it is a job that took longer "
                    f"than it allows. The **red line, `measured`**, is where "
                    f"the jobs actually ran, at {_ex.RATIO:.3f} — "
                    f"{100 * (_ex.RATIO - 1):+.1f}% against what the standard "
                    f"allows. This unit passed all six rules, so that "
                    f"measurement becomes the correction and "
                    f"the standard becomes **{_ex.SUGGESTED_VALUE:g} {_unit}** "
                    f"({_ex.CURRENT_VALUE:g} ÷ {_ex.RATIO:.3f}), a change of "
                    f"{_ex.CHANGE_PCT:+.1f}%. The shaded band runs "
                    f"{_ex.CI95_LOW_PER_WO:.3f} to "
                    f"{_ex.CI95_HIGH_PER_WO:.3f}, and the red line falls "
                    f"inside it — weighting by hours and counting each work "
                    f"order once land in the same place here.")
                # Every mark the chart can draw, not only the two this unit
                # happens to use. Its own legend lists what is present, which
                # teaches nothing about what a different unit will look like.
                ui.chart_key(st)
            else:
                st.caption("No chart for this unit.")
        except Exception as err:                     # noqa: BLE001
            # An example failing must not take the page with it - everything
            # above is the actual content and none of it depends on this.
            st.caption(f"The example could not be drawn ({type(err).__name__})."
                       f" Every unit's own chart is on **Inspect**.")

st.divider()

# ---- the flag ---------------------------------------------------------------
# 85 rows nothing else in the tool mentioned. They pass all six rules, which is
# exactly why they need saying: a reader who trusts the rules has no reason to
# look twice, and these are the ones worth looking at twice.
# Full width, stacked. Side by side, the red box and the paragraph explaining it
# were two half-width columns of unequal length, and the eye had to cross the
# gutter mid-thought to get from the number to what it means.
st.subheader("Flagged for review")
# AMBER, not red - but the same ALERT layout as every other st.error/st.warning
# /st.info in the app, so the boxes differ only in colour. A verdict_banner here
# was the right colour in the wrong shape: one box on one page laid out unlike
# the other eighteen.
#
# st.error painted this the FAIL colour - "a rule stopped it" - directly above a
# paragraph that opens "These have passed all six rules". It contradicted the
# sentence under it and the legend in the sidebar, where the review flag is
# amber. st.warning is what the rest of the app already uses for "needs
# attention, nothing is broken".
st.warning(
    f"**{_k['flagged']} of the {ui.num(_k['edits'])} run rows are marked "
    f"`NEEDS REVIEW`.** Their ratios run from **{_k['flag_lo']:.2f}** to "
    f"**{_k['flag_hi']:.2f}** — outside 0.25–4.0, meaning the evidence says "
    f"the standard is off by a factor of four or more.",
    icon=":material/flag:")
st.markdown("""
These have passed all six rules. The flag is not a doubt about the statistics —
it is a doubt about the **standard being corrected**, because a factor of four
usually means something other than a slow or fast process: a unit of measure
changed, a routing step now covers different work, or a quantity is being
booked against the wrong line.

Treat them as **findings to check, not values to key**. The number is in the
workbook so nothing is hidden, and they are counted in the totals — but keying
one unread is how a data problem becomes a standard.
""")

st.divider()

# "This" had no antecedent - the reader had just been through four sections and
# could reasonably read it as the page, the flag, or the chart.
st.subheader("What the analysis cannot tell you")
st.markdown(text.CANNOT_TELL)

st.divider()

# ---- last, because it is the last thing you do -------------------------------
st.subheader("What you are keying in")
st.caption("One decision is not one edit, and the field it writes to is not "
           "always the same one.")

# ONE COLUMN, STACKED. This was a 1.25/1 split with the instruction list left
# and its two notes right, and the two columns were never the same height - a
# short list beside a long note, or the reverse, leaves a ragged edge down the
# middle and a block of white space in whichever cell ran out first. Stacked,
# every block starts at the same left margin and ends where its own text ends.
#
# It also puts them in reading order. Both notes are ABOUT the list, and a note
# beside the thing it annotates asks the eye to cross a gutter mid-thought to
# find out what is being annotated.

# "six of them" is counted, not typed. If the pipeline ever emits a seventh
# phrasing the list grows on its own, and a sentence saying six beside a list of
# seven is the kind of thing nobody notices for a year.
st.markdown(f"**The instruction is on every decision, and there are "
            f"{len(_k['how_to_apply'])} of them:**")
st.markdown(
    "\n".join(f"- `{n}` — {how}"
              for how, n in _k["how_to_apply"]))

# BOXED. This is an aside - a note about the list above, not an item in it - and
# the box is what says so now that it no longer sits in its own column.
#
# Blue, not amber. Amber on this page means one thing, a human has to look before
# keying, and it is spent on the 85 flagged rows above. This carries no doubt: it
# says a decision fans out to many rows, which is arithmetic.
#
# The closing clause splits the 166 rather than describing them all as
# family-wide, because 59 of them are not: run_actions is every PCS/HR run
# decision, fam_actions only the FAMILY-level ones, and the difference is the
# part-level decisions that touch exactly one part. Both numbers are read from
# the workbook and the remainder is subtracted, so the split cannot drift.
st.info(
    f"**One family decision is many edits.** The {_k['fam_actions']} "
    f"`PCS/HR` family decisions write the same value to "
    f"{ui.num(_k['fam_edits'])} routing lines between them — every part in "
    f"the pool, each with its own `MASTER_OPS_ROWID`. That is why "
    f"{ui.num(_k['edits'])} run rows carry only {_k['run_actions']} run "
    f"decisions — {_k['fam_actions']} of them landing on every part of a "
    f"family at once, and only {_k['run_actions'] - _k['fam_actions']} on a "
    f"single part.",
    # call_split, not content_copy. The old icon was two sheets of paper, which
    # reads as "duplicate this" - the wrong idea entirely, since the many rows
    # are not copies of a decision but the places it lands. One line dividing
    # into several is the shape of the sentence.
    icon=":material/call_split:")

# The blank cell that looks like a bug. Unboxed, unlike the note above it: two
# boxes in a row is a panel of boxes rather than an annotation, and one box
# followed by a paragraph reads as the note and its follow-on, which is what
# they are.
#
# FULL LENGTH, restored. It was cut by two clauses and the cut cost clarity:
# "and that is deliberate" reads as a warning that the surprise is coming, and
# the reader meets the blank column BEFORE the sentence explaining it. And the
# closing point earns its own sentence - it is the one instruction here, what to
# do when the cell is empty, and buried behind a comma it reads as an aside.
st.markdown(
    f"**{_k['no_value']} decisions carry no single value to key in, and "
    f"that is deliberate.** Those families hold several different "
    f"`RUN_MASTER` values across their parts, so there is no one number to "
    f"write. The row says *{_k['no_value_note']}* — the ratio is the "
    f"instruction, not the value. A blank in the suggested column on those "
    f"rows is the correct reading, not a gap.")

# "Staying honest about staleness" and "The pipeline behind this" moved to the
# Dataset page: both are about the files the analysis is computed from rather
# than about how a conclusion is drawn from them.

# The per-operation coverage table used to sit here in an expander. It is a
# statement about the data rather than about the method, so it moved to the
# Dataset page along with the funnel.
#
# The rule closes the page rather than separating two sections: the link below
# leaves for another page, and without it the link read as a loose end of the
# keying section above it.
st.divider()
st.page_link("pages/6_Methodology.py",
             label="What all this is computed over — the dataset, its period, "
                   "and every operation examined",
             icon=":material/database:")
