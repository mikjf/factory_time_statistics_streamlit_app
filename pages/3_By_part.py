"""One part: what changes, and what was examined and deliberately left alone.

The second half carries as much weight as the first. A part owner who cannot
find their part on the queue has no way to tell "we tested this and the standard
holds" from "we never had enough work orders to say", and those are completely
different answers to give a director.
"""

import pathlib
import sys

import streamlit as st

# parent.parent is streamlit_app/, where ftsapp lives. Every page inserts it
# itself rather than relying on Overview.py having run first: deep-link to a
# page in a fresh session and the import failed with ModuleNotFoundError:
# no module named 'ftsapp'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ftsapp import data, freshness, pipeline, ui  # noqa: E402

st.set_page_config(page_title="FTS · By part", page_icon=":material/qr_code:",
                   layout="wide")
ui.inject()
freshness.guard()

S = data.SEQ


# ONE SPEC, TWO TABLES. Both tables on this page carry the same twelve columns:
# the lower one every step that was examined, the upper one the subset that
# changes. They were two separate definitions until 2026-09-02 and had drifted
# into different headers, a different order and a different word for the same
# thing - which is what this page needed a pass for. A second copy is how that
# happens, so there is one.
#
# WHAT THE CALLER HANDS OVER is a frame already carrying the STEP_COLS names.
# For the lower table that is data.part_steps as it comes. For the upper one it
# is data.edits renamed onto them, because THE VALUES THERE MUST BE THE UPDATE
# LIST'S, not this frame's:
#
# On one family-route unit checked while this was written, the update list
# read 70.0 -> 40.6 where part_steps read 69.9 -> 40.5. Only the first pair is
# keyable. (No part number here on purpose - stage_streamlit_for_github.py
# sweeps this file for identifiers and will refuse to stage one.)
#
# A family row of part_steps carries the pool's average current value; the
# update list carries THIS part's own stored value with the family factor
# applied. 26 of 169 family units have members running more than one current
# value, so the two genuinely disagree - and only one of them is keyable.
# ELEVEN SHARED, AND A TWELFTH THAT DIFFERS. The two tables agree on
# everything up to Change %. The last column is the one thing they legitimately
# disagree about:
#
#   lower table  VERDICT           its rows are mostly NOT changes, and the
#                                  verdict is what separates "tested and the
#                                  standard holds" from "never enough evidence
#                                  to say" - the distinction the page exists for
#   top table    MASTER_OPS_ROWID  its rows are ALL changes, so a verdict there
#                                  reads "update" on every row, in five
#                                  different phrasings that name the pipeline's
#                                  sheets rather than the reader's field:
#                                  UPDATE RUN_MASTER and UPDATE RUN are the SAME
#                                  edit to the SAME column, OPERATION.RUN, from
#                                  two different analyses. Checked on all 2'468
#                                  rows: the verdict is fully determined by
#                                  Analysis and Applies to, both already on the
#                                  row and both written in the app's own words.
#                                  The routing row is what the line is keyed
#                                  against, and is not derivable from anything.
STEP_TABLE_COLS = ["OPERATION", S, "ANALYSIS", "APPLIES_TO", "N_WO",
                   "HOURS_DELTA", "NOW", "SUGGESTED", "RATIO", "EFFECT",
                   "CHANGE_PCT"]

# Both signed figures carry their sign, the same way the Review queue and
# Overview's Net column do: a change and a delta printed bare read as totals.
STEP_TABLE_FMT = {"N_WO": ",.0f", "HOURS_DELTA": "+,.1f", "NOW": ",.2f",
                  "SUGGESTED": ",.2f", "RATIO": ",.3f", "CHANGE_PCT": "+,.1f"}

