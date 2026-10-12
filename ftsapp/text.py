"""Shared prose, and the rule ladder.

The ladder is the reason this tool is worth building rather than sending the
workbook round. A recommendation is easy to read; the absence of one is not. A
part owner asking "why is mine not on the list" currently has to find somebody
who knows. Here every unit shows the six rules in the order the pipeline applies
them, with the actual figures, so "we looked at this and the standard holds" and
"we never had enough data to say" stop being the same blank cell.
"""

import numpy as np
import pandas as pd

from . import pipeline


def _fmt(v, spec=".3f"):
    """Swiss thousands separator, same as ui.fmt - kept here rather than
    imported so this module stays free of anything that touches streamlit."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return format(v, spec).replace(",", "'")


def _honest(v, threshold, passed, at_least=True, specs=(".1f", ".2f", ".3f",
                                                        ".4f", ".5f")):
    """Format a rule's value so the number cannot contradict its own verdict.

    A ratio of 1.099706 is 9.97% off the standard and fails the 10% rule, but
    printed to one decimal it reads "10.0%" beside "needs at least 10%" and a
    cross. On a screen whose entire pitch is that you can check the arithmetic
    yourself, that hands the room a free reason to disbelieve the other 235
    rows. So: add decimals until the printed figure lands on the same side of
    the threshold as the real one.

    Landing exactly ON the threshold counts as contradicting it. 5.2 h printed
    as "5 h" beside "needs at least 5 h" and a tick reads as a coin-flip
    called in our favour, which is the same loss of confidence by a different
    route - so a figure only stops gaining decimals once it is visibly clear of
    the line, unless it truly sits on it.
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    exact = float(v) == float(threshold)
    for spec in specs:
        # Thousands separators are wanted in the output but break float(), which
        # raised ValueError on any unit misstating four figures of hours. Not a
        # live case today - the largest is 179 h - but it would have arrived
        # unannounced the first time one crossed 1,000. Both separator styles
        # are stripped: the displayed one is an apostrophe, but a spec can still
        # produce a comma before _fmt swaps it.
        shown = float(format(v, spec).replace(",", "").replace("'", ""))
        agrees = (shown >= threshold) if at_least else (shown < threshold)
        if agrees == passed and (exact or shown != threshold):
            return _fmt(v, spec)
    return _fmt(v, specs[-1])


