"""The distribution chart, and the family bar on the overview.

One decision runs through the whole of the distribution chart: the x axis is
LOG-SCALED but LABELLED AS A RATIO. The test is on ln(actual / master), so a job
that took half the master time and one that took twice it are the same distance
from it and have to look it - on a linear axis the fast half of every
distribution is squashed into a sliver. Nobody in the meeting reads logs, so the
ticks say 0.5 and 2, not -0.69 and 0.69.

TWO WORDS, USED EVERYWHERE: **master** for the standard the ERP holds, **actual**
for what the shop floor booked. They are the terms the workbook and the query
use, so a figure on screen can be traced without translation. Earlier drafts
paraphrased them as "allowed" and "worked", which read more naturally in a
sentence and quietly gave the room a third vocabulary for two things.
"""

import altair as alt
import numpy as np
import pandas as pd

from . import evidence, ui

# Muted for everything excluded, saturated for the rows that carried the number.
#
# NOTHING IN HERE MAY REUSE ui.WARN (#dd9d3d). Amber has one meaning in this
# tool - a human has to look before keying - and OUTLIER was #e8a33d, which
# differs from it by 11 in red and 6 in green and is the same colour to any
# reader. Both were on screen at once on "How to read it": the ! dot in the
# sidebar legend, the set-aside dots in the chart beside it.
#
# PINK, chosen on hue separation rather than on RGB distance. Two earlier
# attempts and why they were wrong:
#
#   #e8a33d amber      - 13 from WARN. The bug.
#   #7fb3d5 pale blue  - far from WARN, but only 71 from MUTE and it reads as a
#                        washed-out "counted", which is what it sat beside.
#   #f0dd7a pale yellow- scores BEST on RGB distance (90) and is still wrong:
#                        hue 50deg against WARN's 36deg. Same hue family, so it
#                        reads as "a lighter warning". Euclidean distance in RGB
#                        does not predict what a reader will confuse.
#
# #d977a8 sits at hue 330deg with a 22deg gap to its nearest neighbour - the
# widest of any candidate - and 114 from WARN. Nothing else here is pink, and
# pink means nothing else in this tool, which is the whole requirement.
COLOURS = {
    evidence.IN: "#2b7bba",
    evidence.OUTLIER: "#d977a8",
    evidence.TOKEN: "#8d6cab",
    evidence.SKIPPED: "#a2705f",
    evidence.CREW: "#7a9a3f",
    evidence.SUPERSEDED: "#8b8b8b",
    evidence.OWN_PART: "#3aa7a7",
    evidence.MULTILOAD: "#c2554d",
}


def _ticks(lo, hi):
    """Powers of two spanning the data - 0.25, 0.5, 1, 2, 4."""
    out, v = [], 1.0
    while v >= lo / 2:
        out.append(v)
        v /= 2
    v = 2.0
    while v <= hi * 2:
        out.append(v)
        v *= 2
    return sorted(out)


