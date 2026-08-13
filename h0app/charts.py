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
COLOURS = {
    evidence.IN: "#2b7bba",
    evidence.OUTLIER: "#e8a33d",
    evidence.TOKEN: "#8d6cab",
    evidence.SKIPPED: "#a2705f",
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

    if ci_lo is not None and not pd.isna(ci_lo) and not pd.isna(ci_hi):
        layers.append(
            alt.Chart(pd.DataFrame({"lo": [ci_lo], "hi": [ci_hi]}))
            .mark_rect(opacity=0.12, color="#2b7bba")
            .encode(x=alt.X("lo:Q"), x2=alt.X2("hi:Q")))

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
            tooltip=[alt.Tooltip("WORK_ORDER:N", title="work order"),
                     alt.Tooltip("PART_ID:N", title="part"),
                     alt.Tooltip("LAST_DATE:T", title="last booked"),
                     alt.Tooltip("TOTAL_QTY:Q", title="pieces", format=",.0f"),
                     alt.Tooltip("HOURS_MASTER:Q", title="master h",
                                 format=".3f"),
                     alt.Tooltip("HOURS_WORKED:Q", title="actual h",
                                 format=".3f"),
                     alt.Tooltip("RATIO:Q", title="ratio", format=".3f"),
                     alt.Tooltip("STATUS:N", title="")]))

    # DRAWN AFTER THE POINTS, not before. Altair layers in argument order, so
    # with the rules ahead of the dots a well-populated pool buried the red line
    # under 250 circles at 0.8 opacity - the one mark the chart exists to show.
    # The band stays underneath: it is a region, and dots on top of it read
    # correctly as "inside the interval".
    marks = [(1.0, "the standard", "#555555", [6, 3])]
    if ratio is not None and not pd.isna(ratio):
        marks.append((float(ratio), "the correction", "#c0392b", []))
    over = []
    for value, label, colour, dash in marks:
        base = alt.Chart(pd.DataFrame({"v": [value], "label": [label]}))
        over.append(base.mark_rule(color=colour, size=2.5, strokeDash=dash,
                                   opacity=1)
                    .encode(x=alt.X("v:Q")))
        over.append(base.mark_text(align="left", dx=5, dy=-int(height / 2) + 12,
                                   fontSize=11, color=colour)
                    .encode(x=alt.X("v:Q"), text="label:N"))

    return (alt.layer(*layers, points, *over)
            .properties(height=height)
            .configure_view(strokeWidth=0))


def ci_caption(stats):
    """The sentence that has to sit under the chart.

    The shaded band and the red line are two different estimators and they can
    legitimately disagree - in 19 of 244 actions the pooled ratio falls outside
    its own interval. Drawn without saying so, the chart looks broken and takes
    the analysis down with it.
    """
    if stats.get("CI_LOW") is None or pd.isna(stats.get("CI_LOW")):
        return ("No interval: this pool never reached the minimum number of "
                "work orders, so no test was run.")
    return (
        "The shaded band is the 95% interval on the **per-work-order** average "
        "— every work order counts once, whatever its size. The red line is the "
        "**hours-weighted** ratio across the pool, which is what the correction "
        "uses. When large and small jobs behave differently the two genuinely "
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


def _bar(d, label, value, title, fmt=",.0f", height=None, tooltip=None):
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
                tooltip=tooltip or [
                    alt.Tooltip(f"{label}:N", title=""),
                    alt.Tooltip("_VALUE_TXT:N", title=title)])
            .properties(height=height or _height(len(d))))


def _part_tag(s):
    """ADV / ANDV. Family names are long and the part type only has to
    disambiguate, not describe - spelled out it took a third of the axis and
    truncated to "Articolo di vend" on every row anyway.

    Anything unrecognised falls back to its initials rather than defaulting to
    one of the two, so a third part type would show up as itself instead of
    silently joining a bucket it does not belong to.
    """
    def tag(v):
        t = str(v).strip().lower()
        if t.startswith("articolo"):
            return "ANDV" if " non " in f" {t} " else "ADV"
        return "".join(w[0] for w in str(v).split()).upper() or "?"
    return s.map(tag)


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
                HOURS_AXIS)


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
    tip = [alt.Tooltip("LABEL:N", title=""),
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
                tooltip=["LABEL:N", "MEASURE:N",
                         alt.Tooltip("HOURS:Q", format=",.0f")])
            .properties(height=max(260, 34 * len(d))))