# One definition of the six rules, used by the rail, the landing page and the
# method page alike. They were written out three times and the de-jargon pass
# only reached one of them, so the landing page taught "Interval excludes 'no
# difference'" while the working page said "Sure of the direction" - two names
# for one rule, in a tool whose whole claim is that the rules are the spine.
def rule_method():
    """The METHOD behind each rule, in rules() order.

    NOT RENDERED ANYWHERE TODAY, and that is deliberate rather than an
    oversight - which is the difference between this and the `details` list
    deleted from this module on 2026-08-26. That one duplicated rules() and had
    nowhere to go; this has somewhere to go and no mechanism yet.

    It is meant to hang off each rule card on Methodology as a "?" tooltip.
    Three attempts on 2026-08-27 each failed one of the two requirements - look
    like Streamlit's own help icon, keep the six cards the same height - and
    ui.rule_cards records what was tried. Kept because the content is right and
    was checked against scipy; when the mechanism exists this is what goes in
    it.

    IF IT IS STILL UNRENDERED IN SIX MONTHS, delete it. Unrendered prose rots
    exactly like the figures this project spent a day correcting.

    NOT A SECOND EXPLANATION OF WHAT THE RULES DO - rules() owns that, in plain
    language, and a longer plain-language restatement was deleted from this
    module on 2026-08-26 precisely because it duplicated rules(). This is the
    other thing: WHICH TEST, on WHAT STATISTIC, and the arithmetic that makes
    the threshold the number it is.

    Kept off the face of the cards deliberately. "Benjamini-Hochberg controls
    the false discovery rate" is exact and tells a reader who does not already
    know it nothing, so the card says what it stops and this says how - one
    hover away, for the person who asks.

    A SEPARATE FUNCTION rather than a fourth element of rules(), because
    rule_status() unpacks that tuple as (name, _, _) and rules() is also the
    sidebar rail's source. Two consumers of a three-tuple, one consumer of
    this; widening the tuple would touch all three to serve one.
    """
    return [
        # VERIFIED with scipy.stats.wilcoxon: the smallest two-sided p a
        # signed-rank test can produce is 2 / 2**n, so n=4 bottoms out at
        # 0.125, n=5 at 0.0625 and n=6 at 0.0312. Six is not a convention here
        # - it is the first sample size at which rule 2 is winnable at all.
        f"A floor set by the test below it, not by taste. The smallest "
        f"two-sided p a Wilcoxon signed-rank test can return is 2/2^n: at "
        f"n=5 that is 0.063 and at n={pipeline.MIN_WO} it is 0.031. So a "
        f"five-work-order pool could never clear rule 2 however consistently "
        f"it missed the standard.",

        "Wilcoxon signed-rank, two-sided, on the natural log of each work "
        "order's actual/master ratio. Non-parametric: it ranks the deviations "
        "rather than averaging them, so a few extreme jobs cannot carry the "
        "result on their own. Logs because a halving and a doubling have to "
        "count as equal and opposite.",

        f"Benjamini-Hochberg. The p-values are sorted and the i-th of m is "
        f"compared against i/m x {pipeline.ALPHA}. It controls the expected "
        f"SHARE of false positives among the rules that pass, which is the "
        f"right question when hundreds of standards are tested at once - not "
        f"the chance of any single one being wrong.",

        "A t-interval on the mean of the log ratios, back-transformed. That "
        "makes it the geometric mean of the PER WORK ORDER ratios, every work "
        "order counting once. It is a different estimator from the pooled "
        "hours-weighted ratio that drives the correction, which is why the "
        "two can disagree - and why it is only ever read as a test of whether "
        "1.0 is inside, never as error bars.",

        f"|ratio - 1| >= {pipeline.MIN_EFFECT:.0%}, on the pooled "
        f"hours-weighted ratio after the outlier filter. Tested on the ratio "
        f"rather than the percentage change, because the change is asymmetric: "
        f"a rate that quadruples reads +300% while one cut to a quarter reads "
        f"-75% and can never pass -100%.",

        f"|sum(actual) - sum(master)| over the window, against "
        f"{pipeline.MIN_HOURS_IMPACT:g} h. ABSOLUTE, so a standard that "
        f"over-allows counts the same as one that under-allows. It is a sum "
        f"over work orders, so it grows with the window and with how often the "
        f"step runs - a small error on a busy step outranks a large one on a "
        f"rare step, which is the intended behaviour. The window opens on "
        f"{pd.Timestamp(pipeline.FY_START).day} "
        f"{pd.Timestamp(pipeline.FY_START):%b %Y} and never closes, so a part "
        f"produced only now and then joins the list once its gap reaches "
        f"{pipeline.MIN_HOURS_IMPACT:g} h.",
    ]


