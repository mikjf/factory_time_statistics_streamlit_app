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
freshness.guard()

S = data.SEQ
edits = data.edits()
parts = sorted(edits.PART_ID.dropna().unique().tolist())

with st.sidebar:
    ui.side_title(st, "Find a part")

    # THE SAME CONTROL AND THE SAME WORDS INSPECT USES. This was a radio -
    # "Parts with a proposed change" against "Any part number" - which made one
    # filter and one input method look like two halves of a single choice. They
    # are not: the filter narrows a list, and typing a part number is a way in
    # that ignores lists entirely. Split apart, each can be what it is, and the
    # phrase a reader learns on Inspect works here unchanged.
    # OFF BY DEFAULT, the same as Inspect's. The page opens on every part the
    # extract knows rather than on the 954 with something proposed - which is
    # the honest starting point for a page whose question is "what about this
    # part", including the answer "nothing, and here is why".
    only_changes = st.toggle(
        "Only where a change is proposed", value=False,
        help="Hides every part the six rules held or could not judge, so the "
             "pickers below offer only the parts this analysis proposes "
             "editing.")

    # Off, the list is every part in the extract - which is why part_index()
    # exists: 1,438 parts are in there and 954 carry an edit, and without a
    # family for the other 484 the filter below would drop them rather than
    # narrow them.
    pool = edits if only_changes else data.part_index()

    # A MULTISELECT WITH A PLACEHOLDER, not a selectbox with an "all" option in
    # the list. "Nothing chosen" is a state the widget already has, so a
    # sentinel entry would put a fake family among the real ones - and the
    # placeholder renders GREY, which is how every other filter in this tool
    # says "nothing picked yet". The Review queue's narrow() does the same.
    #
    # THE LABEL NAMES THE FIELD, THE COUNT RIDES ON THE VALUE, and the part
    # count MOVES when a family is picked - the filter saying out loud what it
    # did without the reader opening the box.
    # THE PICKERS GO INERT WHILE SOMETHING IS TYPED BELOW, because they no
    # longer decide anything and a live-looking control that decides nothing is
    # a lie the reader has to catch. Typing a part number overrides them, and
    # the rail was still showing a family and a part from the list while the
    # page reported a different part entirely.
    #
    # Read from session_state, not from the variable: the text input is
    # rendered AFTER these, so its value on THIS run is only knowable through
    # the key it wrote on the last one. Streamlit reruns on every keystroke
    # commit, so the greying lands on the same rerun as the override.
    TYPED = "by_part_typed"
    overridden = bool(st.session_state.get(TYPED, "").strip())

    fams = sorted(pool.FAMILY.dropna().unique().tolist())
    picked = st.multiselect("Family", fams,
                            placeholder=f"all families ({ui.num(len(fams))})",
                            disabled=overridden)
    if picked:
        pool = pool[pool.FAMILY.isin(picked)]

    shown = sorted(pool.PART_ID.dropna().unique().tolist())
    part = st.selectbox(f"Part ({ui.num(len(shown))})", shown,
                        disabled=overridden) if shown else ""

    # LAST, AND DELIBERATELY SMALL. The selectbox above is searchable - click
    # it and type - so this is NOT how you find a part that exists, and it had
    # its own titled section for a while as though it were. It has one job the
    # picker cannot do: answer for a part number that is NOT in the extract.
    #
    # That answer is worth a control. An empty dropdown says "no match"; the
    # banner this reaches says the number may be wrong OR the part may not have
    # run this fiscal year, and points at the exclusions that decide it. The
    # difference matters to someone quoting a part and asking whether there is
    # any evidence about it at all.
    typed = st.text_input("Look for part",
                          placeholder="paste full part number",
                          key=TYPED).strip()
    if typed:
        part = typed
        # ON_CLICK, NOT A BODY ASSIGNMENT. Writing to a widget's own key after
        # that widget has been instantiated raises StreamlitAPIException; a
        # callback runs before the next rerun builds its widgets, which is the
        # one moment the value can legally be cleared. It also saves the extra
        # rerun an explicit st.rerun() would cost.
        # THE CAPTION AND ITS BUTTON ARE ONE BLOCK. The sentence ends "clear
        # it to go back", so the button it names is the next thing the eye
        # meets - and the keyed container tightens the gap between them, which
        # Streamlit otherwise sets to the same distance it puts between whole
        # sections.
        with st.container(key="fts-tight-clear"):
            st.caption("The pickers above are ignored while this box has "
                       "something in it. Clear it to go back.")
            st.button("Clear", icon=":material/close:", type="tertiary",
                      on_click=lambda: st.session_state.update({TYPED: ""}))


