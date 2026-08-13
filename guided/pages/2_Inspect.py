"""One recommendation, opened up - with the six rules in the left rail.

The rail is the point of this version. Everything the analysis does is a funnel
of six rules, and a reader who cannot see which rule a unit failed has to take
the verdict on trust. Here they never have to: the rail is filled in with this
unit's own figures, the failing rule is marked, and the main area explains the
consequence rather than repeating the numbers.

Selection lives in the rail too, so the whole width belongs to the evidence.
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

from h0app import (charts, data, evidence, freshness, paths,  # noqa: E402
                   pipeline, text, ui)

st.set_page_config(page_title="Inspect · H0", page_icon=":material/query_stats:",
                   layout="wide")
ui.inject()
freshness.guard()

S = data.SEQ
RUN, SETUP, LOAD = "Run — PCS/HR", "Setup", "Run — HRS/LOAD"
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
    choices = [RUN] + ([SETUP] if data.has_setup() else []) \
        + ([LOAD] if data.has_load() else [])
    kind = st.radio("Analysis", choices, index=_idx(choices, _kind(pre)),
                    help="Three analyses, three different kinds of standard. "
                         "They are never pooled.")

    if kind == SETUP:
        universe = data.setup_book("01_FamilyRollup")
    elif kind == LOAD:
        universe = data.load_book("02_FamilyRollup")
    else:
        universe = None

    ops = (sorted(universe.OPERATION.unique()) if universe is not None
           else data.operation_list())
    operation = st.selectbox("Operation", ops,
                             index=_idx(ops, pre.get("OPERATION")))

    empty_op = False
    if universe is None:
        universe = data.all_units(operation)
        empty_op = universe.empty

    if not empty_op:
        scoped = (universe[universe.OPERATION == operation]
                  if "OPERATION" in universe.columns else universe)
        pairs = sorted({(f, p) for f, p in zip(scoped.FAMILY, scoped.PART_TYPE)})
        labels = [f"{f} · {p}" for f, p in pairs]
        want = f"{pre.get('FAMILY')} · {pre.get('PART_TYPE')}"
        chosen = st.selectbox("Family", labels, index=_idx(labels, want))
        family, part_type = pairs[labels.index(chosen)]

        fam_rows = scoped[(scoped.FAMILY == family)
                          & (scoped.PART_TYPE == part_type)]
        seqs = sorted(int(s) for s in fam_rows[S].unique())
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
            opts = ["The family as a whole"] + sorted(
                members.PART_ID.unique().tolist())
            pick = st.selectbox("Judged at", opts,
                                index=_idx(opts, pre.get("PART_ID")))
            part_id = None if pick == "The family as a whole" else pick

if empty_op:
    # The rail must not simply vanish here. This is the moment its promise -
    # "it always tells you where a unit stands" - is most load-bearing, because
    # "nothing could be tested" is the single answer people are most likely to
    # mistake for "the standard is fine".
    with st.sidebar:
        st.divider()
        st.markdown("### Does it pass the six rules?")
        ui.gate_rail(st, [{"passed": False, "name": "Enough work orders",
                           "value": "nothing left to test"}]
                     + [{"passed": False, "name": g, "value": "not reached"}
                        for g in ["Consistently off the standard",
                                  "Not a fluke of testing many at once",
                                  "Sure of the direction",
                                  "Big enough to be worth it",
                                  "Enough hours to matter"]])
        st.markdown(ui.chip("✕ no verdict is possible either way", ui.FAIL),
                    unsafe_allow_html=True)
        st.caption("Not the same as the standard being fine. There is no "
                   "evidence here in either direction.")
        st.divider()
        ui.legend(st)
    st.title("Inspect")
    st.warning(
        f"**{operation}** produced no testable unit. Every work order in scope "
        f"was closed with a token booking (≤ {pipeline.TOKEN_HOURS} h), which "
        f"records that a ticket was closed rather than how long the job took. "
        f"There is no duration in them to judge a standard against.",
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
st.caption(f"{part_type} · {operation} · routing step {seq}"
           + (f" · part {part_id}" if part_id else " · the family as a whole"))

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

# ---- the rail ---------------------------------------------------------------
with st.sidebar:
    st.divider()
    st.markdown("### Does it pass the six rules?")
    blocker = ui.gate_rail(st, gates)
    if needs_human:
        st.markdown(ui.chip("! all six — but check this one by hand", ui.WARN),
                    unsafe_allow_html=True)
    elif kindof == "act":
        st.markdown(ui.chip("✓ all six — change this standard", ui.PASS),
                    unsafe_allow_html=True)
    elif blocker is not None:
        st.markdown(ui.chip(f"✕ stopped at rule {blocker + 1} — leave as is",
                            ui.FAIL), unsafe_allow_html=True)
    st.divider()
    ui.legend(st)

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
k = st.columns([1, 1, 1, 1.3])
k[0].metric("Standard now", ui.fmt(w["current"]))
if kindof == "act":
    # delta_color is always "off". Streamlit's default colours a delta by its
    # arithmetic sign, so a rate correctly coming DOWN prints red - a colour
    # meaning something other than what the legend says, in the one product
    # whose rule is that colour always carries meaning.
    k[1].metric("Change it to", ui.fmt(w["suggested"]),
                delta=(f"{(w['suggested'] / w['current'] - 1) * 100:+.1f}%"
                       if pd.notna(w["suggested"]) and pd.notna(w["current"])
                       and w["current"] else None),
                delta_color="off")
else:
    k[1].metric("Change it to", "leave as is",
                help=f"The arithmetic would give "
                     f"{ui.fmt(w['suggested'])}, but this unit did not clear "
                     f"all six rules, so it is not proposed. Shown here only "
                     f"so the number is not hidden.")
k[2].metric("Hours a year", ui.hrs(stats.get("HOURS_DELTA", 0)),
            help="Actual minus master, over the fiscal year, for this unit. "
                 "Positive means the job takes longer than the master allows.")
k[3].metric("Ratio", ui.fmt(stats.get("RATIO"), ".3f"),
            help=f"Actual hours ÷ master hours, outliers removed, across "
                 f"{ui.num(stats.get('N_COUNTED', 0))} counted work orders "
                 f"({ui.num(len(rows))} in scope, "
                 f"{ui.num(len(rows) - stats.get('N_COUNTED', 0))} excluded). "
                 f"Above 1.0 the job takes longer than the master.")
st.markdown(ui.direction_note(target, run_type))

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
if ok is True:
    st.caption(f":material/verified: Rebuilt independently from "
               f"`{paths.CACHE.name}` — {why}.")
elif ok is False:
    st.error(f"**These figures no longer reproduce** — {why}. Either the "
             f"workbook was written from a different extract, or an exclusion "
             f"rule has drifted. Do not key this in until the pipeline has "
             f"been re-run.", icon=":material/report:")

if freshness.operation_is_stale(operation):
    st.warning(f"`{pipeline.parts_workbook(operation).name}` is older than the "
               f"extract — the stored figures are from an earlier run.",
               icon=":material/warning:")

st.divider()

# ---- evidence ---------------------------------------------------------------
c1, c2 = st.columns([1.35, 1])

with c1:
    st.subheader("Every work order against its standard")
    st.caption("One dot per work order, actual hours against master. Left of "
               "the line the job beat the master, right of it the job took "
               "longer. Hover any dot for the work order behind it.")
    chart = charts.distribution(rows, stats, height=330)
    if chart is not None:
        st.altair_chart(chart, width="stretch")
    with st.expander("Why the shaded band and the red line can disagree"):
        st.markdown(charts.ci_caption(stats))

with c2:
    st.subheader("What counted, and what did not")
    counts = rows.STATUS.value_counts()
    for status, n in counts.items():
        colour = charts.COLOURS.get(status, ui.MUTE)
        st.markdown(
            ui.chip(f"{n} · {status}", colour), unsafe_allow_html=True)
    if stats.get("BASIS") and stats["BASIS"] != "single master":
        st.info(f"**{stats['BASIS']}** — the standard changed during the "
                f"period, and work orders run under the superseded value "
                f"describe a standard that no longer exists.",
                icon=":material/history:")
    # Gated on the verdict. Unconditional, this told a reader to "apply the
    # ratio to each part's own value" on a screen whose banner said to leave
    # the standard alone - and on a real action it repeated, in different
    # words, the box already shown above the fold.
    spread = stats.get("N_DISTINCT_CURRENT")
    if spread is not None and pd.notna(spread) and int(spread) > 1 \
            and kindof != "act":
        st.caption(f"For information: the parts in this pool run "
                   f"**{int(spread)} different current values**, so "
                   f"'Standard now' is the hours-weighted blend rather than any "
                   f"one stored figure. Nothing to apply — this unit is not "
                   f"proposed for change.")

st.divider()

# ---- the rules, explained ---------------------------------------------------
st.subheader("The six rules, for this unit")
st.caption("Same rail as the sidebar, with the reason each rule exists. All six "
           "must pass before a standard is proposed for change.")
gcols = st.columns(3)
for i, g in enumerate(gates):
    with gcols[i % 3]:
        with st.container(border=True):
            colour = ui.PASS if g["passed"] else (
                ui.FAIL if i == blocker else ui.MUTE)
            mark = "✓" if g["passed"] else ("✕" if i == blocker else "–")
            st.markdown(
                f'<span style="color:{colour};font-weight:700">{mark} '
                f'{i + 1}. {g["name"]}</span>', unsafe_allow_html=True)
            st.markdown(f"**{g['value']}**")
            st.caption(g["detail"])

st.divider()

# ---- the rows ---------------------------------------------------------------
st.subheader("The work orders behind this")
st.caption("Every labour ticket in scope, including the ones that did not "
           "count. This is the row-level data the conclusion was drawn from.")
show = rows.copy()
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