def rules():
    """(name, what it requires, what it stops) for each rule, in order."""
    return [
        ("Enough work orders",
         f"at least {pipeline.MIN_WO}",
         f"A verdict drawn from too little evidence. A hard floor, not a "
         f"preference: below {pipeline.MIN_WO} the test cannot reach "
         f"significance."),
        ("Consistently off the standard",
         f"p under {pipeline.ALPHA}",
         "A few extreme jobs dragging the average while the middle of the "
         "evidence says the standard is fine."),
        # Said as the consequence rather than the method. "Benjamini-Hochberg
        # controls the false discovery rate" is exact and tells a reader who
        # does not already know it nothing. What they need is that the flaw is
        # in the NUMBER of tests, not in any one of them - which is the whole
        # of the first sentence.
        #
        # "Look wrong when they aren't" rather than "look off": it names the
        # error instead of gesturing at it. A pool looks wrong when its work
        # orders happen to land mostly on one side of the standard - which some
        # will do by chance in any large enough set, with nothing at all wrong.
        #
        # No count and no odds here on purpose. An earlier version worked
        # through 1-in-20 against roughly 600 tests, which is the right
        # arithmetic and three times the length; the figures also move every run
        # and this string is the sidebar rail's as well.
        ("Not luck across many tests",
         f"q under {pipeline.ALPHA}",
         "Coincidences. Testing many standards at once can lead to mistakes: "
         "q tightens the threshold in proportion."),
        ("Sure of the direction",
         "the range must not span 1.0",
         "A difference the evidence cannot actually separate from zero."),
        ("Big enough to be worth it",
         f"at least {pipeline.MIN_EFFECT:.0%} off",
         "Churn. Avoids re-keying a standard that does not have relevant "
         "impact."),
        # NO "A YEAR" ON THE HOURS RULE. The window opens at FY_START and never
        # closes, so it is the fiscal year TO DATE - about ten months on this
        # extract - and "a year" invited reading a part-year total as an annual
        # one. Inspect's metric and the Review queue's column were corrected for
        # this; the six rules were missed, which put the same wrong word back on
        # screen wherever they show their figures.
        #
        # Dropped rather than replaced with the window: a bare "at least 20 h"
        # makes no claim about a period, so it cannot be wrong the way "a year"
        # was, and the window belongs to the page rather than to one pill. This
        # is already the longest of the six requirement chips.
        ("Enough hours to matter",
         f"at least {pipeline.MIN_HOURS_IMPACT:g} h "
         f"({pipeline.SETUP_MIN_HOURS:g} h for setup)",
         "Corrections that are right and do not matter."),
    ]


def rule_status(stats, q=None):
    """The six rules with this unit's own figures, in the order they apply.

    Named `rule_status` rather than `gates` because every screen says "rules".
    This module was the last place still calling them gates, so a reader moving
    between the code and the screen had to translate.

    Returns per rule: passed, name, and a compact `value` for the sidebar rail.
    Why each rule exists is rules()' job, not this one's. A rule after the first
    failure is still evaluated and shown - a reviewer wants to know that a unit
    missed the hours floor by two hours, not just that it stopped at the first
    hurdle.
    """
    n = stats.get("N_TESTED")
    min_n = stats.get("MIN_N", pipeline.MIN_WO)
    min_h = stats.get("MIN_HOURS", pipeline.MIN_HOURS_IMPACT)
    ratio = stats.get("RATIO")
    delta = stats.get("HOURS_DELTA")
    pw, ci_lo, ci_hi = (stats.get("P_WILCOXON"), stats.get("CI_LOW"),
                        stats.get("CI_HIGH"))

    def num(v):
        return v is not None and not pd.isna(v)

    excludes_one = num(ci_lo) and num(ci_hi) and (ci_lo > 1 or ci_hi < 1)
    p_ok = num(pw) and pw < pipeline.ALPHA
    q_ok = num(q) and q < pipeline.ALPHA
    dev_ok = num(ratio) and abs(ratio - 1) >= pipeline.MIN_EFFECT
    hrs_ok = num(delta) and abs(delta) >= min_h
    dev_pct = abs(ratio - 1) * 100 if num(ratio) else None

    # The hours figure keeps its sign. It is stated twice on the page - here and
    # in the metric beside it - and showing 10 in one place and -10 in the other
    # reads as two different numbers. The rule itself is on the magnitude, so
    # the threshold text says "either way".
    hrs = _honest(abs(delta) if num(delta) else None, min_h, hrs_ok,
                  specs=(",.0f", ",.1f", ",.2f"))
    if num(delta) and delta < 0 and hrs != "—":
        hrs = f"−{hrs}"

    values = [
        f"{n if num(n) else '—'} tested   (needs {min_n})",
        f"p = {_honest(pw, pipeline.ALPHA, p_ok, at_least=False, specs=('.3f', '.4f', '.5f'))}"
        f"   (needs under {pipeline.ALPHA})",
        f"q = {_honest(q, pipeline.ALPHA, q_ok, at_least=False, specs=('.3f', '.4f', '.5f'))}"
        f"   (needs under {pipeline.ALPHA})",
        f"range {_fmt(ci_lo)} to {_fmt(ci_hi)}   (must not span 1.0)",
        f"off by {_honest(dev_pct, pipeline.MIN_EFFECT * 100, dev_ok)}%"
        # "≥" rather than "at least". These two sit in a narrow rail beside a
        # figure that is the thing being read, and the words were longer than
        # the numbers they qualified. One symbol covers the setup thresholds
        # too: min_h is 5 h there and 20 h on run, from the same string.
        f"   (needs ≥ {pipeline.MIN_EFFECT:.0%})",
        # "a year" gone here too - same reason as on the rule above.
        f"{hrs} h   (needs ≥ {min_h:g} h either way)",
    ]
    # THE SIX EXPLANATORY PARAGRAPHS THAT USED TO SIT HERE ARE GONE. They were
    # returned under a key that no page has ever read - rule_cards takes its
    # sentence from rules(), rule_results shows name and value only, and the
    # rail that once showed them was removed. They were also a second
    # explanation of the same six rules that rules() already explains, which is
    # the failure this project has paid for before: the rules were written out
    # three times and a de-jargon pass reached one of the three. One
    # explanation, in rules(), rendered on Methodology.
    passed = [num(n) and n >= min_n, p_ok, q_ok, excludes_one, dev_ok, hrs_ok]
    return [{"passed": bool(p), "name": nm, "value": v}
            for p, (nm, _, _), v in zip(passed, rules(), values)]


