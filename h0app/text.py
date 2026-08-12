"""Shared prose, and the gate ladder.

The ladder is the reason this tool is worth building rather than sending the
workbook round. A recommendation is easy to read; the absence of one is not. A
part owner asking "why is mine not on the list" currently has to find somebody
who knows. Here every unit shows the six gates in the order the pipeline applies
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
    """Format a gate's value so the number cannot contradict its own verdict.

    A ratio of 1.099706 is 9.97% off the standard and fails the 10% gate, but
    printed to one decimal it reads "10.0%" beside "needs at least 10%" and a
    cross. On a screen whose entire pitch is that you can check the arithmetic
    yourself, that hands the room a free reason to disbelieve the other 235
    rows. So: add decimals until the printed figure lands on the same side of
    the threshold as the real one.

    Landing exactly ON the threshold counts as contradicting it. 5.2 h printed
    as "5 h a year" beside "needs at least 5 h" and a tick reads as a coin-flip
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
def rules():
    """(name, what it requires, what it stops) for each rule, in order."""
    return [
        ("Enough work orders",
         f"at least {pipeline.MIN_WO}",
         f"A verdict drawn from too little evidence. A hard floor, not a "
         f"preference: below {pipeline.MIN_WO} the test cannot reach "
         f"significance however consistently the work orders miss the "
         f"standard."),
        ("Consistently off the standard",
         f"p under {pipeline.ALPHA}",
         "A few extreme jobs dragging the average while the middle of the "
         "evidence says the standard is fine."),
        # Said in terms of the odds rather than the method. "Benjamini-Hochberg
        # controls the false discovery rate" is exact and tells a reader who
        # does not already know it nothing; the one-in-twenty framing is the
        # same statement in numbers anybody can follow, and it makes clear that
        # the flaw is in the NUMBER of tests, not in any one of them.
        #
        # No count here on purpose - roughly 30 of 603 on this extract, but the
        # figures move every run and this string is also the sidebar rail's.
        ("Not a fluke of testing many at once",
         f"q under {pipeline.ALPHA}",
         f"Luck. One test in twenty clears {pipeline.ALPHA} by chance, so "
         f"hundreds of tests throw up convincing results on their own. This "
         f"caps how many on the list can be flukes."),
        ("Sure of the direction",
         "the range must not span 1.0",
         "A difference the evidence cannot actually separate from zero."),
        ("Big enough to be worth it",
         f"at least {pipeline.MIN_EFFECT:.0%} off",
         "Churn. Re-keying a standard across a family to move it 4% costs "
         "more than it is worth."),
        ("Enough hours to matter",
         f"at least {pipeline.MIN_HOURS_IMPACT:g} h a year "
         f"({pipeline.SETUP_MIN_HOURS:g} h for setup)",
         "Corrections that are right and do not matter."),
    ]


