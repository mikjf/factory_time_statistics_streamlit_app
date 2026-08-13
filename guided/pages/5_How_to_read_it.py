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
    st.markdown("### Reading the colours")
    st.caption("Colour means something here. Nothing is coloured for looks.")
    ui.gate_rail(st, [
        {"passed": True, "name": "Green — the rule was satisfied",
         "value": "this unit cleared it"},
        {"passed": False, "name": "Red — the rule stopped it",
         "value": "only the first failure is marked"},
        {"passed": False, "name": "Grey — not the blocker",
         "value": "shown with its real value anyway"},
    ])
    st.caption("Every colour is paired with a symbol — ✓ ✕ – — because roughly "
               "one man in twelve cannot separate the green from the red, and "
               "this goes in front of a room.")
    st.divider()
    st.caption("**Thresholds in force**")
    st.caption(f"Minimum work orders: **{pipeline.MIN_WO}**  \n"
               f"Significance: **{pipeline.ALPHA}**  \n"
               f"Minimum deviation: **{pipeline.MIN_EFFECT:.0%}**  \n"
               f"Minimum impact: **{pipeline.MIN_HOURS_IMPACT:g} h** "
               f"({pipeline.SETUP_MIN_HOURS:g} h setup)  \n"
               f"Token booking: **≤ {pipeline.TOKEN_HOURS} h**")
    st.caption("Read from the analysis scripts, not typed here — if one "
               "changes, this page moves with it.")

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
st.info(
    f"Every unit shows a **shaded band** and a **red line**, and they are "
    f"different estimates. The band is the range around the average of the "
    f"per-work-order ratios — every work order counts once, big job or small. "
    f"The line is the ratio across the whole pool weighted by hours, and that "
    f"is what drives the correction. Where big and small jobs behave "
    f"differently the two genuinely disagree, and in {_outside} of "
    f"{len(_acts)} decisions the line sits outside its own band. That is not a "
    f"mistake: the band is only ever used as a test — does it exclude 1.0? — "
    f"never as error bars on the line.", icon=":material/insights:")
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
# - all 11 that do are family pools - so this example shows the two estimates
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
                    f"than it allows. The **red line is the correction** at "
                    f"{_ex.RATIO:.3f} — the jobs took "
                    f"{100 * (_ex.RATIO - 1):+.1f}% longer than allowed, so "
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
st.error(
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

kc1, kc2 = st.columns([1.25, 1])
with kc1:
    # "six of them" is counted, not typed. If the pipeline ever emits a seventh
    # phrasing the list grows on its own, and a sentence saying six beside a
    # list of seven is the kind of thing nobody notices for a year.
    st.markdown(f"**The instruction is on every decision, and there are "
                f"{len(_k['how_to_apply'])} of them:**")
    st.markdown(
        "\n".join(f"- `{n}` — {how}"
                  for how, n in _k["how_to_apply"]))
with kc2:
    st.info(
        f"**One family decision is many edits.** The {_k['fam_actions']} "
        f"`PCS/HR` family decisions write the same value to "
        f"{ui.num(_k['fam_edits'])} routing lines between them — every part in "
        f"the pool, each with its own `MASTER_OPS_ROWID`. That is why "
        f"{ui.num(_k['edits'])} run rows carry only {_k['run_actions']} run "
        f"decisions.",
        icon=":material/content_copy:")

# The blank cell that looks like a bug. 21 of 230, all family-level run.
st.warning(
    f"**{_k['no_value']} decisions carry no single value to key in, and that "
    f"is deliberate.** Those families hold several different `RUN_MASTER` "
    f"values across their parts, so there is no one number to write. The row "
    f"says *{_k['no_value_note']}* — the ratio is the instruction, not the "
    f"value. A blank in the suggested column on those rows is the correct "
    f"reading, not a gap.", icon=":material/functions:")

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
