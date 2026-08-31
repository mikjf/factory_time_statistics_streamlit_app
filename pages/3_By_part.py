"""One part: what changes, and what was examined and deliberately left alone.

The second half carries as much weight as the first. A part owner who cannot
find their part on the queue has no way to tell "we tested this and the standard
holds" from "we never had enough work orders to say", and those are completely
different answers to give a director.
"""

import pathlib
import sys

import pandas as pd
import streamlit as st

# parent.parent is streamlit_app/, where ftsapp lives. Every page inserts it
# itself rather than relying on Overview.py having run first: deep-link to a
# page in a fresh session and the import failed with ModuleNotFoundError:
# no module named 'ftsapp'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ftsapp import data, freshness, pipeline, ui  # noqa: E402

st.set_page_config(page_title="By part · FTS", page_icon=":material/qr_code:",
                   layout="wide")
ui.inject()
st.title("By part")
freshness.guard()

S = data.SEQ
edits = data.edits()
parts = sorted(edits.PART_ID.dropna().unique().tolist())

with st.sidebar:
    ui.side_title(st, "Find a part")
    mode = st.radio("Search", ["Parts with a proposed change", "Any part number"])
    if mode.startswith("Parts with"):
        part = st.selectbox(f"{ui.num(len(parts))} parts", parts)
    else:
        part = st.text_input("Part number",
                             placeholder="the full part number").strip()

if not part:
    st.info("Pick a part in the left rail, or type a part number, to see every "
            "step of it that was examined.", icon=":material/arrow_back:")
    st.stop()

mine = edits[edits.PART_ID == part]

found = [h for op in data.operation_list()
         for h in [data.all_units(op)] if not h.empty
         for h in [h[h.PART_ID == part]] if len(h)]
steps = pd.concat(found, ignore_index=True) if found else pd.DataFrame()

# Three different situations, and each needs its own answer:
#
#   not in the extract at all   -> a typo, or the part did not run this year
#   in the extract, nothing to  -> 54 parts: every ticket was a token booking,
#     judge                        or rework, or a step no longer in the master
#                                  revision. Real parts. Telling their owner
#                                  they do not exist is worse than the false
#                                  all-clear this replaced.
#   examined, and left alone    -> the standard held
#
# Membership is tested against the extract itself, not against the PCS/HR run
# units, because having no run unit is not the same as not existing.
in_extract = part in data.known_parts()
unknown = not in_extract
nothing_to_judge = in_extract and mine.empty and steps.empty

with st.sidebar:
    st.divider()
    ui.side_title(st, "What we found")
    if unknown:
        st.error("No labour ticket in this extract carries this part number.",
                 icon=":material/search_off:")
    elif nothing_to_judge:
        st.warning("In the extract, but nothing here could be judged.",
                   icon=":material/help:")
    else:
        held = int(steps.RECOMMENDATION.str.startswith("no change").sum()) \
            if len(steps) else 0
        thin = int((steps.N_WORK_ORDERS < pipeline.MIN_WO).sum()) \
            if len(steps) else 0
        # A counted summary, NOT the six-rule rail. These are counts, not
        # verdicts, and borrowing the rail's ticks and crosses put a green tick
        # on "0 steps tested" and a red cross on a part with nothing wrong.
        ui.summary_rail(st, [
            ("Standards to change", f"{len(mine)}",
             "field edits, across every analysis"),
            ("Examined and left alone", f"{held}",
             "tested, and the standard held"),
            ("Too few work orders to judge alone", f"{thin}",
             f"under {pipeline.MIN_WO} work orders — covered through the "
             f"family instead, where the family pools enough"),
        ])

st.subheader(f"{part}")

if unknown:
    ui.verdict_banner(
        st, "Part number not found", "unknown",
        "No labour ticket in this extract carries it. Check the number — or it "
        "may not have run in the current fiscal year.")
    st.info("The analysis covers the current fiscal year only, and only "
            "routing steps that still exist in the current master revision. "
            "**Methodology** lists every exclusion.", icon=":material/info:")
    st.stop()