def distribution(rows, stats, height=300, legend=True):
    """One dot per work order against the standard it was measured on.

    legend=False suppresses the built-in colour legend, for the one caller that
    puts ui.chart_key() underneath instead. That key lists every status the
    chart can draw rather than the two this unit happens to use, and with both
    on screen four of its rows appeared twice directly above themselves.
    """
    d = rows[rows.RATIO.notna() & (rows.RATIO > 0)].copy()
    if d.empty:
        return None

    # Deterministic jitter. A fresh random draw on every rerun makes the points
    # jump whenever anything on the page changes, which reads as the data
    # moving.
    d["JITTER"] = np.random.default_rng(0).uniform(-1, 1, len(d))

    lo, hi = float(d.RATIO.min()), float(d.RATIO.max())
    ci_lo, ci_hi = stats.get("CI_LOW"), stats.get("CI_HIGH")
    ratio = stats.get("RATIO")
    for v in (ci_lo, ci_hi, ratio, 1.0):
        if v is not None and not pd.isna(v) and v > 0:
            lo, hi = min(lo, float(v)), max(hi, float(v))
    lo, hi = lo * 0.75, hi * 1.35

    present = [s for s in evidence.EXCLUDED_FIRST if s in set(d.STATUS)]
    layers = []

    # ---- the tooltip -------------------------------------------------------
    # Ordered the way somebody reads a dot: WHICH job (part, work order, when,
    # which step), HOW BIG it was, WHAT THE ROUTING SAYS, then the arithmetic
    # that judges it, then what came of it.
    #
    # Part before work order. The part is what carries a standard and what gets
    # edited; the work order is one occasion on which it was made.
    #
    # The standard sits ABOVE the hours and the achieved rate BELOW the ratio,
    # so the four lines read as a sentence: the routing allows 10 pieces an
    # hour, that made 6.000 master hours against 4.230 actual, a ratio of
    # 0.705, and the job in fact ran at 14.184 pieces an hour. Putting the two
    # rates adjacent would have been tidier and would have hidden that the rate
    # moves the OTHER WAY to the ratio, which is the single thing about this
    # analysis people get wrong.
    #
    # FIELDS THAT ARE EMPTY FOR EVERY DOT DRAWN ARE DROPPED, rather than shown
    # as a row of dashes. That is what makes one tooltip definition work for
    # all three routes: setup has no quantity and no achieved rate, HRS/LOAD
    # has no achieved rate but does have a load count, PCS/HR has both and no
    # load count. Each chart shows only the lines it can fill.
    tip_all = [
        ("PART_ID", alt.Tooltip("PART_ID:N", title="part")),
        ("WORK_ORDER", alt.Tooltip("WORK_ORDER:N", title="work order")),
        ("LAST_DATE", alt.Tooltip("LAST_DATE:T", title="last booked")),
        ("OP_TXT", alt.Tooltip("OP_TXT:N", title="operation")),
        ("TOTAL_QTY", alt.Tooltip("TOTAL_QTY:Q", title="pieces",
                                  format=",.0f")),
        ("LOADS", alt.Tooltip("LOADS:N", title="loads")),
        ("STANDARD", alt.Tooltip("STANDARD:N", title="standard")),
        # Pre-formatted strings, not numeric fields with a d3 format: the unit
        # belongs beside the number and Vega cannot append one to a Q field.
        # Two decimals throughout - the precision the ERP stores hours at.
        ("MASTER_TXT", alt.Tooltip("MASTER_TXT:N", title="master")),
        ("ACTUAL_TXT", alt.Tooltip("ACTUAL_TXT:N", title="actual")),
        # THE RATIO KEEPS ITS THIRD DECIMAL, alone on this list. It is computed
        # rather than stored, so there is no false precision to trim - and 1.0
        # is the reference line this whole chart is drawn against, so rounding
        # a genuinely-off 1.004 to "1.00" would say the opposite of the truth
        # at the one value where it matters most.
        ("RATIO", alt.Tooltip("RATIO:Q", title="ratio", format=".3f")),
        ("ACHIEVED", alt.Tooltip("ACHIEVED:N", title="achieved")),
        # title="status", NOT title="". An empty title does not suppress the
        # key - Vega falls back to the FIELD NAME - so this row has been
        # showing a shouted "STATUS" beside eleven lower-case labels.
        ("STATUS", alt.Tooltip("STATUS:N", title="status")),
    ]
    tip = [t for col, t in tip_all
           if col in d.columns and d[col].notna().any()]

    # ---- the reference marks share ONE tooltip -----------------------------
    # The band, the dashed line and the red line are three readings of the same
    # comparison, and a reader hovering any of them is asking the same question:
    # where does this unit sit. Three tooltips each holding a third of the
    # answer made you hunt for the other two, and the band held none at all.
    #
    # Values only. An explanation of what the band IS belongs under the chart,
    # where it can be read once - a hover is for looking something up, not for
    # being taught, and a paragraph in one costs a reader the same seconds
    # every time they check a number.
    has_band = (ci_lo is not None and not pd.isna(ci_lo)
                and not pd.isna(ci_hi))
    has_corr = ratio is not None and not pd.isna(ratio)

    # "measured", NOT "the correction". This chart is drawn for every unit,
    # including the ones that produced no action - and on those the red line is
    # not a correction, because nothing is being corrected. It is where the
    # pool sits, weighted by hours; whether that becomes a correction is the
    # verdict's business, and the verdict is stated in full elsewhere on the
    # page. A label that is true on the action units and false on the rest is
    # worse than one that is true on both.
    #
    # No leading "the" on any of the three: they are keys in a two-column table,
    # not a sentence, and the article only pushed every value further right.
    ref = {"STD": ["1.000"]}
    ref_tip = [alt.Tooltip("STD:N", title="standard")]
    if has_corr:
        r = float(ratio)
        ref["COR"] = [f"{r:.3f}   ({100 * (r - 1):+.1f}%)"]
        ref_tip.append(alt.Tooltip("COR:N", title="measured"))
    if has_band:
        ref["BAND"] = [f"{float(ci_lo):.3f}  to  {float(ci_hi):.3f}"]
        ref_tip.append(alt.Tooltip("BAND:N", title="95% band"))

    if has_band:
        layers.append(
            alt.Chart(pd.DataFrame({"lo": [ci_lo], "hi": [ci_hi], **ref}))
            .mark_rect(opacity=0.12, color="#2b7bba")
            .encode(x=alt.X("lo:Q"), x2=alt.X2("hi:Q"), tooltip=ref_tip))

    points = (
        alt.Chart(d)
        .mark_circle(size=95, opacity=0.8, stroke="white", strokeWidth=0.5)
        .encode(
            x=alt.X("RATIO:Q",
                    scale=alt.Scale(type="log", domain=[lo, hi], clamp=True,
                                    nice=False),
                    axis=alt.Axis(values=_ticks(lo, hi), format="~g",
                                  title="actual hours ÷ master hours"
                                        "   (1.0 = the master is right)",
                                  grid=False)),
            y=alt.Y("JITTER:Q", axis=None,
                    scale=alt.Scale(domain=[-1.5, 1.5])),
            color=alt.Color("STATUS:N",
                            scale=alt.Scale(domain=present,
                                            range=[COLOURS[s] for s in present]),
                            legend=alt.Legend(title=None, orient="bottom",
                                              columns=1, labelLimit=400)
                            if legend else None),
            tooltip=tip))

    # DRAWN AFTER THE POINTS, not before. Altair layers in argument order, so
    # with the rules ahead of the dots a well-populated pool buried the red line
    # under 250 circles at 0.8 opacity - the one mark the chart exists to show.
    # The band stays underneath: it is a region, and dots on top of it read
    # correctly as "inside the interval".
    #
    # BOTH RULES CARRY ref_tip, the same one the band carries. Without any
    # tooltip at all they showed a box reading "v: 1" - "v" being the column
    # name in the one-row frame the layer is built from, an implementation
    # detail escaping onto the screen.
    # The words drawn on the chart match the keys in the tooltip, so the mark a
    # reader points at is named the same in both places.
    marks = [(1.0, "standard", "#555555", [6, 3])]
    if has_corr:
        marks.append((float(ratio), "measured", "#c0392b", []))
    over = []
    for value, label, colour, dash in marks:
        base = alt.Chart(pd.DataFrame({"v": [value], "label": [label], **ref}))
        over.append(base.mark_rule(color=colour, size=2.5, strokeDash=dash,
                                   opacity=1)
                    .encode(x=alt.X("v:Q"), tooltip=ref_tip))
        # The label above the line gets the same tooltip as the line itself.
        # They are one object to a reader, and hovering the words rather than
        # the rule is the easier target of the two.
        over.append(base.mark_text(align="left", dx=5, dy=-int(height / 2) + 12,
                                   fontSize=11, color=colour)
                    .encode(x=alt.X("v:Q"), text="label:N", tooltip=ref_tip))

    return (alt.layer(*layers, points, *over)
            .properties(height=height)
            .configure_view(strokeWidth=0))


