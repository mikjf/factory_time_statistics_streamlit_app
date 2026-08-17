"""The queue: every standard proposed for change, narrowed to what you own.

Two things this does that a spreadsheet does not. Filters live in the left rail
so the table gets the whole width, and the totals follow the filter - so
"what is my family worth" is answered by the same control that finds it.
"""

import pathlib
import sys

import streamlit as st

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import data, freshness, pipeline, ui  # noqa: E402  (ui: number format)

st.set_page_config(page_title="Review queue · H0",
                   page_icon=":material/checklist:", layout="wide")
ui.inject()
st.title("Review queue")
st.caption("One row per decision. Pick a row to open the evidence behind it.")
freshness.guard()

acts = data.actions()
S = data.SEQ

# ---- filters, in the rail ---------------------------------------------------
with st.sidebar:
    st.markdown("### Narrow it down")

    def multi(label, col, key=None):
        vals = sorted(acts[col].dropna().unique().tolist())
        return st.multiselect(label, vals, default=[], key=key,
                              placeholder=f"all ({len(vals)})")

    fam = multi("Family", "FAMILY")
    op = multi("Operation", "OPERATION")
    pt = multi("Part type", "PART_TYPE")
    st.divider()
    field = st.multiselect("Field it edits", sorted(acts.TARGET.unique()),
                           placeholder="all")
    rtype = st.multiselect("Run type", sorted(acts.RUN_TYPE.unique()),
                           placeholder="all")
    level = st.multiselect("Judged at", sorted(acts.LEVEL.unique()),
                           placeholder="all")
    st.divider()
    only_review = st.toggle(
        "Only the ones needing a human", value=False,
        help=f"Ratio outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI}. The "
             f"test is on the ratio, not the percentage change: a rate that "
             f"quadruples reads +300% but one cut to a quarter reads −75% and "
             f"can never pass −100%, so flagging on the change would catch "
             f"only increases.")
    big_first = st.toggle("Biggest hours first", value=True)

d = acts
for col, sel in [("FAMILY", fam), ("OPERATION", op), ("PART_TYPE", pt),
                 ("TARGET", field), ("RUN_TYPE", rtype), ("LEVEL", level)]:
    if sel:
        d = d[d[col].isin(sel)]
if only_review:
    d = d[d.NEEDS_REVIEW]
if big_first:
    d = d.reindex(d.HOURS_DELTA.abs().sort_values(ascending=False).index)

m = st.columns(4)
m[0].metric("Decisions shown", ui.num(len(d)),
            delta=f"of {ui.num(len(acts))}" if len(d) != len(acts) else None,
            delta_color="off")
m[1].metric("Absolute misstated hours", ui.hrs(d.HOURS_DELTA.abs().sum()))
# N_PARTS summed is a count of FIELD EDITS, not of parts: a part is edited once
# per operation it runs, so summing it across actions counts the same part
# several times. It sat one click from Home's distinct-part count under a
# near-identical label, reading as a contradiction.
m[2].metric("Operations rows to edit", ui.num(d.N_PARTS.sum()),
            help="One edit per part per operation. A part running four "
                 "corrected operations is four edits.")
m[3].metric("Need a human first", ui.num(d.NEEDS_REVIEW.sum()),
            help=f"Ratio outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI} — "
                 f"large enough to want checking before it is keyed in.")

if d.empty:
    st.info("Nothing matches those filters.", icon=":material/filter_alt_off:")
    st.stop()

detail = st.toggle("Show the statistics columns", value=False,
                   help="Ratio and confidence interval. Hidden by default so "
                        "the decision columns are readable at a glance.")

base = ["FAMILY", "PART_TYPE", "OPERATION", S, "LEVEL", "PART_ID", "TARGET",
        "RUN_TYPE", "N_PARTS", "N_WO", "CURRENT_VALUE", "SUGGESTED_VALUE",
        "CHANGE_PCT", "HOURS_DELTA", "NEEDS_REVIEW"]
extra = ["RATIO", "CI95_LOW_PER_WO", "CI95_HIGH_PER_WO", "DIRECTION",
         "HOW_TO_APPLY"]
cols = base + (extra if detail else [])

event = st.dataframe(
    ui.swiss_grid(d[cols], {"N_WO": ",.0f", "N_PARTS": ",.0f",
                            "CURRENT_VALUE": ",.2f", "SUGGESTED_VALUE": ",.2f",
                            "CHANGE_PCT": ",.1f", "HOURS_DELTA": ",.0f",
                            "RATIO": ",.3f", "CI95_LOW_PER_WO": ",.3f",
                            "CI95_HIGH_PER_WO": ",.3f"}),
    hide_index=True, width="stretch", height=430,
    on_select="rerun", selection_mode="single-row",
    column_config={
        "FAMILY": st.column_config.TextColumn(width="medium"),
        "PART_TYPE": st.column_config.TextColumn("TYPE", width="small"),
        S: st.column_config.NumberColumn("SEQ", format="%d"),
        "LEVEL": st.column_config.TextColumn(
            "JUDGED AT", help="PART = this part had enough work orders on its "
                              "own. FAMILY = it did not, but its family pooled "
                              "enough."),
        "PART_ID": st.column_config.TextColumn("APPLIES TO", width="medium"),
        "TARGET": st.column_config.TextColumn("FIELD"),
        "N_WO": st.column_config.NumberColumn(
            "WORK ORDERS", help="How much evidence the figure rests on"),
        # No `format` on these: the Styler above owns the display, and a
        # NumberColumn format would override it and put the commas back.
        "CURRENT_VALUE": st.column_config.NumberColumn("NOW"),
        "SUGGESTED_VALUE": st.column_config.NumberColumn("PROPOSED"),
        "CHANGE_PCT": st.column_config.NumberColumn("CHANGE %"),
        "HOURS_DELTA": st.column_config.NumberColumn(
            "HOURS A YEAR",
            help="Actual minus master. Positive = the job takes longer than "
                 "the master allows."),
        "NEEDS_REVIEW": st.column_config.CheckboxColumn("CHECK?"),
        "RATIO": st.column_config.NumberColumn(),
        "CI95_LOW_PER_WO": st.column_config.NumberColumn("CI LOW"),
        "CI95_HIGH_PER_WO": st.column_config.NumberColumn("CI HIGH"),
        "HOW_TO_APPLY": st.column_config.TextColumn(width="large"),
    })

rows = event.selection["rows"] if event and event.selection else []
if rows:
    r = d.iloc[rows[0]]
    st.session_state["unit"] = {
        "TARGET": r.TARGET, "RUN_TYPE": r.RUN_TYPE, "OPERATION": r.OPERATION,
        "FAMILY": r.FAMILY, "PART_TYPE": r.PART_TYPE, "SEQ": int(r[S]),
        "LEVEL": r.LEVEL,
        "PART_ID": r.PART_ID if r.LEVEL == "PART" else None,
    }
    with st.container(border=True):
        st.markdown(f"**{r.FAMILY} · {r.OPERATION} · seq {int(r[S])}** — "
                    f"{r.HOW_TO_APPLY}")
        # Caption, matching Inspect: the same sentence should not be body text
        # on one page and a note on the next.
        st.caption(ui.direction_note(r.TARGET, r.RUN_TYPE))
        st.page_link("pages/2_Inspect.py",
                     label="Open the evidence behind this",
                     icon=":material/query_stats:")
else:
    st.caption("Click any row to carry it into **Inspect**.")

st.download_button(
    "Download this view as CSV", d[cols].to_csv(index=False).encode("utf-8"),
    file_name="h0_review_queue.csv", mime="text/csv",
    icon=":material/download:")