if nothing_to_judge:
    ui.verdict_banner(
        st, "This part is in the extract, but nothing could be judged",
        "blocked",
        "It ran this year, and no step of it produced evidence a standard "
        "could be tested against.")
    st.markdown(f"""
**This is not a clean bill of health.** It means the analysis has nothing to say
about **{part}** in either direction, which usually comes down to one of:

- every work order was closed at or under {pipeline.TOKEN_HOURS} h — an order
  closed rather than a job timed, with no duration inside it to judge
- the steps it runs are rework, which carries no standard by design
- its routing steps are no longer in the current master revision, so the work
  orders measure a process that has been replaced

Its standards may be badly wrong and this analysis will never say so. **Not
standards changes** carries what that costs across the whole extract.
""")
    st.page_link("pages/4_Additional_findings.py",
                 label="See the hours charged for work with no evidence",
                 icon=":material/arrow_forward:")
    st.stop()

if mine.empty:
    ui.verdict_banner(st, "No standard change proposed for this part", "hold",
                      "That is not the same as no issue — see what was examined "
                      "below.")
else:
    ui.verdict_banner(st, f"{len(mine)} standard(s) to change", "act",
                      "MASTER_OPS_ROWID is the routing row to update so future "
                      "work orders inherit it.")
    # REVIEW_FLAG IS A SENTENCE IN THE SHEET - "NEEDS REVIEW - ratio outside
    # 0.25-4.0", on 88 of 2'422 rows and blank on the rest - and it was rendered
    # raw, under its own database name, to a reader with no schema. As a tick it
    # takes one narrow column and matches the Review queue, which shows the same
    # state under the same header; the sentence moves into the tooltip, where it
    # is read once rather than repeated down the column.
    _mine = mine.copy()
    _mine["REVIEW_FLAG"] = _mine.REVIEW_FLAG.notna()
    st.dataframe(
        ui.swiss_grid(
            _mine[["OPERATION", S, "TARGET_COLUMN", "RUN_TYPE", "ROUTE",
                   "CURRENT", "RECOMMENDED", "CHANGE", "BASIS", "RATIO",
                   "EVIDENCE_N", "MASTER_OPS_ROWID", "REVIEW_FLAG"]],
            {"CURRENT": ",.2f", "RECOMMENDED": ",.2f", "CHANGE": ",.1f",
             "RATIO": ",.3f", "EVIDENCE_N": ",.0f"}),
        hide_index=True, width="stretch",
        column_config={
            "OPERATION": st.column_config.TextColumn("Operation"),
            S: st.column_config.NumberColumn("Step", format="%d"),
            "TARGET_COLUMN": st.column_config.TextColumn("Field"),
            "RUN_TYPE": st.column_config.TextColumn("Run type"),
            "ROUTE": st.column_config.TextColumn(
                "Judged at", help="PART = this part had enough evidence alone. "
                                  "FAMILY = its family supplied the evidence."),
            "CURRENT": st.column_config.NumberColumn("Now"),
            "RECOMMENDED": st.column_config.NumberColumn("Suggested"),
            "CHANGE": st.column_config.NumberColumn("Change %"),
            "BASIS": st.column_config.TextColumn("Basis"),
            "RATIO": st.column_config.NumberColumn("Ratio"),
            "EVIDENCE_N": st.column_config.NumberColumn("Work orders"),
            # Left ungrouped on purpose - a routing row id is an identifier,
            # not a quantity, and 1'234'567 invites reading it as one.
            "MASTER_OPS_ROWID": st.column_config.NumberColumn("Routing row",
                                                              format="%d"),
            # Same header and same sentence as the Review queue's column.
            "REVIEW_FLAG": st.column_config.CheckboxColumn(
                "Flagged?",
                help=f"Ratio outside {pipeline.REVIEW_LO}–"
                     f"{pipeline.REVIEW_HI}. It passed all six rules, but the "
                     f"change is large enough that a person should check it "
                     f"before it is keyed in."),
        })
    if (~mine.ROWID_FOUND.fillna(False)).any():
        st.warning("Some rows have no routing row id and cannot be applied "
                   "from this list.", icon=":material/warning:")
    st.caption("A `RUN` row under PCS/HR is a rate and the correction divides; "
               "a `SETUP_HRS` row, or `RUN` under HRS/LOAD, is a duration and "
               "it multiplies.")