def ci_caption(stats):
    """The sentence that has to sit under the chart.

    The shaded band and the red line are two different estimators and they can
    legitimately disagree - on a minority of actions the pooled ratio falls
    outside its own interval (10 of 224 on the 13 Aug 2026 extract; the guided
    app computes the live figure rather than quoting one). Drawn without saying
    so, the chart looks broken and takes the analysis down with it.
    """
    if stats.get("CI_LOW") is None or pd.isna(stats.get("CI_LOW")):
        return ("No interval: this pool never reached the minimum number of "
                "work orders, so no test was run.")
    return (
        "The shaded band is the 95% interval on the **per-work-order** average "
        "— every work order counts once, whatever its size. The red line, "
        "**measured**, is the hours-weighted ratio across the pool, and it is "
        "the figure a correction is computed from where one is proposed at "
        "all. When large and small jobs behave differently the two genuinely "
        "disagree, and the line can sit outside the band. The band is only ever "
        "used as a test — does it exclude 1.0? — never as error bars on the line."
    )


MISSTATED = "#2b7bba"
# Same hue, lighter: the two bars on "most wrong families" are the same measure
# over two different denominators, not two different things. A contrasting hue
# would imply they are unrelated, and every other colour in this tool already
# means something specific.
MISSTATED_LIGHT = "#8fbadd"

ALL_STEPS = "of all its master run time"
FLAGGED_STEPS = "of just the steps being changed"