STEP_TABLE_CONFIG = {
    "OPERATION": st.column_config.TextColumn("Operation"),
    S: st.column_config.NumberColumn("Step", format="%d"),
    # Same header, same three strings and the same helper as the Review
    # queue - see ui.analysis_name for why naming the analysis also names
    # the field it edits.
    # NOT width="small": that clipped "Run PCS/HR" to "Run PCS/HI" and
    # "whole family" to "whole famil", turning both columns into things the
    # reader has to guess at.
    "ANALYSIS": st.column_config.TextColumn(
        "Analysis",
        help="Which of the three this row came from, which also says which "
             "field it is about: both run analyses judge RUN, setup judges "
             "SETUP_HRS. Setup is only ever judged per family."),
    # THE PART NUMBER, the same as the Review queue's column of this
    # name - see ui.applies_to. It repeats the page title on those rows,
    # which is the price of the two screens saying a thing one way.
    "APPLIES_TO": st.column_config.TextColumn(
        "Applies to",
        help="The part number where this part had enough work orders to be "
             "judged on its own; the whole family where its family supplied "
             "the evidence. On a whole family row every figure beside it is "
             "the family's."),
    "N_WO": st.column_config.NumberColumn(
        "Work orders", help="How many the figures on this row are based "
                            "on. For setup, the real setups left after the "
                            "skipped ones and the crew mismatches come out."),
    # "Δ Hours", the same header the Review queue uses for the same
    # column. It read "Δ h" here and "Hours" there.
    "HOURS_DELTA": st.column_config.NumberColumn(
        "Δ Hours",
        help=f"From the start of {pipeline.FY_LABEL} to the last booking in "
             f"the extract — a running total, not a rate. Positive means "
             f"the jobs take longer than the master allows."),
    "NOW": st.column_config.NumberColumn(
        "Now", help="The value the master carries today."),
    # BLANK IS A STATEMENT HERE, not a gap. Two of the three analyses write
    # a suggested value only where they propose one, and the family rollups
    # write one even where their own verdict says nothing could be judged -
    # which data.part_steps strips back out. So: a number appears only
    # where the analysis stands behind it, and Ratio carries the size of
    # the gap on every other row.
    "SUGGESTED": st.column_config.NumberColumn(
        "Suggested",
        help="Only where the analysis proposes one. Blank does not mean "
             "zero and does not mean the standard is right — Verdict says "
             "which, and Ratio says how far off it was measured."),
    "RATIO": st.column_config.NumberColumn(
        "Ratio", help="Actual hours divided by master hours, across the "
                      "work orders that counted. It is on every row, "
                      "including the ones with nothing to key."),
    "EFFECT": st.column_config.TextColumn(
        "Effect",
        help="What the measurement says about the time the standard should "
             "allow, which is not the direction the field's own number "
             "moves — slowing down a PCS/HR standard means a lower rate. "
             "It describes the measurement, not an instruction: Verdict "
             "says whether anything is being proposed."),
    "CHANGE_PCT": st.column_config.NumberColumn(
        "Change %",
        help="How much the field's own number changes, which is not how "
             "the hours change. Blank wherever Suggested is."),
    "VERDICT": st.column_config.TextColumn("Verdict", width="medium"),
    # Left ungrouped on purpose - a routing row id is an identifier, not a
    # quantity, and 1'234'567 invites reading it as one.
    #
    # THE FIELD'S OWN NAME, not a description of it. The banner above this
    # table says "MASTER_OPS_ROWID", the download's column is MASTER_OPS_ROWID
    # and the Review queue's master row updater leads with it under that name -
    # so a header reading "Routing row" was the one place the same thing went
    # by a different word, on the page that names it most.
    # WHOSE ROUTING ROW IT IS, spelled out. A row reading "Applies to: whole
    # family" with a single id beside it invites reading the id as the
    # family's. It is not: this page is about ONE part, edits() is one row per
    # part per unit, and the id here is that part's own. The family decision
    # behind it covers a routing row for every part it touches - 184 of the 193
    # family units in the update list span more than one, up to 73 - and the
    # place that lists them all is the Review queue's master row updater.
    #
    # A FAMILY ROW MIXES SCOPES ON PURPOSE, which is the root of the confusion:
    # Work orders, Delta Hours and Ratio are the FAMILY's, because that is the
    # pool the verdict was reached on; Now, Suggested and this id are THIS
    # PART's, because that is what somebody would key.
    "MASTER_OPS_ROWID": st.column_config.NumberColumn(
        "Master Ops RowID", format="%d",
        help="This part's own OPERATION row - what the change is keyed "
             "against, so future work orders inherit it. On a whole family "
             "row the decision still covers every part in the family, and "
             "each of those has a different routing row of its own: the "
             "Review queue's master row updater lists them all."),
}


def steps_table(df, part, last):
    """Render the table. `last` is the twelfth column - see STEP_TABLE_COLS.

    Returns the frame that was shown, so a caller can hand it straight to a
    download rather than rebuilding the same selection.
    """
    cols = STEP_TABLE_COLS + [last]
    shown = df.copy()
    shown["ANALYSIS"] = [ui.analysis_name(t, r)
                         for t, r in zip(df.TARGET, df.RUN_TYPE)]
    shown["APPLIES_TO"] = [ui.applies_to(part, lv) for lv in df.LEVEL]
    shown["EFFECT"] = [ui.effect_from_ratio(r) for r in df.RATIO]
    # The one place a raw verdict string reaches a reader - everywhere else the
    # app reduces it through evidence.outcome first. Mapped on the display
    # frame, so the CSV below carries the same words as the screen.
    if "VERDICT" in shown.columns:
        shown["VERDICT"] = [ui.verdict_name(v, rt)
                            for v, rt in zip(shown.VERDICT, df.RUN_TYPE)]
    st.dataframe(ui.swiss_grid(shown[cols], STEP_TABLE_FMT),
                 hide_index=True, width="stretch",
                 column_config=STEP_TABLE_CONFIG)
    return shown[cols]

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