if not part:
    # THE ONLY PLACE THE PAGE NAMES ITSELF. Once a part is chosen the title is
    # the part - Inspect does the same, titling the family and leaving the page
    # name to the sidebar - so "By part" only appears while there is nothing
    # more specific to say.
    st.title("By part")
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

# NO "WHAT WE FOUND" RAIL, removed on 2026-08-31. Every state it reported
# is already stated in the main column, larger and in the reader's line of
# sight: the unknown part, the in-extract-but-unjudgeable part and the count
# of standards to change all arrive as a verdict_banner below, and the steps
# examined and left alone are the table under it, with their verdicts spelled
# out rather than counted. The rail was a second, quieter copy.

# THE SUBJECT IS THE TITLE, exactly as on Inspect - which titles the family and
# puts what qualifies it on the line below. This page is about one part, so the
# part is the heading and the family and type are what qualify it. It used to
# read "By part" over "<family> - ADV - part <number>", which spent the largest
# type on the page name and the smallest on the only thing that changes.
#
# It degrades rather than guesses. Three sources, most specific first: the
# part's own edits, the steps it was examined in, and failing both the extract
# itself, which knows the family of every part that ever ran. A part number that
# is in none of them gets a title and no line under it, which is the honest
# answer - the verdict banner immediately below then says why.
_idx = data.part_index()
_idx = _idx[_idx.PART_ID == part]
_id = mine if len(mine) else (steps if len(steps) else
                              (_idx if len(_idx) else None))
st.title(f"{part}")
if _id is not None and len(_id):
    ui.subtitle(st, " · ".join([str(_id.FAMILY.iat[0]),
                                ui.part_tag(_id.PART_TYPE.iat[0])]))

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
    # NO IDIOM HERE EITHER. "This is not a clean bill of health" stood here
    # until 2026-08-31 - the same English figure of speech the Review queue
    # dropped from its own version of this warning, and for the same reason:
    # decoration sitting exactly where the sentence does its only real work,
    # in front of readers who do not read English figures of speech.
    #
    # The replacement says the thing plainly. It is safe to be blunt here in a
    # way the Review queue's line could not be: that one covers two groups at
    # once, one of which WAS tested and held, so "nothing judged" would have
    # been false of half of them. This block only ever renders for a part where
    # nothing reached a test at all.
    st.markdown(f"""
**Nothing was judged. That is not the same as nothing being wrong.** The
analysis has nothing to say about **{part}** in either direction, which usually
comes down to one of:

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
    # AMBER WHEN ANY OF THEM IS FLAGGED, the same split Inspect makes on a
    # single unit. Amber has one meaning across this whole tool - a person has
    # to look - and it was the one signal this page could not raise: a part
    # whose only proposed change sits outside the 0.25-4.0 band arrived under a
    # plain green "change this standard", while the SAME edit opened on Inspect
    # showed amber. Same row, two different instructions depending on which
    # page you came in by.
    #
    # 104 of 954 parts carry at least one flagged edit, and 4 have every one of
    # theirs flagged. The Flagged? column already shows it per row - but the
    # banner is what gets read first, and it was saying go.
    _flagged = int(mine.REVIEW_FLAG.notna().sum())
    ui.verdict_banner(
        st,
        f"{len(mine)} standard(s) to change"
        + (" — check before keying" if _flagged else ""),
        "review" if _flagged else "act",
        (f"{_flagged} of them {'is' if _flagged == 1 else 'are'} flagged: the "
         f"ratio is outside {pipeline.REVIEW_LO}–{pipeline.REVIEW_HI}, so the "
         f"change is large enough to want a second pair of eyes. "
         if _flagged else "")
        + "MASTER_OPS_ROWID is the routing row to update so future work orders "
          "inherit it.")
    # A HEADING AND ITS CAPTION, like every other table in this tool. This one
    # had neither: the page went from the green verdict straight into column
    # headers, which is what made it read as jammed against the banner rather
    # than as a section of its own. The banner is the verdict; the heading says
    # what the rows below it ARE.
    #
    # The caption moved up here from below the table for the same reason. It
    # explains which way the correction goes, and that is something you need
    # before the first row, not after the last.
    st.subheader("What to change")
    st.caption("A `RUN` row under PCS/HR is a rate and the correction divides; "
               "a `SETUP_HRS` row, or `RUN` under HRS/LOAD, is a duration and "
               "it multiplies.")

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
