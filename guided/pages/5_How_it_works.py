"""The flow, the exclusion rules and the limits - in plain language."""

import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from h0app import data, freshness, pipeline, text, ui  # noqa: E402

st.set_page_config(page_title="How it works · H0",
                   page_icon=":material/school:", layout="wide")
ui.inject()
st.title("How it works")
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

st.markdown(text.HOW_IT_WORKS)
st.page_link("pages/6_Dataset.py",
             label="What is deliberately left out of the data, and why",
             icon=":material/database:")

st.subheader("The six rules")
st.caption("Applied in this order to every pool. All six must pass before a "
           "standard is proposed for change — and every unit shows which of "
           "them it passed, including the ones left alone.")

# From text.rules(), the same source the rail uses. Written out here separately
# it drifted out of step with the working page within a day.
cols = st.columns(3)
for i, (name, rule, stops) in enumerate(text.rules()):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{i + 1}. {name}**")
            st.markdown(ui.chip(rule, ui.INFO), unsafe_allow_html=True)
            st.caption(f"**Stops:** {stops}")

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
st.page_link("pages/6_Dataset.py",
             label="What all this is computed over — the dataset, its period, "
                   "and every operation examined",
             icon=":material/database:")