# ALL THREE ANALYSES, since 2026-09-01. This walked 05_AllUnits across every
# operation, which is Run PCS/HR at part level and nothing else - so a part
# whose setup or whose HRS/LOAD run had been examined saw no trace of it here
# unless it produced an edit, and the banner below promised more than the table
# under it delivered. data.part_steps carries the reconciliation notes.
steps = data.part_steps(part)

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

# THE NAME BOTH DOWNLOADS USE. Only the fields that MEAN anything here: a By
# part download covers every operation and every step of ONE part, so the
# operation, sequence and route that name an Inspect download have no single
# value to print. What is left is family, part type and the part, most
# specific last.
#
# ui.part_tag with with_title=False: ADV / ANDV, the two words the subtitle
# above and the Overview rankings use, rather than the 23 characters of
# "ARTICOLO NON DI VENDITA" carrying one bit.
#
# OFF _id, NOT _idx. _idx is the extract's part index and is only the LAST of
# the three sources _id falls back through, so a part that reached this page
# through its edits or its steps could have an empty _idx - and the name is
# built here, above both downloads, rather than beside one of them.
_name = ("_".join(str(x) for x in [
    _id.FAMILY.iat[0], ui.part_tag(_id.PART_TYPE.iat[0], with_title=False),
    part]) if _id is not None and len(_id) else str(part))
st.title(f"{part}")
if _id is not None and len(_id):
    # THE DESCRIPTION ALWAYS COMES FROM THE EXTRACT, not from _id. Only one of
    # the three sources carries it, and this line is the one place in the whole
    # tool that says what the part physically IS - so it must not appear or
    # vanish depending on which source happened to answer.
    bits = [str(_id.FAMILY.iat[0]), ui.part_tag(_id.PART_TYPE.iat[0])]
    if len(_idx):
        bits.append(str(_idx.PART_DESCRIPTION.iat[0]))
    ui.subtitle(st, " · ".join(bits))

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
    # theirs flagged. This banner is now the ONLY place the flag reaches a
    # reader on this page - the Flagged? column came out when the two tables
    # were matched - so the count below is not a summary of a column, it is the
    # whole signal. Per-row, the Review queue's master row updater carries it.
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
        # NO MARKDOWN HERE: ui.verdict_banner escapes this string before it
        # reaches the page, so asterisks would print as asterisks.
        + "Master Ops RowID is this part's own routing row to update, so "
          "future work orders inherit it. Where a change applies to the whole "
          "family, every other part in it has a routing row of its own \u2014 "
          "the Review queue's master row updater lists all of them.")
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
    # THE SAME TWELVE COLUMNS AS THE TABLE BELOW, filtered to the rows
    # that change - asked for on 2026-09-02, and why steps_table exists.
    #
    # BUILT FROM data.edits, NOT by filtering part_steps, though the columns
    # are the lower table's. edits() is the update list: one row per part per
    # unit, carrying the value that gets keyed against that part's routing row.
    # Filtering part_steps would have been fewer lines and would have printed
    # the family's pooled figures on every family row - the worked example is
    # on steps_table above.
    #
    # HOURS_DELTA AND VERDICT are the two the update list does not carry, so
    # they are joined from part_steps on the unit AND the level. The level is
    # not optional in that key: a part can hold both a PART row and a FAMILY
    # row for one operation and step, and they are different pools. Checked
    # over the whole extract on 2026-09-02 - all 2'468 edit rows across 954
    # parts matched exactly one steps row, none unmatched, none duplicated.
    #
    # Delta Hours on a family row is the FAMILY's, exactly as in the table
    # below. The caption under this heading says so.
    #
    # ROUTING ROW AND FLAGGED? CAME OUT with everything else that was not in
    # the lower table. They were the only two columns this table had that the
    # other did not, and MASTER_OPS_ROWID is now on neither - see the banner
    # above, which still names it.
    _mine = mine.rename(columns={"TARGET_COLUMN": "TARGET", "ROUTE": "LEVEL",
                                 "EVIDENCE_N": "N_WO", "CURRENT": "NOW",
                                 "RECOMMENDED": "SUGGESTED",
                                 "CHANGE": "CHANGE_PCT"})
    _key = ["OPERATION", S, "TARGET", "RUN_TYPE", "LEVEL"]
    _n = len(_mine)
    # HOURS_DELTA only now. VERDICT was joined here too until the column was
    # swapped for the routing row; nothing on this table reads it any more.
    _mine = _mine.merge(steps[_key + ["HOURS_DELTA"]], on=_key, how="left")
    assert len(_mine) == _n, "the steps join changed the row count"
    # THIS TABLE IS FOR READING, NOT FOR KEYING - decided 2026-09-02. It briefly
    # had a download of its own, added when matching the lower table's columns
    # had taken MASTER_OPS_ROWID off the screen and the id needed to live
    # somewhere. Putting the id back in the table settled that, and a second
    # download a scroll above the page's own download was two buttons answering
    # one question.
    #
    # REVIEW_FLAG WENT WITH IT and is now nowhere on this page as a column. The
    # count still reaches the reader through the verdict banner above, which
    # says how many are flagged and why. The list somebody actually keys from
    # is the Review queue's master row updater, which carries the flag per row.
    steps_table(_mine, part, "MASTER_OPS_ROWID")
    if (~mine.ROWID_FOUND.fillna(False)).any():
        st.warning("Some rows have a blank routing row and cannot be keyed "
                   "until one is found for them.", icon=":material/warning:")

