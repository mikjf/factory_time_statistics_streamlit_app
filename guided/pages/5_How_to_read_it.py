"""The flow, the exclusion rules and the limits - in plain language."""

import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from h0app import data, freshness, pipeline, text, ui  # noqa: E402

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

# ---- what you actually key in -----------------------------------------------
_k = data.keying()

st.subheader("What you are keying in")
st.caption("One decision is not one edit, and the field it writes to is not "
           "always the same one.")

kc1, kc2 = st.columns([1.25, 1])
with kc1:
    st.markdown("**The instruction is on every row, and there are six of "
                "them:**")
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

st.divider()

# ---- the flag ---------------------------------------------------------------
# 85 rows nothing else in the tool mentioned. They pass all six rules, which is
# exactly why they need saying: a reader who trusts the rules has no reason to
# look twice, and these are the ones worth looking at twice.
st.subheader("Flagged for review")
fc1, fc2 = st.columns([1, 1])
with fc1:
    st.error(
        f"**{_k['flagged']} of the {ui.num(_k['edits'])} run rows are marked "
        f"`NEEDS REVIEW`.** Their ratios run from **{_k['flag_lo']:.2f}** to "
        f"**{_k['flag_hi']:.2f}** — outside 0.25–4.0, meaning the evidence "
        f"says the standard is off by a factor of four or more.",
        icon=":material/flag:")
with fc2:
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

st.subheader("What this cannot tell you")
st.markdown(text.CANNOT_TELL)

# "Staying honest about staleness" and "The pipeline behind this" moved to the
# Dataset page: both are about the files the analysis is computed from rather
# than about how a conclusion is drawn from them.

# The per-operation coverage table used to sit here in an expander. It is a
# statement about the data rather than about the method, so it moved to the
# Dataset page along with the funnel.
st.page_link("pages/6_Methodology.py",
             label="What all this is computed over — the dataset, its period, "
                   "and every operation examined",
             icon=":material/database:")
