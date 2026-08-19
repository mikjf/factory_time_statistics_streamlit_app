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

# parent.parent.parent is streamlit_app/, where h0app lives. parent.parent is
# guided/ - which held only because Overview.py runs first in an ordinary visit
# and inserts the right path. Deep-link to a page in a fresh session and the
# import failed with ModuleNotFoundError: no module named 'h0app'.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from h0app import (charts, data, evidence, freshness,  # noqa: E402
                   pipeline, text, ui)

st.set_page_config(page_title="Inspect · H0", page_icon=":material/query_stats:",
                   layout="wide")
ui.inject()
freshness.guard()

S = data.SEQ
RUN, SETUP, LOAD = "Run — PCS/HR", "Setup", "Run — HRS/LOAD"
# One phrase, two casings: WHOLE is a menu option and takes a capital, and
# WHOLE_INLINE runs inside a sentence. Held here rather than written out at
# each of the three places it appears, because the picker's value is compared
# against it - a typo in one copy silently turns the family into a part.
WHOLE = "Family as a whole"
WHOLE_INLINE = "family as a whole"
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
    st.markdown("### What to look at")
    # The two run analyses together, setup last: RUN_MASTER under PCS/HR and
    # RUN under HRS/LOAD are the same field on the same routing line held in two
    # different units, so they belong beside each other. Setup is a different
    # field and a different question.
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
            opts = [WHOLE] + sorted(members.PART_ID.unique().tolist())
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
    st.page_link("pages/4_Not_standards.py",
                 label="See what that costs, on Not standards changes",
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
gates = text.gates(stats, w["q"])
kindof = evidence.outcome(w["verdict"], stats)

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
blocker = next((i for i, g in enumerate(gates) if not g["passed"]), None)

# ---- verdict ----------------------------------------------------------------
field = {"SETUP_HRS": "SETUP_HRS",
         "RUN": "RUN (hours per load)" if run_type == "HRS/LOAD"
                else "RUN_MASTER (pieces per hour)"}[target]

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
    "hold": (f"Rule {blocker + 1} of 6 stopped it: {gates[blocker]['name'].lower()}"
             f" — {gates[blocker]['value']}." if blocker is not None else ""),
    "blocked": (gates[blocker]["value"] if blocker is not None else ""),
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
k = st.columns([1, 1, 1.1, 1, 1])
k[0].metric("Standard now", ui.fmt(w["current"]))

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
    # .st-key-h0-inline-delta rules in ui.py. It is a qualifier on the number,
    # read in the same breath as it, and on its own line it took a line of the
    # row and left this metric taller than the four beside it.
    with k[2].container(key="h0-inline-delta-change"):
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
# "Hours from FY26", not "Hours a year". The window is the fiscal year TO DATE -
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
# are called Standard now and Measured, and the pill it lines up with says
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
with k[3].container(key="h0-inline-delta-hours"):
    st.metric(f"Hours from {pipeline.FY_LABEL}", _shown,
              delta=("slower" if _shown.startswith("+")
                     else "faster" if _shown.startswith("-") else None),
              delta_color="off",
              help=f"Actual minus master for this unit, from the start of "
                   f"{pipeline.FY_LABEL} to the last booking in the extract. "
                   f"Positive means the jobs take longer than the master "
                   f"allows.")
k[4].metric("Ratio", ui.fmt(stats.get("RATIO"), ".3f"),
            help=f"Actual hours ÷ master hours, outliers removed, across "
                 f"{ui.num(stats.get('N_COUNTED', 0))} counted work orders "
                 f"({ui.num(len(rows))} in scope, "
                 f"{ui.num(len(rows) - stats.get('N_COUNTED', 0))} excluded). "
                 f"Above 1.0 the job takes longer than the master.")
# st.caption, not st.markdown. This sentence is a note about how to read the
# two numbers above it, which is what every other caption on the page does; at
# body weight it sat in the reading flow as though it were a finding of its own.
# The v1 page has always rendered it as a caption - the guided one was the odd
# man out.
st.caption(ui.direction_note(target, run_type))

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
# and "as the routing holds it" - so the three lines of caption that used to
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
    ui.rule_results(st, gates, per_row=2)

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

    st.markdown(
        f"| | ratio | as the routing holds it |\n"
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
        f"| **judged at** | | {_at} |")

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
               f"'Standard now' is the hours-weighted blend rather than any "
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
# The link that replaced them is now at the foot of the page rather than here.
# Two reasons, and the second is the one that matters: it reads better as the
# way out of a finished page than as an interruption before the row-level data;
# and st.page_link raises inside Streamlit's AppTest harness, which aborts the
# script, so anything below it is invisible to the test suite. Sitting here it
# hid the work-order table and its download from every automated run.

# ---- the rows ---------------------------------------------------------------
st.subheader("The work orders behind this")
st.caption("Every labour ticket in scope, including the ones that did not "
           "count. This is the row-level data the conclusion was drawn from.")
# evidence.ROWS, not every column: the frame also carries the pre-formatted
# strings the chart tooltip needs, which are display text and would sort as text
# in a column. The CSV below takes the same eight, so the download keeps
# matching what is on screen.
show = rows[evidence.ROWS].copy()
show["LAST_DATE"] = pd.to_datetime(show.LAST_DATE, errors="coerce")
st.dataframe(
    ui.swiss_grid(show, {"TOTAL_QTY": ",.0f", "HOURS_MASTER": ",.4f",
                         "HOURS_WORKED": ",.4f", "RATIO": ",.3f"}),
    hide_index=True, width="stretch", height=380,
    column_config={
        "WORK_ORDER": st.column_config.TextColumn("WORK ORDER"),
        "LAST_DATE": st.column_config.DateColumn("LAST BOOKED",
                                                 format="YYYY-MM-DD"),
        # No `format` on the numeric columns - the Styler owns the display and
        # a NumberColumn format would override it back to commas.
        "TOTAL_QTY": st.column_config.NumberColumn("PIECES"),
        "HOURS_MASTER": st.column_config.NumberColumn("MASTER h"),
        "HOURS_WORKED": st.column_config.NumberColumn("ACTUAL h"),
        "RATIO": st.column_config.NumberColumn("ACTUAL ÷ MASTER"),
        "STATUS": st.column_config.TextColumn("COUNTED?", width="large"),
    })

tag = "_".join(str(x) for x in [operation, family, part_type, seq,
                                part_id or "family"])
st.download_button("Download these work orders as CSV",
                   show.to_csv(index=False).encode("utf-8"),
                   file_name=f"h0_evidence_{pipeline.slug(tag)}.csv",
                   mime="text/csv", icon=":material/download:")

# Last on the page, deliberately - see the note where the six explained rule
# cards used to be. It is the way out of a finished page, and it is the one
# element that blinds the test harness to everything after it.
st.divider()
st.page_link("pages/6_Methodology.py",
             label="What each of the six rules is for, and where it is applied",
             icon=":material/rule:")