# Which labour tickets are in the data at all. Lives with the dataset rather
# than with the method: every row is a statement about what the numbers are
# computed over, and it sits directly above the funnel that counts them.
# Keyed by the labels in data.EXCLUSIONS, so the prose table and the deduction
# table below it cannot drift apart. A rule added there without a reason added
# here renders with a blank Why, which is visible on the page rather than
# silent - the two are meant to be read as one statement and a missing half
# should look wrong.
#
# THESE ARE THE SCOPE RULES ONLY. They decide which labour tickets reach an
# analysis at all, which is why the deduction table can count them down to a
# total. Everything in WHAT_IS_EXCLUDED_LATER happens after that point, inside
# one analysis, and does not belong in the same arithmetic.
WHY_EXCLUDED = {
    "Rework":
        "Carries no master by design — thousands of actual hours against a "
        "master of zero. Matched on `S RIL%`.",
    "Ticket negative correction":
        "Hours booked back off a ticket already closed, so the figure is "
        "negative. It records an adjustment, not the length of a job.",
    "Step is no longer in the master routing":
        "The work order measured a process that no longer exists. A blank "
        "routing id means the step was deleted, or the slot now holds a "
        "different operation.",
    # Two causes, and the wording has to cover both. It used to say "there is
    # no standard on the step", which is untrue of roughly a tenth of these:
    # the standard is set, the booked quantity was zero, and a rate times no
    # pieces is no hours.
    "Step carries no master hours to compare against":
        "Master hours come out at zero, either deliberately or rate is set but "
        "no quantity was booked against it.",
    "Nothing was booked against it":
        "Zero hours recorded. No duration to judge a standard by.",
}

# Ordered by reach, widest first: the two that apply to every analysis, then run,
# then HRS/LOAD run, then setup. A reader scanning for "does this affect me"
# meets the universal rules before the ones that only bite in one place.
WHAT_IS_EXCLUDED_LATER = """
| Set aside later, and where | Why |
|---|---|
| Semi-finished pooled with finished — *every analysis* | Not an exclusion at all: both are analysed, never in the same pool. Same family, different physical job. |
| Work orders booked at or under 0.02 h — *every analysis* | A flat hundredth of an hour against a lot records that a ticket was closed, not how long the job took. There is no duration inside it to correct. |
| Work orders run under a master since replaced — *run and setup* | They describe a master that no longer exists. |
| Multi-load `HRS/LOAD` work orders — *`HRS/LOAD` run* | A job needing two loads is charged two full masters, but the data shows the second load costs less than the first. Kept and reported separately. |
| Setups booked at or under 0.02 h — *setup* | The setup did not happen. Running several orders of one family back to back on one machine, only the first needs a full setup. Not performed. |
| Setups run by a different crew than planned — *setup* | `SETUP_HRS` is one elapsed value for the crew the routing plans for. A different crew size is not used as evidence about the standard. |
"""