# Below this a percentage stops meaning anything. Unfiltered, the "% of master"
# ranking is led by a family misstating 58.8% of 200 master hours and another at
# 24.3% of 88 - real arithmetic, no information. Four of the unfiltered top ten
# sit under 500 master hours. At 1,000 the survivors still carry 84% of all
# misstated hours.
PCT_FLOOR_H = 1000

# Axis titles carry the arithmetic rather than the word "misstated", so a bar is
# self-describing to somebody who has not read the glossary. Parentheses, not
# square brackets: square brackets read as an interval or a citation to a
# technical audience, and the metric tooltip already uses ( ).
#
# The per-standard level is deliberately NOT crammed in here. An axis title has
# to be short, and the tooltip on the headline metric plus the method page carry
# that detail.
HOURS_AXIS = "absolute (actual − master) run hours"
PCT_AXIS = "absolute (actual − master) as % of master run hours"


# Swiss thousands separator on chart axes. Neither Altair nor Vega-Lite exposes
# a number locale here - Config has no `locale` key - so the label is built by a
# Vega expression that formats normally and then swaps the separators. Chained
# twice so it still holds above a million, which these figures are nowhere near
# but the next extract need not stay that way.
_APOS = ("replace(replace(format(datum.value, ',.0f'), ',', \"'\"), "
         "',', \"'\")")


def _height(n):
    """One band per family, whatever how many bars sit inside it.

    Shared by both family panels so they cannot drift: the paired chart splits
    its band between two bars rather than taking twice the room, which keeps
    the bottom row level and the two charts comparable at a glance.
    """
    return max(240, 30 * n)


def _bar(d, label, value, title, fmt=",.0f", height=None, tooltip=None,
         name="family"):
    """One horizontal ranking. Net is deliberately absent - see the note on
    most_wrong_bar and the sentence under the grid."""
    d = d.copy()
    d["_VALUE_TXT"] = d[value].map(
        lambda v: ui.fmt(v, fmt) if pd.notna(v) else "—")
    return (alt.Chart(d)
            .mark_bar(color=MISSTATED, cornerRadiusEnd=3)
            .encode(
                y=alt.Y(f"{label}:N", sort=list(d[label]), title=None,
                        axis=alt.Axis(labelLimit=260, labelFontSize=12)),
                x=alt.X(f"{value}:Q", title=title,
                        axis=alt.Axis(format=fmt,
                                      labelExpr=_APOS if "," in fmt else None)),
                # Tooltips take a pre-formatted string field rather than a d3
                # format: Vega has no labelExpr equivalent here, so the only
                # way to get the apostrophe into a tooltip is to put it there
                # in pandas first.
                #
                # `name`, not title="". An empty title leaves Vega to fall
                # back to the field name, so this row read "LABEL" or
                # "OPERATION" in capitals.
                tooltip=tooltip or [
                    alt.Tooltip(f"{label}:N", title=name),
                    alt.Tooltip("_VALUE_TXT:N", title=title)])
            .properties(height=height or _height(len(d))))


def _part_tag(s):
    """ADV / ANDV down a column. Spelled out, the part type took a third of the
    axis and truncated to "Articolo di vend" on every row anyway.

    The mapping itself moved to ui.part_tag, which Inspect also uses in its
    subtitle. with_title=False because a Vega axis label is plain text - there
    is no element to hang a hover on.
    """
    return s.map(lambda v: ui.part_tag(v, with_title=False))


def _family_label(d):
    """Family plus part type. The name alone is ambiguous - the same family
    carries a finished and a semi-finished row, they are never pooled, and they
    can sit at opposite ends of a ranking."""
    return d.FAMILY + "  (" + _part_tag(d.PART_TYPE) + ")"


def operation_bar(d, top=10):
    """Which process holds the misstated run time.

    Operations are more concentrated than families - the top ten cover about
    four fifths of every misstated run hour, and S FRESATURA alone is roughly a
    quarter - so this is the more actionable of the two cuts and the one a
    process owner reads.
    """
    return _bar(d.nlargest(top, "GROSS_HOURS"), "OPERATION", "GROSS_HOURS",
                HOURS_AXIS, name="operation")


def family_misstated_bar(d, top=10):
    """Which product line holds the most misstated run time."""
    d = d.copy()
    d["LABEL"] = _family_label(d)
    return _bar(d.nlargest(top, "GROSS_HOURS"), "LABEL", "GROSS_HOURS",
                HOURS_AXIS)