st.divider()
st.subheader("Every step of this part that was examined")

if steps.empty:
    st.info(f"No PCS/HR run step of **{part}** is in scope. Either the part did "
            f"not run this year, or every step of it sits outside the analysis "
            f"— most often because the routing step is no longer in the current "
            f"master revision. **Methodology** lists every exclusion.",
            icon=":material/info:")
    st.stop()

# Same two states as the Outcome column on Methodology, and worded the same.
# This page said "tested and it holds" / "never enough data to say" for what
# that one calls "tested and holds" / "not enough evidence" - one distinction,
# three phrasings, in a tool whose claim is that its words do not vary.
st.caption("Including the ones left alone. The verdict column distinguishes "
           "'tested and holds' from 'not enough evidence'.")
cols = ["OPERATION", S, "PART_DESCRIPTION", "N_WORK_ORDERS", "HOURS_MASTER",
        "HOURS_WORKED", "HOURS_DELTA", "RATIO_OUTLIERS_REMOVED",
        "RUN_MASTER_CURRENT", "RUN_MASTER_SUGGESTED", "RECOMMENDATION"]
st.dataframe(
    ui.swiss_grid(
        steps[cols].sort_values(S),
        {"N_WORK_ORDERS": ",.0f", "HOURS_MASTER": ",.1f",
         "HOURS_WORKED": ",.1f", "HOURS_DELTA": ",.1f",
         "RATIO_OUTLIERS_REMOVED": ",.3f", "RUN_MASTER_CURRENT": ",.2f",
         "RUN_MASTER_SUGGESTED": ",.2f"}),
    hide_index=True, width="stretch",
    column_config={
        S: st.column_config.NumberColumn("Step", format="%d"),
        "OPERATION": st.column_config.TextColumn("Operation"),
        "PART_DESCRIPTION": st.column_config.TextColumn("Description",
                                                        width="medium"),
        "N_WORK_ORDERS": st.column_config.NumberColumn("Work orders"),
        "HOURS_MASTER": st.column_config.NumberColumn("Master h"),
        "HOURS_WORKED": st.column_config.NumberColumn("Actual h"),
        # "Δ Hours", the same header the Review queue uses for the same
        # column. It read "Δ h" here and "Hours" there.
        "HOURS_DELTA": st.column_config.NumberColumn("Δ Hours"),
        "RATIO_OUTLIERS_REMOVED": st.column_config.NumberColumn("Ratio"),
        "RUN_MASTER_CURRENT": st.column_config.NumberColumn("Now"),
        "RUN_MASTER_SUGGESTED": st.column_config.NumberColumn("Suggested"),
        "RECOMMENDATION": st.column_config.TextColumn("Verdict", width="medium"),
    })
jump = st.selectbox(
    "Open one of these in Inspect", ["—"] + [
        f"{r.OPERATION} · seq {int(r[S])}" for _, r in steps.iterrows()],
    help="Carries the selection across, so Inspect opens on this part rather "
         "than making you pick the operation, family and step again.")
if jump != "—":
    r = steps.iloc[[f"{x.OPERATION} · seq {int(x[S])}"
                    for _, x in steps.iterrows()].index(jump)]
    st.session_state["unit"] = {
        "TARGET": "RUN", "RUN_TYPE": "PCS/HR", "OPERATION": r.OPERATION,
        "FAMILY": r.FAMILY, "PART_TYPE": r.PART_TYPE, "SEQ": int(r[S]),
        "LEVEL": "PART", "PART_ID": part,
    }
    st.page_link("pages/2_Inspect.py",
                 label=f"Open {r.OPERATION} · seq {int(r[S])} in Inspect",
                 icon=":material/query_stats:")
st.download_button("Download this part's steps as CSV",
                   steps[cols].to_csv(index=False).encode("utf-8"),
                   file_name=f"fts_by_part_{pipeline.slug(part)}.csv",
                   mime="text/csv", icon=":material/download:")