# Split so a page can take the piece it needs. "How to read it" wants only the
# correction directions; Methodology answers "where the numbers come from" at
# length. A third piece, GROSS_NOT_NET, went with the flat version that was the
# last thing rendering it - gross-versus-net is stated on the landing page and
# again in Methodology's reconciliation column.
# The date is derived from FY_START, not written. "This fiscal year" was vague
# on the page that carries the dates in its own caption.
#
# Day taken off the Timestamp rather than formatted with %-d, which is a glibc
# extension and raises ValueError on Windows.
_FY = pd.Timestamp(pipeline.FY_START)
_FY_LONG = f"{_FY.day} {_FY:%B %Y}"
#
# A middle paragraph used to sit here saying that "actual" and "master" are
# never paraphrased anywhere in the tool. True, and a note to whoever maintains
# it rather than to the person reading a recommendation - they need the two
# words defined, which the first paragraph does, not a promise about how
# consistently they are used.
#
# The two query-level filters are stated HERE and not in the deduction table,
# because they run in the SQL: the rows never reach the extract, so nothing
# downstream can count what they removed. Two sentences saying that in full were
# cut - they explained the placement to a maintainer, and the reader only needs
# the fact. Full four-row comparison against the operational dashboard is in
# README.md, "Why these totals differ from the operational dashboard".
#
# The closing paragraph no longer spells out part x routing step / family x
# routing step: the Methodology page now opens "What counts as one pool"
# directly below with exactly that, and said twice in two vocabularies it read
# as two different rules.
WHERE_FROM = f"""
### Where the numbers come from

Every labour ticket the ERP recorded from **{_FY_LONG}** onwards is joined to
the master routing that was in force for it. For each one the analysis has two
figures: the
**actual** hours booked and the **master** hours the standard carries. Their
ratio is the whole analysis.

Two filters are applied in the query itself, so those rows never reach the
extract at all:

- **Closed operations only.** An operation still in progress has booked part of
  its hours against the whole of its standard, so it would read as fast work.
- **4-digit routing steps only.** The master-data overhaul renumbered routing
  steps from 2 and 3 digits to 4 as it rebuilt them, so a shorter sequence
  belongs to a routing that no longer exists.

The second is usually the whole reason a total here is smaller than the same
total on the operational dashboard, which includes both.

A single work order says nothing — jobs vary. So the ratios are pooled, and the
question asked of each pool is a statistical one: *could this many work orders
land this consistently on one side of the standard by chance?*
"""

TWO_DIRECTIONS = """
### The two directions of correction

This is the one thing that must not be got backwards, because getting it wrong
produces plausible numbers that are wrong in **both** directions at once.

- **PCS/HR** — `RUN` holds a *rate*, pieces per hour. Hours = quantity ÷ rate,
  so the correction **divides**: a job taking 25% longer means the rate comes down.
- **`SETUP_HRS`, and `RUN` under HRS/LOAD** — both are *durations*. The correction
  **multiplies**: a job taking 25% longer means the allowance goes up.

`RUN` is one ERP column holding both, so the run type is what says which kind of
number is in it. The extract aliases it to `RUN_MASTER`; the ERP calls it `RUN`.
"""