st.divider()
st.subheader("Every step of this part that was examined")

if steps.empty:
    st.info(f"No step of **{part}** is in scope for any of the three analyses. "
            f"Either the part did not run this year, or every step of it sits "
            f"outside them — most often because the routing step is no longer "
            f"in the current master revision. **Methodology** lists every "
            f"exclusion.",
            icon=":material/info:")
    st.stop()

# Same two states as the Outcome column on Methodology, and worded the same.
# This page said "tested and it holds" / "never enough data to say" for what
# that one calls "tested and holds" / "not enough evidence" - one distinction,
# three phrasings, in a tool whose claim is that its words do not vary.
#
# AND WHOSE FIGURES THEY ARE. A family row carries the family's work orders and
# the family's hours, not this part's share of them - which is the one thing a
# reader could take from this table and be wrong about, since the page is about
# a single part. Applies to says it per row; this says it once, before the
# first row rather than after the last.
st.caption("Including the ones left alone. **Verdict** distinguishes 'tested "
           "and holds' from 'not enough evidence'. On a *whole family* row "
           "every figure is the family's, this part included.")

# THE REVIEW QUEUE'S COLUMN ORDER, and for the same reasons it settled on:
# which routing row, what kind, how wide and how big, then what to do. Family
# and Part type are not columns here - they are the subtitle, one line up, and
# identical on every row of a single part's table.
#
# DESCRIPTION IS GONE FROM HERE for the same reason: it moved into the subtitle
# on 2026-09-01, where it is read once instead of repeated down a medium-width
# column that was the same string on every row.
#
# MASTER H AND ACTUAL H WENT WITH IT. Δ Hours is their difference and the only
# one of the three anyone acts on; Ratio is the same pair as a proportion. The
# per-work-order rows they summarise are one click away in Inspect, which is
# where a reader who wants the two absolutes should be looking anyway.
shown_steps = steps_table(steps, part, "VERDICT")
# ONE LABEL PER ROW, not per step. The table now carries up to three analyses
# and two levels at the same operation and step, and Inspect opens a different
# unit for each - so a label naming only the operation and the step would have
# offered several rows under one entry and silently opened the first of them.
_labels = [f"{r.OPERATION} · step {int(r[S])} · {ui.analysis_name(r.TARGET, r.RUN_TYPE)}"
           f" · {ui.applies_to(part, r.LEVEL)}" for _, r in steps.iterrows()]
jump = st.selectbox(
    "Open one of these in Inspect", ["—"] + _labels,
    help="Carries the selection across, so Inspect opens on this row rather "
         "than making you pick the analysis, operation, family and step "
         "again.")
if jump != "—":
    r = steps.iloc[_labels.index(jump)]
    # PART_ID IS None ON A FAMILY ROW. Inspect's "Judged at" picker indexes on
    # pre["PART_ID"] and falls back to its first option - the whole family -
    # when it finds nothing there, so None is what selects the family unit.
    st.session_state["unit"] = {
        "TARGET": r.TARGET, "RUN_TYPE": r.RUN_TYPE, "OPERATION": r.OPERATION,
        "FAMILY": r.FAMILY, "PART_TYPE": r.PART_TYPE, "SEQ": int(r[S]),
        "LEVEL": r.LEVEL, "PART_ID": part if r.LEVEL == "PART" else None,
    }
    st.page_link("pages/2_Inspect.py",
                 label=f"Open {jump} in Inspect",
                 icon=":material/query_stats:")
# THE SAME NAMING AS INSPECT, which builds operation_family_ADV_seq_route_part
# and reads "where, which product, how it was judged, at what grain - most
# specific last". This one carried the part number alone, so a folder of these
# sorted by part number and told the reader nothing about what any of them was
# until it was opened.
#
# _name is built once, up beside _id - see there for what goes into it.
st.download_button("Download this part's steps as CSV",
                   shown_steps.to_csv(index=False).encode("utf-8"),
                   file_name=f"fts_by_part_{pipeline.slug(_name)}.csv",
                   mime="text/csv", icon=":material/download:")