def most_wrong_bar(d):
    """Misstatement as a share of the family's master run hours.

    A different question from "how much", and a different answer: the family
    holding the most hours is only fifth by proportion. Hours are deliberately
    absent - this chart answers "how wrong", and putting a second measure on it
    would let a reader take the bigger of the two.
    """
    d = d.copy()
    d["LABEL"] = _family_label(d)
    order = list(d.LABEL)

    # Whole numbers on the axis, one decimal in the tooltip. The axis is for
    # comparing bars, where "26.5" and "27" say the same thing and the decimal
    # is just ink; the tooltip is where somebody reads the figure to quote it.
    #
    # Both tooltips carry both figures, whichever bar is hovered, so the pair is
    # always readable together - the gap between them is the point.
    for col, spec in [("GROSS_HOURS", ",.0f"), ("MASTER_H", ",.0f"),
                      ("FLAGGED_MASTER_H", ",.0f"), ("PCT", ".1f"),
                      ("PCT_FLAGGED", ".1f")]:
        d[f"{col}_TXT"] = d[col].map(
            lambda v, s=spec: ui.fmt(v, s) if pd.notna(v) else "—")
    tip = [alt.Tooltip("LABEL:N", title="family"),
           alt.Tooltip("GROSS_HOURS_TXT:N", title="misstated hours"),
           alt.Tooltip("MASTER_H_TXT:N", title="all master run hours"),
           alt.Tooltip("PCT_TXT:N", title=f"% {ALL_STEPS}"),
           alt.Tooltip("FLAGGED_MASTER_H_TXT:N",
                       title="master hours on the flagged steps"),
           alt.Tooltip("PCT_FLAGGED_TXT:N", title=f"% {FLAGGED_STEPS}")]

    # Built by concat rather than melt on purpose: both percentage columns have
    # to survive into every row so either bar's tooltip can show the pair, and
    # naming a column in both id_vars and value_vars makes melt return nothing
    # at all - an empty chart with correct axes and no bars.
    long = pd.concat([d.assign(MEASURE=ALL_STEPS, VALUE=d.PCT),
                      d.assign(MEASURE=FLAGGED_STEPS, VALUE=d.PCT_FLAGGED)],
                     ignore_index=True)
    return (alt.Chart(long)
            .mark_bar(cornerRadiusEnd=2)
            .encode(
                y=alt.Y("LABEL:N", sort=order, title=None,
                        axis=alt.Axis(labelLimit=260, labelFontSize=12)),
                yOffset=alt.YOffset("MEASURE:N", sort=[ALL_STEPS,
                                                       FLAGGED_STEPS]),
                x=alt.X("VALUE:Q", title=PCT_AXIS,
                        axis=alt.Axis(format=".0f")),
                # Legend suppressed: the two swatches sit inline with the two
                # questions in the caption, which is where a reader needs the
                # mapping rather than detached above the plot.
                color=alt.Color("MEASURE:N", legend=None,
                                scale=alt.Scale(
                                    domain=[ALL_STEPS, FLAGGED_STEPS],
                                    range=[MISSTATED, MISSTATED_LIGHT])),
                tooltip=tip)
            .properties(height=_height(len(d))))


def family_bar(fam, top=15):
    """Families by misstated hours, gross with net beside it."""
    d = fam[fam.FAMILY != "TOTAL"].nlargest(top, "GROSS_HOURS").copy()
    d["LABEL"] = d.FAMILY + "  (" + d.PART_TYPE.str.slice(0, 18) + ")"
    long = d.melt(id_vars=["LABEL"], value_vars=["GROSS_HOURS", "NET_HOURS"],
                  var_name="MEASURE", value_name="HOURS")
    long["MEASURE"] = long.MEASURE.map({"GROSS_HOURS": "misstated (gross)",
                                        "NET_HOURS": "net"})
    return (alt.Chart(long)
            .mark_bar()
            .encode(
                y=alt.Y("LABEL:N", sort=list(d.LABEL), title=None,
                        axis=alt.Axis(labelLimit=320)),
                x=alt.X("HOURS:Q", title="hours over the fiscal year"),
                yOffset=alt.YOffset("MEASURE:N"),
                color=alt.Color("MEASURE:N",
                                scale=alt.Scale(
                                    domain=["misstated (gross)", "net"],
                                    range=["#2b7bba", "#b8c9d9"]),
                                legend=alt.Legend(title=None, orient="top")),
                tooltip=[alt.Tooltip("LABEL:N", title="family"),
                         alt.Tooltip("MEASURE:N", title="measure"),
                         alt.Tooltip("HOURS:Q", title="hours",
                                     format=",.0f")])
            .properties(height=max(260, 34 * len(d))))