CANNOT_TELL = """
- **Whether a standard is *fair*.** It measures actual against master. If a step
  is consistently under-booked the analysis will read it as
  fast work, and nothing in the data distinguishes the two.
- **Why** a standard is off. It locates the disagreement; the cause is a
  conversation with the people who run the step.
- **Anything about `LOAD_SIZE_QTY`.** How many pieces fit in a basket is a
  physical fact about the machine. Labour tickets measure elapsed time and
  contain no evidence about it, so `RUN` is the only parameter this analysis
  moves.
- **Steps nobody records.** Where a step is closed with a token booking there is
  no evidence either way. The standard may be badly wrong and this analysis will
  never say so — which is why those are listed rather than quietly dropped.
- **Setups run by a different crew than planned.** `SETUP_HRS` describes the
  crew the routing plans for, so a setup done by a different number of people
  cannot say whether that value is right. Those are charged and counted, but
  produce no verdict — the same silence as a token booking, for a different
  reason.
"""

# The tooltip on the "Absolute misstated hours" tile. ONE STRING, because
# Overview and the Review queue show the same figure under the same label, and
# an explanation carried by one of them only reads as the other meaning
# something else.
#
# "once per standard" is what pins the absolute to the right level. Without it,
# "absolute hours delta" reads as the absolute of each work order's delta - a
# different and larger number, because it would count ordinary job-to-job
# variation as misstatement. Within one standard the deltas cancel; across
# standards they do not.
#
# NO COMPARISON NUMBER IN HERE. An earlier version quoted the flat app's total
# against this one and went stale the moment either moved. A specific number
# nobody keeps current is worse than none.
ABSOLUTE_MISSTATED_HELP = (
    "The difference between actual and master, summed across every time the "
    "routing was performed — then taken as an absolute value once per "
    "standard, so different standards never cancel each other out.")

# The tooltip on the "Operations rows to edit" tile, which Overview and the
# Review queue also both carry. They had drifted: Overview said "higher than
# distinct parts affected as each part has multiple operations", the Review
# queue said "one edit per part per operation" - the same fact, in two
# vocabularies, under the same label and against the same 2'422.
#
# NAMES NO TILE. Overview's wording pointed at "Distinct parts affected", which
# sits beside it there and does not exist on the Review queue - so copying it
# across would have referred a reader to something not on their screen. It names
# the CONCEPT instead, which is true wherever the tile appears.
#
# The two pages reach 2'422 by different routes - Overview counts rows in the
# three execution sheets, the Review queue sums N_PARTS over 01_Actions - and
# they agree. Worth knowing if they ever stop agreeing; not worth a tooltip.
#
# What it still does not say: this also runs ahead of distinct ERP routing rows,
# because 39 rows share a MASTER_OPS_ROWID - one physical row needing both RUN
# and SETUP_HRS edited is two field edits and one row. That is a third
# comparison and would double the length of a tile tooltip.
ROWS_TO_EDIT_HELP = (
    "One edit per part per operation. This is higher than the number of "
    "distinct parts, because a part with four operations to correct needs "
    "four edits.")

# TWO CONSTANTS, because Additional findings puts the warning in a banner
# headline and the description in the sub-line under it. Held apart so the page
# does not say the same thing twice - which the long single string did, its
# headline and its first sentence being the same sentence.
NOT_A_STANDARD = "Nothing here is a standard to key in"

# WHAT UNITES THE THREE, and WHEN it happened - which is the one thing neither
# the sidebar (three costs) nor the tab bar (three names) says.
#
# "In scope" is precise, not decoration. All three are counted from rows that
# already passed every scope rule the analysis applies - the fiscal-year window,
# rework out, HOURS_MASTER and HOURS_WORKED above zero, MASTER_OPS_ROWID still
# present. Only then are they excluded, as evidence.TOKEN, evidence.SKIPPED and
# evidence.MULTILOAD. So the hours are real hours the analysis saw and could not
# test, not a tally of everything the extract contains.
#
# It is also why none of it is a standards edit: the master is not in question,
# the work behind it never entered a test.
NOT_A_STANDARDS_CHANGE = (
    "Routing and booking-discipline questions. These rows are all in scope for "
    "the analysis, and were excluded before any standard was tested."
)
