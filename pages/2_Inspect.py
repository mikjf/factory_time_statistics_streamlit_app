"""One recommendation, opened up.

Everything the analysis does is a funnel of six rules, and a reader who cannot
see which rule a unit failed has to take the verdict on trust. Here they never
have to: "How this was decided" carries all six with this unit's own figures and
names the one that stopped it.

That block used to be a rail in the sidebar, and for a while the page carried
both. The main area won: it is where the evidence is, it has the width for the
figures, and a reader looking at a chart should not have to track a summary of
it in the corner of their eye.

The sidebar now does one thing - choose what to look at - so the whole width
belongs to the unit.
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

from ftsapp import (charts, data, evidence, freshness,  # noqa: E402
                   pipeline, text, ui)

st.set_page_config(page_title="FTS · Inspect", page_icon=":material/query_stats:",
                   layout="wide")
ui.inject()
freshness.guard()

S = data.SEQ
RUN, SETUP, LOAD = "Run — PCS/HR", "Setup", "Run — HRS/LOAD"
# One phrase, two casings - see ui. It moved there when the Review queue's
# Applies to column needed the same words: that column compacts the workbook's
# "all parts of this family" down to this phrase, so the two pages have to agree
# on it, and the picker below compares its value against WHOLE by string.
WHOLE, WHOLE_INLINE = ui.WHOLE, ui.WHOLE_INLINE
pre = st.session_state.get("unit") or {}


def _kind(p):
    if p.get("TARGET") == "SETUP_HRS":
        return SETUP
    return LOAD if p.get("RUN_TYPE") == "HRS/LOAD" else RUN


def _idx(options, value, default=0):
    try:
        return list(options).index(value)
    except (ValueError, AttributeError):
        return default


# ---- selection, in the rail -------------------------------------------------
with st.sidebar:
    ui.side_title(st, "What to look at")

    # ---- ONLY WHAT CHANGES -------------------------------------------------
    # Fewer than one unit in fifty carries a proposed change. Unfiltered, the
    # four pickers below offer over a thousand combinations for the run analysis
    # alone, and the overwhelming majority land on "leave this standard alone"
    # or "not enough evidence" - which is the honest answer for those units and
    # useless as a way to find the ones that need keying in.
    #
    # NO COUNTS WRITTEN DOWN. They were here as "237 of 11'777" and both halves
    # went stale, the second one twice. The ratio is the argument; the tiles on
    # Overview and the Review queue carry the live figures.
    #
    # FIRST IN THE RAIL, above the analysis it does not itself filter. It is the
    # bigger fork: this decides whether the rail offers the units that changed
    # or every unit examined, and the radio then navigates inside whichever of
    # those was chosen. It sat
    # between the radio and the pickers, which is exactly the boundary of what it
    # affects and reads as belonging to neither.
    #
    # OFF BY DEFAULT. Inspect is also the page somebody opens to ask why THEIR
    # part is not on the list, and a filter that hid it would answer by making
    # the question unaskable. It is also where Review queue lands, and that
    # arrives with a unit already chosen.
    #
    # Sourced from 01_Actions, which is the update list's own record of what is
    # proposed - the same sheet Review queue reads and the same cache. Deriving
    # it instead from each unit's verdict would mean reading five different
    # verdict columns across five workbooks to reproduce a list that already
    # exists.
    only_changes = st.toggle(
        "Only where a change is proposed", value=False,
        help="Hides every unit the six rules held or could not judge, so the "
             "pickers below offer only the standards this analysis proposes "
             "editing.")

    # The two run analyses together, setup last: both edit RUN on the same
    # routing line, one holding a rate and one a duration, so they belong beside
    # each other. Setup is a different field and a different question.
    choices = [RUN] + ([LOAD] if data.has_load() else []) \
        + ([SETUP] if data.has_setup() else [])
    kind = st.radio("Analysis", choices, index=_idx(choices, _kind(pre)),
                    help="Three analyses, three different kinds of standard. "
                         "They are never pooled.")

    # ---- FAMILY FIRST, then the operations that family is routed through ----
    # It used to be operation first, because the PCS/HR run analysis writes one
    # workbook per operation and that workbook was the only way to know which
    # families existed. data.run_index() removes that constraint - it reads all
    # 47 once and caches on their mtimes - so the picker can now follow how the
    # people using it think: my product line, then where in its routing.
    #
    # Setup and HRS/LOAD needed nothing: each already has a single rollup
    # covering every operation.
    if kind == SETUP:
        universe = data.setup_book("01_FamilyRollup")
    elif kind == LOAD:
        universe = data.load_book("02_FamilyRollup")
    else:
        universe = data.run_index()

    # Applying the toggle declared at the top of the rail. It is read here
    # rather than there because it filters `universe`, which only exists once
    # the analysis is known - a widget's value is available the moment it is
    # declared, so where it renders and where it is used need not be the same
    # place.
    act_keys = act_parts = act_fams = None
    if only_changes:
        _a = data.actions()
        _a = _a[(_a.TARGET == "SETUP_HRS") if kind == SETUP
                else ((_a.TARGET == "RUN")
                      & (_a.RUN_TYPE == ("HRS/LOAD" if kind == LOAD
                                         else "PCS/HR")))]
        # int() on the sequence: 01_Actions and the rollups agree on the column
        # name, not always on whether it arrived as 2500 or 2500.0, and a tuple
        # key compares those unequal.
        def _key(f, p, o, q):
            return (f, p, o, int(q))
        act_keys = {_key(f, p, o, q) for f, p, o, q
                    in zip(_a.FAMILY, _a.PART_TYPE, _a.OPERATION, _a[S])}
        # Which LEVEL is proposed matters for "Judged at": a family can hold
        # while one of its parts changes, and the point of the filter is to
        # offer the level that actually changed.
        act_parts = {_key(f, p, o, q) + (pid,) for f, p, o, q, pid
                     in zip(_a.FAMILY, _a.PART_TYPE, _a.OPERATION, _a[S],
                            _a.PART_ID) if pd.notna(pid)}
        act_fams = {_key(f, p, o, q) for f, p, o, q, lvl
                    in zip(_a.FAMILY, _a.PART_TYPE, _a.OPERATION, _a[S],
                           _a.LEVEL) if str(lvl).upper() == "FAMILY"}
        universe = universe[[
            _key(f, p, o, q) in act_keys for f, p, o, q
            in zip(universe.FAMILY, universe.PART_TYPE, universe.OPERATION,
                   universe[S])]]

    pairs = sorted({(f, p) for f, p in zip(universe.FAMILY, universe.PART_TYPE)})
    empty_op = not pairs

    if not empty_op:
        # ADV / ANDV here too, so the picker and the subtitle it produces say
        # the same word. with_title=False: a selectbox option is plain text and
        # cannot carry a hover, and any markup would be shown literally.
        #
        # The label is built by a function rather than an f-string in two
        # places, because `want` has to reproduce it exactly - the pre-selection
        # from Review queue is matched by string, so a difference of one space
        # silently lands the reader on the wrong family.
        def _fam_label(f, p):
            return f"{f} · {ui.part_tag(p, with_title=False)}"

        labels = [_fam_label(f, p) for f, p in pairs]
        want = _fam_label(pre.get("FAMILY"), pre.get("PART_TYPE"))
        chosen = st.selectbox("Family", labels, index=_idx(labels, want))
        family, part_type = pairs[labels.index(chosen)]

        fam_rows = universe[(universe.FAMILY == family)
                            & (universe.PART_TYPE == part_type)]
        # Only the operations this family is actually routed through. The list
        # was every operation in the plant; on a family with four steps, forty
        # of the forty-eight led to an empty page.
        ops = sorted(fam_rows.OPERATION.unique())
        operation = st.selectbox("Operation", ops,
                                 index=_idx(ops, pre.get("OPERATION")))

        scoped = fam_rows[fam_rows.OPERATION == operation]
        seqs = sorted(int(s) for s in scoped[S].unique())
        seq = st.selectbox("Routing step", seqs, index=_idx(seqs, pre.get("SEQ")),
                           help="The same operation can appear at several "
                                "points of one routing and is a different job "
                                "each time.")

        part_id = None
        if kind == SETUP:
            st.caption("Judged per family. Setup units average under four "
                       "worked hours across a whole year, so no single part "
                       "ever clears a materiality gate alone.")
        else:
            members = (data.all_units(operation) if kind == RUN
                       else data.load_book("01_PartUnits"))
            members = members[(members.FAMILY == family)
                              & (members.PART_TYPE == part_type)
                              & (members[S] == seq)]
            # "Family as a whole", not "The family as a whole". Under a label
            # that already reads "Judged at", the article adds a word without
            # adding a distinction - the alternatives are part numbers, and no
            # one needs "the" to tell a family from one of those.
            parts = sorted(members.PART_ID.unique().tolist())
            opts = [WHOLE] + parts
            # With the filter on, this picker offers the LEVELS that changed,
            # not every level that exists. A family that holds while one of its
            # parts is corrected would otherwise open on the family and show
            # "leave this standard alone" - the filter having promised the
            # opposite. Both levels can change, and then both are offered.
            if only_changes:
                _k = (family, part_type, operation, int(seq))
                opts = ([WHOLE] if _k in (act_fams or ()) else [])                     + [x for x in parts if _k + (x,) in (act_parts or ())]
                opts = opts or [WHOLE]
            pick = st.selectbox("Judged at", opts,
                                index=_idx(opts, pre.get("PART_ID")))
            part_id = None if pick == WHOLE else pick

if empty_op:
    # WHAT THIS BRANCH MEANS CHANGED with the family-first picker. It used to
    # fire when the chosen OPERATION had no testable unit - every work order a
    # token booking - and it named that operation. Now the picker is built from
    # the units themselves, so an operation in that state is simply never
    # offered, and this fires only if an entire analysis has none: a workbook
    # missing, or a pipeline run that produced nothing.
    #
    # It must not name `operation` any more. There is no operation selected at
    # this point - the widget below the family never rendered - and the old
    # message would have raised NameError on the one path it exists to handle.
    st.title("Inspect")
    st.warning(
        f"**{kind}** has no units to inspect. Either its workbook has not been "
        f"produced yet, or every work order in scope was closed with a token "
        f"booking (≤ {pipeline.TOKEN_HOURS} h), which records that a ticket was "
        f"closed rather than how long the job took.\n\n"
        f"**This is not the same as the standards being fine.** None of the six "
        f"rules could be applied, so there is no evidence here in either "
        f"direction.",
        icon=":material/info:")
    st.page_link("pages/4_Additional_findings.py",
                 label="See what that costs, on Additional findings",
                 icon=":material/arrow_forward:")
    st.stop()

# ---- the evidence -----------------------------------------------------------
if kind == SETUP:
    rows, stats = evidence.setup(operation, family, part_type, seq)
    target, run_type = "SETUP_HRS", "-"
elif kind == LOAD:
    rows, stats = evidence.load(operation, family, part_type, seq, part_id)
    target, run_type = "RUN", "HRS/LOAD"
elif part_id is not None:
    rows, stats = evidence.run_part(operation, family, part_type, part_id, seq)
    target, run_type = "RUN", "PCS/HR"
else:
    rows, stats = evidence.run_family(operation, family, part_type, seq)
    target, run_type = "RUN", "PCS/HR"

st.title(f"{family}")
# ui.subtitle, not st.caption. This line is what makes every number below it
# mean something - which part type, which step, one part or the whole family -
# and it was set in the same 14px grey as a footnote under a chart.
#
# WHAT is judged, then WHERE. Part type, then whether this is one part or the
# whole family, then the step it happens at - so the two facts about the pool
# sit together instead of being split by the operation and its sequence, which
# are one fact in two words and belong at the end as the address.
#
# ADV / ANDV, the same abbreviation the Overview rankings use, with the full
# wording on hover. Spelled out it was the longest thing on the line and the
# least informative - two of the four segments say what this unit IS, and
# "Articolo di vendita" pushed them along without adding anything a reader of
# this page does not already know.
ui.subtitle(st, " · ".join([
    ui.part_tag(part_type),
    f"part {part_id}" if part_id else WHOLE_INLINE,
    str(operation),
    f"routing step {seq}"]))

if not stats or rows.empty:
    st.info("No work orders in scope for this combination.",
            icon=":material/info:")
    st.stop()

w = evidence.verdict_for(target, run_type, operation, family, part_type, seq,
                         part_id)
rule_state = text.rule_status(stats, w["q"])
kindof = evidence.outcome(w["verdict"], stats)

# THE VALUE TO KEY IS THIS UNIT'S OWN, on every part-level unit. verdict_for
# reads the unit sheets; the execution sheets carry RM_RECOMMENDED, and since
# 2026-08-26 the two agree on every part row - a part that cleared the six
# rules keeps its own figure. See data.actions.
#
# _own is kept anyway. It costs nothing, and it is the guard: if it ever
# diverges from the value to key, the rule upstream has moved and this page
# should not quietly show one number while the workbook holds another.
#
# Only an action carries a row here, which is exactly when "Change it to"
# renders a number - a held or untestable unit shows "leave as is" and never
# reads w["suggested"].
_own = w["suggested"]
_act = data.action_row(target, run_type, operation, family, part_type, seq,
                       part_id)
if _act is not None and pd.notna(_act.TO_KEY):
    w["suggested"] = float(_act.TO_KEY)
_from_family = (_act is not None and pd.notna(_own)
                and pd.notna(w["suggested"])
                and abs(float(_own) - float(w["suggested"])) > 0.101)

# TODAY'S MASTER, beside the standard the jobs ran under. "Standard now" used to
# be the only standard on this page and it was never the master: it is the
# work orders' own copy of the routing, which is what the six rules test and
# what stays the yardstick here. The master can have moved since - a new
# revision, or an edit in place - and on some actions it already holds the
# value proposed. The pipeline works all of that out per part for every action,
# and on an action this page reads it from the update list (data.today_rows).
#
# AN ACTION STAYS AN ACTION when it is already done. The banner, the value to
# key and every figure the six rules produced are untouched; the status is
# stated beside them, the way ACTION_STATUS sits beside the action in the
# workbook.
#
# EVERY OTHER UNIT GETS IT TOO, rebuilt from the extract (evidence.today_parts)
# for the parts in this unit's evidence. That is the page somebody opens to ask
# why their part is NOT on the list, and whether the master has moved since is
# part of the answer. Only the action-specific notes - already done, partly
# done, still to key, check - stay on actions.
#
# ON AN ACTION BOTH COPIES EXIST, and they are compared part by part: the same
# Standard WO, the same Standard today, the same kind of change. The update
# list stays the one shown; a disagreement is an error on screen, never
# resolved quietly in either direction.
_tkind = evidence.kind_of(target, run_type)
_exec = (data.today_rows(target, run_type, operation, family, part_type, seq,
                         part_id) if _act is not None else None)
if _exec is not None and len(_exec):
    td = data.today_summary(_exec)
    _chk = evidence.today_parts(_tkind, operation, seq, _exec.PART_ID)
    _m = _exec[["PART_ID", "STANDARD_WO", "STANDARD_TODAY",
                "STANDARD_CHANGE"]].merge(
        _chk if _chk is not None else
        pd.DataFrame(columns=["PART_ID", "STANDARD_WO", "STANDARD_TODAY",
                              "STANDARD_CHANGE"]),
        on="PART_ID", how="left", suffixes=("", "_X"))

    def _same(x, y):
        x, y = pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")
        return ((x - y).abs() <= 1e-4) | (x.isna() & y.isna())

    _today_bad = int((~(_same(_m.STANDARD_WO, _m.STANDARD_WO_X)
                        & _same(_m.STANDARD_TODAY, _m.STANDARD_TODAY_X)
                        & (_m.STANDARD_CHANGE.astype(str)
                           == _m.STANDARD_CHANGE_X.astype(str)))).sum())
    td_action = True
else:
    _parts = [part_id] if part_id else rows.PART_ID.dropna().unique().tolist()
    td = data.today_summary(evidence.today_parts(_tkind, operation, seq, _parts))
    _today_bad = 0
    td_action = False
_unit_word = "part" if part_id else "family"

# Does the queue flag this one for a human? The band is on the RATIO, not on
# the percentage change, because the change is asymmetric - a rate that
# quadruples reads +300% while one cut to a quarter reads -75% and can never
# pass -100%, so flagging on the change would catch only the increases.
#
# This page is the one people are told to open "when you disagree with a
# number", and it was the one page that never showed the flag: the most extreme
# action in the list proposes cutting a rate by 95% and arrived here under a
# plain green "change this standard", with nothing to suggest a second look.
_r = stats.get("RATIO")
needs_human = (kindof == "act" and _r is not None and pd.notna(_r)
               and (_r < pipeline.REVIEW_LO or _r > pipeline.REVIEW_HI))

# ---- THE RAIL IS GONE, and with it the chip and the colour legend -----------
# It was the point of this page when the main area repeated the numbers and
# explained the consequence. It is not any more: "How this was decided" carries
# the same six rules with the same figures, marks the blocker in words, and sits
# above the fold; the banner above it states the outcome the chip used to; and
# the legend now has three states a reader meets in the cards themselves.
#
# Three copies of the six rules on one screen was the thing to fix, and the rail
# was the copy furthest from the evidence it describes. The sidebar keeps what
# only it can do - choosing what to look at.
blocker = next((i for i, g in enumerate(rule_state) if not g["passed"]), None)

# ---- verdict ----------------------------------------------------------------
# ui.field_name, not a mapping written out here. The Review queue needs the same
# TARGET + RUN_TYPE -> ERP column translation to name what a row edits, and two
# copies of it is how one page ends up saying RUN where the other says
# RUN_MASTER - for the same row.
field = ui.field_name(target, run_type, unit=True)

headline = {
    "act": (f"Change this standard — but check it first" if needs_human
            else f"Change this standard — edit {field}"),
    "hold": "Leave this standard alone",
    "blocked": "Not enough evidence to judge this",
    "unknown": "No verdict recorded for this unit",
}[kindof]
detail = {
    "act": ("It passed all six rules, and the change it proposes is large "
            "enough to want a second pair of eyes." if needs_human
            else "It passed all six rules."),
    "hold": (f"Rule {blocker + 1} of 6 stopped it: {rule_state[blocker]['name'].lower()}"
             f" — {rule_state[blocker]['value']}." if blocker is not None else ""),
    "blocked": (rule_state[blocker]["value"] if blocker is not None else ""),
    "unknown": "The workbook has no row for this combination.",
}[kindof]
ui.verdict_banner(st, headline, "review" if needs_human else kindof, detail)
if needs_human:
    ui.review_warning(st, w["current"], w["suggested"], stats.get("RATIO"),
                      pipeline.REVIEW_LO, pipeline.REVIEW_HI)

# Only show a keyable number when the verdict is to key one in. Rendering the
# workbook's SUGGESTED beside "Leave this standard alone" put a live-looking
# 172.82 and a green +8.1% under a banner saying to do nothing - and it was
# inconsistent about it too, so nobody could learn when the number meant "do
# this". The arithmetic stays available below, labelled as what it is.
#
# SIX TILES since "Standard today" joined: the two standards side by side, then
# the argument. `k` is shifted by one after the second tile, so k[1]..k[4]
# below still name Measured, Change it to, Hours and Work orders counted.
k = st.columns([1, 1, 1, 1.1, 1, 1])
# "Standard WO", not "Standard now". It is the work orders' copy, and "now"
# invited reading it as the master today - which is the tile beside it.
k[0].metric("Standard WO", ui.fmt(w["current"]),
            help="The standard the work orders ran under: each work order's "
                 "own copy of the routing, taken from the latest one completed. "
                 "This is what the six rules test, and what every figure on "
                 "this page is measured against.")
if td is None:
    k[1].metric("Standard today", "—",
                help="No master line for this step was found in the extract "
                     "for these parts, so there is no value to show.")
else:
    _nl = td["no_line"]
    with k[1].container(key="fts-inline-delta-today"):
        st.metric(
            "Standard today",
            (ui.fmt(td["value"]) if td["value"] is not None
             else f"{td['n_values']} values" if td["n_values"]
             else "no line"),
            delta=("no line today" if _nl == td["n"]
                   else "unchanged" if td["moved"] == 0
                   else "moved" if td["moved"] == td["n"]
                   else f"moved on {td['moved']} of {td['n']}"),
            delta_color="off",
            help=(f"The master as it stands in the latest extract, on the "
                  f"part's current revision ({', '.join(td['cur_rev']) or '—'}); "
                  f"the work orders ran on revision "
                  f"{', '.join(td['wo_rev']) or '—'}. "
                  + ("Unchanged since the jobs ran."
                     if td["moved"] == 0 and not _nl else
                     "; ".join(f"{n} {h}" if td["n"] > 1 else h
                               for h, n in td["how"].items()
                               if h != "unchanged") + ".")
                  + (f" Across the {td['n']} parts it holds "
                     f"{td['n_values']} different values."
                     if td["value"] is None and td["n_values"] > 1 else "")
                  + ("" if td_action else
                     " Read from the extract: this unit is not on the update "
                     "list.")))
k = k[1:]

# MEASURED, between the standard and the decision. The row now reads as the
# argument it is: this is the standard, this is what the jobs actually came to,
# so this is what to do about it - and the ratio at the end is the arithmetic
# joining the first two.
#
# On a unit that passes all six rules this equals "Change it to", and that is
# not a redundancy to hide: for a rate, current / ratio IS the pool's achieved
# rate, so the value proposed is precisely what the shop floor already does.
# The help says so. On a unit that fails, the two differ - measured still has a
# value, and the decision is to leave the standard alone - which is the case the
# old four-metric row could not express at all, and papered over with a tooltip.
_mk = evidence.kind_of(target, run_type)
_op = "÷" if _mk == evidence.K_PCSHR else "×"
# Derived rather than read off the workbook - see evidence.measured_value. The
# SUGGESTED columns are empty on every no-change row of the setup and load
# sheets, so reading them printed a dash on exactly the units where this is the
# interesting number.
_measured = evidence.measured_value(w["current"], stats.get("RATIO"), _mk)
k[1].metric("Measured", ui.fmt(_measured),
            help=f"What this pool actually came to, in the same unit as the "
                 f"standard: {ui.fmt(w['current'])} {_op} "
                 f"{ui.fmt(stats.get('RATIO'), '.3f')}. Where all six rules "
                 f"pass this is also the value proposed — the new standard is "
                 f"what the jobs already achieve. Where a rule stops the unit, "
                 f"this is still what was measured; it is simply not proposed.")
if kindof == "act":
    # delta_color is always "off". Streamlit's default colours a delta by its
    # arithmetic sign, so a rate correctly coming DOWN prints red - a colour
    # meaning something other than what the legend says, in the one product
    # whose rule is that colour always carries meaning.
    #
    # The key puts the change beside the value rather than under it - see the
    # .st-key-fts-inline-delta rules in ui.py. It is a qualifier on the number,
    # read in the same breath as it, and on its own line it took a line of the
    # row and left this metric taller than the four beside it.
    with k[2].container(key="fts-inline-delta-change"):
        st.metric("Change it to", ui.fmt(w["suggested"]),
                  delta=(f"{(w['suggested'] / w['current'] - 1) * 100:+.1f}%"
                         if pd.notna(w["suggested"]) and pd.notna(w["current"])
                         and w["current"] else None),
                  delta_color="off")
else:
    # No number here, and no apology for it either. "Measured" two columns left
    # now carries the arithmetic openly, so this metric no longer has to smuggle
    # it into a tooltip to avoid hiding it.
    k[2].metric("Change it to", "leave as is",
                help="This unit did not clear all six rules, so no change is "
                     "proposed. What the evidence measured is beside it.")
# "Hours since FY26 start", not "Hours a year" and not "Hours from FY26". The
# window opens at FY_START and never closes - there is no upper bound anywhere
# in the pipeline - so once FY27 bookings arrive this figure will span two
# fiscal years. "from FY26" reads as BELONGING TO FY26 and would quietly become
# false on 1 Oct 2026; "since FY26 start" says where the window opens and
# stays true however far past it the extract runs.
#
# The window is the fiscal year TO DATE -
# it opens at FY_START and runs to the last labour ticket, which today is about
# ten months - so "a year" invited a reader to treat a part-year total as an
# annual one. The label is built from pipeline.FY_LABEL, itself derived from
# FY_START, so it cannot outlive the year it names.
_hd = stats.get("HOURS_DELTA", 0)
# WHICH DIRECTION, in a word, in the slot Streamlit keeps for a delta. The sign
# is on the number already, but a minus in front of hours is ambiguous until you
# know whether hours going down is the jobs being quick or the standard being
# cut - and it is the first, which is not obvious.
#
# It used to be our own chip in a block underneath, pulled up by a negative
# margin matched to Streamlit's furniture by eye. As a real delta it IS that
# furniture: the same element as the "+17.8%" two columns left, so the two can
# no longer drift apart under a Streamlit upgrade. One word - "than the master"
# is the only thing it could be measured against on a row whose other metrics
# are called Standard WO and Measured, and the pill it lines up with says
# "+17.8%", not "+17.8% against the standard".
#
# delta_color is "off" here for the reason it is off there: this is a fact about
# the pool, not a verdict, and green/red/amber are spoken for by the six rules.
# The pill reads the PRINTED figure, not the raw one. Rounded to whole hours, a
# delta of +0.34 prints "0 h" - and a pill saying "slower" beside a number
# saying nothing happened is a contradiction the reader has to resolve. It is
# not a rare shape either: across the unit sheets, 3'761 run units and 1'100
# load units round to zero from a non-zero delta, against 515 and 18 that are
# flat zero. Taking the direction off ui.hrs's own output rather than off _hd
# makes the two agree by construction instead of by coincidence.
_shown = ui.hrs(_hd, sign=True)
with k[3].container(key="fts-inline-delta-hours"):
    st.metric(f"Hours since {pipeline.FY_LABEL} start", _shown,
              delta=("slower" if _shown.startswith("+")
                     else "faster" if _shown.startswith("-") else None),
              delta_color="off",
              help=f"Actual minus master for this unit, from the start of "
                   f"{pipeline.FY_LABEL} to the last booking in the extract. "
                   f"Positive means the jobs take longer than the master "
                   f"allows.")
# HOW MUCH EVIDENCE, rather than the ratio that used to sit here. The ratio is
# on this page five times over - the table below states it in both scales, rule
# 4 gives its band, rule 5 restates it as a percentage, and the chart's whole
# axis is it - while the weight of evidence behind it appeared nowhere in the
# summary. "Is this based on enough?" is the first thing anyone asks of a
# proposed change, and it was an expander away.
#
# N_COUNTED, the same figure and the same word as the chart's legend below
# ("17 · counted"), so the two agree on sight. It is deliberately NOT the
# "17 tested" of rule 1: tested is what entered the statistical test, counted is
# what survived the outlier filter into the ratio, and on 40 of 150 sampled
# units those differ. The tooltip therefore names all three stages, so a reader
# who spots the gap against rule 1 finds it explained rather than contradicted.
#
# "Work orders counted", not "n" or "evidence" - the words a reader meets in the
# chart legend below and in the tooltip's own breakdown.
k[4].metric("Work orders counted", ui.num(stats.get("N_COUNTED", 0)),
            help=f"{ui.num(len(rows))} in scope, "
                 f"{ui.num(stats.get('N_TESTED', 0))} tested, "
                 f"{ui.num(stats.get('N_COUNTED', 0))} counted once outliers "
                 f"were removed. The ratio is measured across the counted "
                 f"ones.")
# st.caption, not st.markdown. This sentence is a note about how to read the
# two numbers above it, which is what every other caption on the page does; at
# body weight it sat in the reading flow as though it were a finding of its own.
# A caption is what every other note-about-the-numbers on this page is.
st.caption(ui.direction_note(target, run_type))

# WHAT TODAY'S MASTER SAYS ABOUT THIS ACTION, in the same words as
# TODAY_STATUS: "already done" means today's master is within MIN_EFFECT (10%)
# of the value proposed. Blue, not green - green is "rule passed" on this page,
# and this is a fact about the ERP, not a verdict. Actions only: on any other
# unit there is nothing proposed to be done or still to key.
#
# BELOW THE METRIC ROW AND ITS RATE/DURATION NOTE, not under the banner (user,
# 2026-10-06): they qualify the two standards on the left of that row, so they
# are read after them; the banner keeps only what the six rules decided.
#
# THE CHECK NAMES ITS NUMBERS. "Outside 0.25-4.0 of the value the master holds
# today" was accurate and abstract; the reader has to see the part, the value
# proposed, today's value and the multiple between them to judge it. The first
# three flagged parts are named, the rest counted.
_runit = evidence.UNITS[_mk][1]


def _with_unit(v):
    return f"{ui.fmt(v)} {_runit}"
if td is not None and td_action:
    _n, _d, _mv = td["n"], td["done"], td["moved"]
    _of = "" if _n == 1 else f" ({_n} parts)"
    if _d and _d == _n:
        st.info(f"**Already done in today's master.** "
                + (f"It holds {ui.fmt(td['value'])}, " if td["value"] is not None
                   else "Every part already holds a value ")
                + f"within 10% of the {ui.fmt(w['suggested'])} proposed — "
                  f"nothing left to key on this {_unit_word}{_of}.",
                icon=":material/task_alt:")
    elif _d:
        _left = _n - _d
        st.info(f"**Partly done — {_d} of {_n} parts** already hold a value "
                f"within 10% of the proposal in today's master. "
                + (f"The other {_left} are" if _left > 1 else "The other one is")
                + " still to key; **By part** lists which.",
                icon=":material/task_alt:")
    elif _mv:
        st.info(f"**Today's master has moved since these jobs ran**"
                + ("" if _mv == _n else f", on {_mv} of {_n} parts")
                + f", but not to within 10% of the proposal, so this is still "
                  f"to key."
                + (f" Against today's master the change is "
                   f"**{td['change_pct']:+.1f}%**."
                   if td["change_pct"] is not None else ""),
                icon=":material/history:")
    if td["review"]:
        _rec = next(c for c in ("RM_RECOMMENDED", "SETUP_HRS_RECOMMENDED",
                                "RUN_RECOMMENDED") if c in _exec.columns)
        _fl = _exec[_exec.REVIEW_FLAG_TODAY.notna()
                    & (_exec.REVIEW_FLAG_TODAY.astype(str) != "")]
        _band = _fl[_fl.REVIEW_FLAG_TODAY.astype(str).str.contains("outside")]
        _typ = _fl[_fl.REVIEW_FLAG_TODAY.astype(str).str.contains("run type")]
        _said = []
        for r in _band.head(3).itertuples():
            _v, _t = getattr(r, _rec), r.STANDARD_TODAY
            _x = f" — {_v / _t:.1f}×" if _t else ""
            _said.append(("the proposal is " if _n == 1 else
                          f"on {r.PART_ID} the proposal is ")
                         + f"{_with_unit(_v)} against {_with_unit(_t)} in "
                           f"today's master{_x}")
        _txt = "; ".join(_said)
        if len(_band) > 3:
            _txt += f"; and {len(_band) - 3} more of the {_n} parts"
        _msg = "**Check this against today's master.** "
        if _said:
            _msg += (_txt[0].upper() + _txt[1:]
                     + f" — outside the {pipeline.REVIEW_LO}–"
                       f"{pipeline.REVIEW_HI} band where a change is flagged "
                       f"for manual review.")
        if len(_typ):
            _msg += (f" On {len(_typ)} of {_n} parts today's master no longer "
                     f"holds this run type, so the value proposed does not "
                     f"apply as it stands.")
        st.warning(_msg, icon=":material/pan_tool:")
if _today_bad:
    st.error(f"**Today's master disagrees between the update list and the "
             f"extract** on {_today_bad} of {len(_exec)} parts. Either the "
             f"update list was written from a different extract, or this "
             f"page's rebuild has drifted from the pipeline. Do not rely on "
             f"\"Standard today\" or the status shown until the pipeline has "
             f"been re-run.", icon=":material/report:")

# WHY "CHANGE IT TO" IS NOT WHAT THIS PART MEASURED. On these units the rail
# says a part number and the metrics show a measured value the recommendation
# does not match, with nothing on screen accounting for the difference - which
# reads as a fault rather than as a decision. Both figures are named so the
# reader can see the size of the gap, and the reason is the workbook's own.
#
# An st.info rather than a caption: it is not a note about how to read the
# numbers above it, it is a fact about which of two numbers to key.
# INVERTED 2026-08-26. This used to explain why the value to key was the
# family's rather than this part's. That rule is gone - a part clearing the six
# rules keeps its own figure - so a difference here is now a fault, not a
# feature, and the box says so. Do not restore the old wording.
if _from_family:
    st.warning(
        f"**This page and the workbook disagree.** The part measured "
        f"**{ui.fmt(_own)}**, but the execution sheet carries a different "
        f"value to key. A part that cleared all six rules on its own evidence "
        f"should keep its own figure, so this should not happen. Check "
        f"`02_RunUpdateList` before keying it. The workbook records the basis "
        f"as *{_act.TO_KEY_BASIS}*.",
        icon=":material/error:")

# Some family actions carry no single value to key in, because the family
# runs several different current standards. Those rows say "divide each part's
# own value by the ratio" - so the ratio has to be on the page, and it is, in
# the metric above.
if kindof == "act" and (pd.isna(w["suggested"]) or pd.isna(w["current"])):
    st.info(
        f"**This family runs more than one current standard**, so there is no "
        f"single number to key in. Apply the ratio to each part's own value: "
        f"{'divide' if target == 'RUN' and run_type == 'PCS/HR' else 'multiply'}"
        f" it by **{ui.fmt(stats.get('RATIO'), '.3f')}**. **By part** lists the "
        f"resulting value for every affected part.", icon=":material/call_split:")

got = evidence.stored(target, run_type, operation, family, part_type, seq,
                      part_id)
ok, why = evidence.reconcile(stats, got[0] if got else None,
                             got[1] if got else None)
# REPORTED BY EXCEPTION. The success line - "rebuilt independently, reproduces
# the workbook" - said the same thing on every unit that was working correctly,
# which is nearly all of them, and cost a line above the fold on each. The check
# still runs on every unit; it now only speaks when it has something to say.
#
# The failure branch below is deliberately louder than the removed caption was
# quiet: it is an st.error telling the reader not to key the number in.
if ok is False:
    st.error(f"**These figures no longer reproduce** — {why}. Either the "
             f"workbook was written from a different extract, or an exclusion "
             f"rule has drifted. Do not key this in until the pipeline has "
             f"been re-run.", icon=":material/report:")

if freshness.operation_is_stale(operation):
    st.warning(f"`{pipeline.parts_workbook(operation).name}` is older than the "
               f"extract — the stored figures are from an earlier run.",
               icon=":material/warning:")

st.divider()

# ---- what the result looks like ---------------------------------------------
# ABOVE THE CHART, not below it. On "How to read it" this pair comes last,
# because that page is teaching you to read the picture and the outcome is the
# payoff. Here the reader arrives already holding a recommendation and wants to
# know whether to trust it; the six marks and the two scales answer that in one
# screen, and the chart below is the backing they can check afterwards.
#
# THE FULL-DETAIL RULE CARDS THAT USED TO SIT LOWER DOWN ARE GONE. With this
# block added the page carried the six rules three times - the sidebar rail, a
# compact set here, and a set of cards with an explanatory paragraph each. What
# each rule stops is worth reading once, and Methodology owns it.
#
# A HEADING, BUT NO CAPTIONS. The two blocks are self-describing - six ticks
# and crosses against six named rules, and a table whose own header says "ratio"
# and "as the jobs ran it" - so the three lines of caption that used to
# introduce them were paying rent above the fold for nothing. The heading is a
# different matter: it names what the pair IS, and without one the section sat
# between the verdict and the chart with nothing to say which question it
# answers.
#
# "How this was decided", not "What the result looks like". The banner above
# says WHAT was decided and the chart below is the EVIDENCE; this block is the
# working in between - the checks on the left, the figures they were applied to
# on the right. It also stays true when the answer is to leave the standard
# alone, which "the result" does not, quite.
st.subheader("How this was decided")

_rc, _tc = st.columns(2)

with _rc:
    # fill: the six end level with the table, which is a row taller since
    # "master today" joined it.
    ui.rule_results(st, rule_state, per_row=2, fill=True)

with _tc:
    # _mk and _measured come from the metric row above - one derivation per
    # page, so the table and the metric can never show different numbers for
    # the same thing.
    _now = evidence.rate_txt(w["current"], _mk)
    _then = evidence.rate_txt(_measured, _mk)
    _ratio = stats.get("RATIO")
    _lo, _hi = stats.get("CI_LOW"), stats.get("CI_HIGH")

    # Every row below has to survive a unit that is NOT an action, which the
    # example on "How to read it" never is. Three differences follow.
    #
    # 1. The change in the routing's own unit is computed here rather than read
    #    from CHANGE_PCT: a non-action unit has no row in 01_Actions to read it
    #    from, and the arithmetic is still worth showing. From _measured, which
    #    every unit has, rather than from the workbook's SUGGESTED, which most
    #    no-change units leave empty.
    _pct = ((_measured / w["current"] - 1) * 100
            if _measured is not None and pd.notna(w.get("current"))
            and w["current"] else None)
    # 2. The band may SPAN 1.0 here. That is rule 4 failing - the evidence is
    #    consistent with the standard being right - and printing "excludes
    #    1.000" on such a unit would state the opposite of the verdict above.
    if _lo is None or pd.isna(_lo) or _hi is None or pd.isna(_hi):
        _band, _band_says = "—", "no interval — too few work orders to test"
    else:
        _band = f"{_lo:.3f} – {_hi:.3f}"
        _band_says = ("excludes 1.000" if not (_lo <= 1.0 <= _hi)
                      else "**spans 1.000** — consistent with the standard "
                           "being right")
    # 3. "to key" is only a number when the verdict says to key one. Otherwise
    #    it says to leave it, and names the rule that decided - the same reason
    #    the metric above prints "leave as is" rather than a live-looking value.
    if kindof == "act":
        _key = (f"**{ui.fmt(w['suggested'])}** — edit `{field}`"
                if pd.notna(w.get("suggested"))
                else f"no single value — apply the ratio to each part")
    elif blocker is not None:
        _key = f"nothing — rule {blocker + 1} of 6 stopped it"
    else:
        _key = "nothing"

    _at = (f"part **{part_id}**" if part_id else
           WHOLE_INLINE
           + (f" — {int(stats['N_PARTS'])} parts pooled"
              if stats.get("N_PARTS") else ""))

    # "as the jobs ran it", not "as the routing holds it": the standard row is
    # the work orders' copy, and the routing as it holds it TODAY is the
    # master-today row - on every unit where a master line was found. One
    # definition (evidence.today_row) shared with the example on How to read it.
    _today_row = evidence.today_row(td, _mk)

    st.markdown(
        f"| | ratio | as the jobs ran it |\n"
        f"|---|---|---|\n"
        f"| **standard** | 1.000 | {_now} |\n"
        f"| **measured** | {ui.fmt(_ratio, '.3f')}"
        + (f" ({100 * (_ratio - 1):+.1f}%)"
           if pd.notna(_ratio) else "")
        + f" | {_then}"
        + (f" ({_pct:+.1f}%)" if _pct is not None else "")
        + f" |\n"
        f"| **95% band** | {_band} | {_band_says} |\n"
        f"| **to key** | | {_key} |\n"
        + _today_row
        + f"| **judged at** | | {_at} |")

st.divider()

# ---- evidence ---------------------------------------------------------------
# FULL WIDTH. "What counted, and what did not" used to sit in a column beside
# this one, listing each status with its count. The counts moved into the
# chart's own legend - "15 · counted" - which is where the colours already are,
# so the panel was a second reading of the same fact taking a third of the row.
st.subheader("Every work order against its standard")
st.caption("One dot per work order, actual hours against master. Left of the "
           "line the job beat the master, right of it the job took longer. "
           "Hover any dot for the work order behind it. The legend counts each "
           "kind.")
chart = charts.distribution(rows, stats, height=330)
if chart is not None:
    st.altair_chart(chart, width="stretch")

# WHAT THE CHART CANNOT DRAW still has to be counted somewhere. A skipped setup
# has no worked hours, so it has no ratio and no dot - it was in the old panel's
# list and would otherwise have vanished with it. Same test the chart applies.
_undrawn = rows[rows.RATIO.isna() | (rows.RATIO <= 0)]
if len(_undrawn):
    st.caption("Not on the chart, having no ratio to place: "
               + ", ".join(f"**{n}** {s}"
                           for s, n in _undrawn.STATUS.value_counts().items())
               + ".")

with st.expander("Why the shaded band and the red line can disagree"):
    st.markdown(charts.ci_caption(stats))

if stats.get("BASIS") and stats["BASIS"] != "single master":
    st.info(f"**{stats['BASIS']}** — the standard changed during the "
            f"period, and work orders run under the superseded value "
            f"describe a standard that no longer exists.",
            icon=":material/history:")

# Gated on the verdict. Unconditional, this told a reader to "apply the ratio to
# each part's own value" on a screen whose banner said to leave the standard
# alone - and on a real action it repeated, in different words, the box already
# shown above the fold.
spread = stats.get("N_DISTINCT_CURRENT")
if spread is not None and pd.notna(spread) and int(spread) > 1 \
        and kindof != "act":
    st.caption(f"For information: the parts in this pool run "
               f"**{int(spread)} different current values**, so "
               f"'Standard WO' is the hours-weighted blend rather than any "
               f"one stored figure. Nothing to apply — this unit is not "
               f"proposed for change.")

st.divider()

# "The six rules, for this unit" USED TO SIT HERE, as six bordered cards each
# carrying an explanatory paragraph. It moved above the chart in compact form -
# see "How this was decided" - because a reader deciding whether to trust a
# recommendation wants the six marks before the evidence, not after it.
#
# The paragraphs did not come with it. They explain what each rule is FOR, which
# is worth reading once rather than on every unit, and Methodology carries them
# in full. Keeping them here as well would have put the six rules on this one
# page three times over: the sidebar rail, the compact set, and these.
#
# A link to Methodology stood at the foot of this page for a while and was
# removed on 2026-08-31: the sidebar reaches Methodology in one click from
# anywhere, so a second route out of a finished page was a button nobody
# needed. Its going has a side benefit - st.page_link raises inside
# Streamlit's AppTest harness and aborts the script, so this page's work-order
# table and download are now visible to the test suite instead of sitting
# below the one element that blinded it.

# ---- the rows ---------------------------------------------------------------
st.subheader("The work orders behind this")
st.caption("Every work order in scope, including the ones that did not "
           "count. This is the row-level data the conclusion was drawn from.")
# evidence.table_cols, not every column: the frame also carries the chart
# tooltip's pre-formatted strings, which are display text and would sort as
# text in a column. The list is route-aware, so setup no longer draws a PIECES
# column it has no quantities for, and PCS/HR gains the achieved rate.
_cols = evidence.table_cols(_mk)
show = rows[_cols].copy()
show["LAST_DATE"] = pd.to_datetime(show.LAST_DATE, errors="coerce")
# HOURS AT 2 DECIMALS, the way every other table in the tool shows them. These
# two were the only 4-decimal columns in the app, and the extra digits bought
# nothing a reader uses: the ratio is computed from the underlying values and
# printed beside them, so it does not depend on reproducing the division by eye.
#
# CHECKED BEFORE CUTTING IT. Across all three routes, 24 work orders hold an
# Actual h that is above zero and rounds to 0.00 - 1 on the run route, 23 on
# setup PCS/HR, smallest 0.0033 h. Every one of them is a token booking or a
# skipped setup, which the Counted? column already names as excluded, so 0.00 is
# the honest reading rather than a lost figure. No Master h rounds to zero: the
# smallest is 0.0074 h on run and 0.1667 h on setup.
st.dataframe(
    ui.swiss_grid(show, {"TOTAL_QTY": ",.0f", "HOURS_MASTER": ",.2f",
                         "HOURS_WORKED": ",.2f", "RATIO": ",.3f",
                         "ACHIEVED_N": ",.2f"}),
    hide_index=True, width="stretch", height=380,
    column_config={
        "WORK_ORDER": st.column_config.TextColumn("Work order"),
        "PART_ID": st.column_config.TextColumn("Part"),
        "LAST_DATE": st.column_config.DateColumn("Last booked",
                                                 format="YYYY-MM-DD"),
        # No `format` on the numeric columns - the Styler owns the display and
        # a NumberColumn format would override it back to commas.
        "TOTAL_QTY": st.column_config.NumberColumn("Pieces"),
        "HOURS_MASTER": st.column_config.NumberColumn("Master h"),
        "HOURS_WORKED": st.column_config.NumberColumn("Actual h"),
        "RATIO": st.column_config.NumberColumn("Actual ÷ master"),
        # The unit in the header, the way MASTER h and ACTUAL h carry theirs,
        # so the cells stay numbers and sort like numbers.
        "ACHIEVED_N": st.column_config.NumberColumn(
            f"Achieved {evidence.UNITS[_mk][1]}"),
        "STATUS": st.column_config.TextColumn("Counted?", width="large"),
    })

# THE DOWNLOAD CARRIES MORE THAN THE SCREEN, which is a deliberate break from
# how this page worked before. Family, part type, operation and standard are one
# value each on screen - the title says all four already - but a CSV opened next
# week, or two of them concatenated in Excel, has no title above it. STANDARD
# comes per row, so a work order that ran under a superseded value exports the
# value it actually ran under rather than today's.
dl = show.copy()
dl.insert(0, "STANDARD", rows["STANDARD"])
# SEQUENCE and OPERATION as two columns, not the hover's "2500 S CALIB.SBAVARE".
# That string is right for a tooltip, where it reads as one address the way a
# routing is spoken - and wrong for a spreadsheet, where a step glued to a name
# cannot be sorted, filtered or pivoted on either half. Split, SEQUENCE stays a
# number and lines up with the column of the same name in the workbooks.
dl.insert(0, "OPERATION", operation)
dl.insert(0, "SEQUENCE", seq)
dl.insert(0, "PART_TYPE", part_type)
dl.insert(0, "FAMILY", family)
# NAMED FOR THE PAGE, then for the unit. Every download in the tool now starts
# with the page that produced it, so a folder of them sorts by where they came
# from and a colleague can be told where to go back to.
#
# ui.part_tag for the part type: "ARTICOLO_NON_DI_VENDITA" is 23 characters
# carrying one bit, and ADV/ANDV is what the subtitle and the Overview rankings
# already say. One mapping, so the filename uses the word the page uses.
#
# THE ANALYSIS IS IN THE NAME, and it has to be. The same unit can be inspected
# under Run PCS/HR, Run HRS/LOAD and Setup, and without this all three
# downloaded as ONE filename - the browser silently appending "(1)", "(2)",
# leaving three files whose only distinguishing feature was the order they were
# saved in. A rate and a duration in indistinguishable files is exactly the
# confusion this tool spends its time preventing.
#
# It sits just before the level, so the name reads: where, which product, how
# it was judged, at what grain - and the most specific part stays last.
_route = _mk if _mk == evidence.K_SETUP else f"RUN_{_mk}"
tag = "_".join(str(x) for x in [operation, family,
                                ui.part_tag(part_type, with_title=False), seq,
                                _route, part_id or "family"])
st.download_button("Download these work orders as CSV",
                   dl.to_csv(index=False).encode("utf-8"),
                   file_name=f"fts_inspect_{pipeline.slug(tag)}.csv",
                   mime="text/csv", icon=":material/download:")
st.caption("The download adds family, part type, routing step, operation and "
           "the standard as columns — one value each here, but the only "
           "way to tell rows apart once two of these files sit in the same "
           "spreadsheet.")