def gates(stats, q=None):
    """The six gates, in the order recommend() and verdict() apply them.

    Returns per gate: passed, name, a compact `value` for the sidebar rail, and
    a longer `detail` for anyone who wants to know why the rule exists. A gate
    after the first failure is still evaluated and shown - a reviewer wants to
    know that a unit missed the hours floor by two hours, not just that it
    stopped at the first hurdle.
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
    # reads as two different numbers. The gate itself is on the magnitude, so
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
        f"   (needs at least {pipeline.MIN_EFFECT:.0%})",
        f"{hrs} h a year   (needs at least {min_h:g} h either way)",
    ]
    details = [
        f"A hard floor, not a preference: with fewer than {min_n} work orders "
        f"the test cannot reach significance however consistently they miss "
        f"the standard. Note this counts every work order the test used — a few "
        f"may still be set aside afterwards as unlike the rest, which changes "
        f"the estimate but never the test.",
        "A signed-rank test — it asks whether the work orders land on one side "
        "of the standard more often than coin-flipping would explain. It makes "
        "no assumption about the shape of the data, which is the guard against "
        "a few extreme jobs dragging the average while the middle of the "
        "evidence says the standard is fine.",
        "Hundreds of part-and-step combinations are tested together, so a "
        "handful would look convincing by chance alone. This adjusts for that, "
        "and is what keeps the list from filling with coincidences.",
        "The plausible range for the true ratio. If it straddles 1.0 the "
        "evidence is still consistent with the standard being right, however "
        "far off the best single estimate looks.",
        "Real but small differences are not worth the churn of re-keying a "
        "standard across every part of a family.",
        "Actual minus master over the year. The gate is on the size of the "
        "miss, not its direction — the sign is kept so it matches the metric "
        "beside it. Below the threshold the correction is right and does not "
        "matter enough to be worth making.",
    ]
    passed = [num(n) and n >= min_n, p_ok, q_ok, excludes_one, dev_ok, hrs_ok]
    return [{"passed": bool(p), "name": nm, "value": v, "detail": d}
            for p, (nm, _, _), v, d in zip(passed, rules(), values, details)]


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
| Work orders run under a master since replaced — *run* | They describe a master that no longer exists. |
| Multi-load `HRS/LOAD` work orders — *`HRS/LOAD` run* | A job needing two loads is charged two full masters, but the data shows the second load costs less than the first. Kept and reported separately. |
| Setups booked at or under 0.02 h — *setup* | The setup did not happen. Running several orders of one family back to back on one machine, only the first needs a full setup. Not performed. |
"""

# Split into three so a page can take the piece it needs. The guided app's
# "How to read it" wants only the correction directions: Methodology now answers
# "where the numbers come from" at length, and gross-versus-net is stated on the
# landing page and again in Methodology's reconciliation column. The v1 flat
# Method page still renders all three, which is why they stay here rather than
# being deleted.
# The date is derived from FY_START, not written. "This fiscal year" was vague
# on the page that carries the dates in its own caption and unanchored on the v1
# Method page, which renders this at the very top with nothing above it.
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
WHERE_FROM = f"""
### Where the numbers come from

Every labour ticket the ERP recorded from **{_FY_LONG}** onwards is joined to
the master routing that was in force for it. For each one the analysis has two
figures: the
**actual** hours booked and the **master** hours the standard carries. Their
ratio is the whole analysis.

A single work order says nothing — jobs vary. So the ratios are pooled per
**part × routing step**, or per **family × routing step** where a part is too
thin to judge alone, and the question asked of each pool is a statistical one:
*could this many work orders land this consistently on one side of the standard
by chance?*
"""

TWO_DIRECTIONS = """
### The two directions of correction

This is the one thing that must not be got backwards, because getting it wrong
produces plausible numbers that are wrong in **both** directions at once.

- **PCS/HR** — `RUN_MASTER` is a *rate*, pieces per hour. Hours = quantity ÷ rate,
  so the correction **divides**: a job taking 25% longer means the rate comes down.
- **`SETUP_HRS`, and `RUN` under HRS/LOAD** — both are *durations*. The correction
  **multiplies**: a job taking 25% longer means the allowance goes up.
"""

GROSS_NOT_NET = """
### Gross, not net

An operation whose families are half too fast and half too slow is not half
right. It is wrong twice. Netting hides exactly that, and across this analysis
the gross and net figures differ by nearly an order of magnitude. Every total
here is gross — the sum of the absolute misstatement — with net shown beside it
only to show how much cancels. The landing page states both, computed.
"""

# What the v1 flat Method page renders: all three, in the order they were
# written. Composed rather than copied, so editing a section moves both apps.
HOW_IT_WORKS = WHERE_FROM + TWO_DIRECTIONS + GROSS_NOT_NET

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
"""

NOT_A_STANDARDS_CHANGE = (
    "Nothing on this page is a standards change. These are the hours the "
    "schedule reserved and the costing charged for work with no evidence it was "
    "performed, and capacity reserved and not used. They are routing and "
    "booking-discipline questions, and they go to different people."
)
