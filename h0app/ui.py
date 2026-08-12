"""The visual language: colours, the gate rail, the funnel, the verdict banner.

One rule runs through all of it. **Colour carries meaning here, never decoration.**
Green means a rule was satisfied. Red means a rule stopped this from becoming an
action. Amber means a human has to look before it is keyed in. Grey means
excluded from the evidence. Blue is neutral data. Nothing is coloured for
prettiness, so a reader can trust that a colour is telling them something.

Every colour is also paired with a symbol - a tick, a cross, a dash - because
roughly one man in twelve cannot separate the green from the red, and this is
going in front of a room, not a screenshot.

The gate rail is the centrepiece. The analysis is a funnel of six rules and a
standard only changes if it passes all of them, so the rail shows all six with
the unit's own figure against each, all the time, in the sidebar. That turns
"why is my part not on the list" from a question somebody has to answer into
something the screen already says.
"""

import html

import pandas as pd

# --- semantic palette -------------------------------------------------------
PASS = "#3d9970"     # the rule was satisfied
FAIL = "#d1495b"     # the rule stopped this
WARN = "#dd9d3d"     # a human has to look
MUTE = "#8b9198"     # excluded, or not applicable
INFO = "#3f88c5"     # neutral data

CSS = """
<style>
/* st.caption dims its whole container with opacity:.6. Opacity on a parent
   creates a stacking context, so a coloured span inside comes out washed to
   60% - and two colours of different lightness converge, which is fatal when
   the caption IS a two-series legend.

   Fix it at the root: drop the container opacity and reproduce the same muted
   look by fading the TEXT COLOUR instead. color-mix keeps it relative to
   whatever the theme's text colour is, so light and dark both behave, and an
   explicit `color` on a child now wins outright.

   Applied app-wide so every caption keeps identical spacing and weight - the
   alternative was a hand-rolled caption whose block height did not match the
   real ones, which showed up as charts sitting at different heights. */
[data-testid="stCaptionContainer"] { opacity: 1 !important; }
[data-testid="stCaptionContainer"] p {
    color: color-mix(in srgb, currentColor 60%, transparent); }
.h0-rail { margin: .2rem 0 .6rem 0; }
.h0-step { display:flex; gap:.55rem; padding:.3rem 0 .3rem .1rem;
           position:relative; align-items:flex-start; }
.h0-step:not(:last-child)::before {
    content:""; position:absolute; left:6px; top:20px; bottom:-4px;
    width:2px; background:rgba(140,140,140,.30); }
.h0-dot { width:14px; height:14px; border-radius:50%; flex:0 0 14px;
          margin-top:2px; display:flex; align-items:center;
          justify-content:center; font-size:9px; font-weight:700;
          color:#fff; line-height:1; z-index:1; }
/* Sized up deliberately. These were .78/.72rem and measured 12.5px and
   11.5px on screen - a third the size of the metrics they qualify, on the
   one element the whole design exists to surface, in a tool meant to be
   read across a meeting room. */
.h0-txt { font-size:.95rem; line-height:1.35; min-width:0; }
.h0-name { font-weight:600; }
.h0-val { opacity:.85; font-size:.88rem; }
.h0-stop { font-size:.78rem; font-weight:700; letter-spacing:.04em;
           text-transform:uppercase; }

.h0-banner { border-radius:10px; padding:.85rem 1rem; margin:.2rem 0 .9rem 0;
             border-left:5px solid; }
.h0-banner .h0-b-title { font-size:1.05rem; font-weight:700; }
.h0-banner .h0-b-sub { font-size:.85rem; opacity:.85; margin-top:.15rem; }

.h0-chip { display:inline-block; padding:.12rem .55rem; border-radius:999px;
           font-size:.72rem; font-weight:600; margin:.1rem .25rem .1rem 0;
           border:1px solid; }

/* st.dataframe draws to a canvas, so its column headers cannot be reached by
   CSS and column_config has no header-alignment option - numbers end up right
   aligned under a left aligned title. st.table renders real HTML, so a small
   summary table can have both aligned. Only the first column is a label.

   !important on the header because streamlit's own rule wins on specificity
   otherwise - the cells moved and the titles above them did not. */
[data-testid="stTable"] th:not(:first-child),
[data-testid="stTable"] td:not(:first-child) {
    text-align: right !important; }
/* Streamlit dims the header row AND the index column to 60% alpha, treating
   both as chrome around the figures. Half right. The header is chrome - read
   once, never again - and stays dimmed. The index column is not: it holds the
   row's label, and dimming it while the figures sit at full strength inverts
   the reading order, so the eye lands on -13'681 before the words saying what
   it is. Line-item labels carry full weight on any financial statement; it is
   the column headings that go light. inherit works in both themes. */
[data-testid="stTable"] th { font-weight: 600; }
[data-testid="stTable"] tbody th { color: inherit; }

.h0-count { display:flex; gap:.6rem; align-items:baseline; padding:.35rem 0; }
.h0-cval { font-size:1.35rem; font-weight:700; min-width:3.2rem;
           text-align:right; }

/* Sized up with the rail. The funnel is the one graphic a director actually
   looks at, and it had become the smallest text on the landing page. */
.h0-funnel { margin:.4rem 0 .2rem 0; }
.h0-fhead { font-size:.85rem; font-weight:700; letter-spacing:.06em;
            text-transform:uppercase; opacity:.7; margin:.9rem 0 .4rem 0; }
/* st.divider draws an <hr> with equal 32px margins, but the vertical block it
   sits in is a flex container with gap:16px - and the gap lands on one side
   only. The result is 48px above every rule and 33px below it, so a divider
   hugs whatever follows it. Most visible around a single boxed element between
   two rules, where it reads as the box being pushed upward.

   Taking the gap out of the top margin evens it: 16 + 24 = 40 above, 40 + 1 =
   41 below. */
[data-testid="stElementContainer"] hr { margin-top: 24px; margin-bottom: 40px; }

/* The six rules, 3 x 2. grid-auto-rows:1fr is what makes every box the same
   height - rows size to the tallest card rather than to their own content.
   FIXED AT THREE COLUMNS, not auto-fit: auto-fit packs in as many as will fit,
   so a wide window laid the six out 5 + 1 and the pairing of rows 1-3 and 4-6
   disappeared. Stepped down explicitly instead, so a narrow pane still works. */
.h0-rules { display:grid; gap:.7rem; grid-auto-rows:1fr;
            grid-template-columns:repeat(3, 1fr); }
@media (max-width: 900px) {
    .h0-rules { grid-template-columns:repeat(2, 1fr); } }
@media (max-width: 600px) {
    .h0-rules { grid-template-columns:1fr; } }
.h0-rule { border:1px solid rgba(128,128,128,.35); border-radius:.55rem;
           padding:.85rem 1rem; display:flex; flex-direction:column;
           gap:.5rem; }
.h0-rule-name { font-weight:700; font-size:1rem; }
/* No margin-top:auto here. Pushing this to the foot of the card left a gap of a
   different size under every pill, so six boxes of identical height still read
   as six different layouts. The text follows the pill and the slack collects at
   the bottom, where it is the same shape in each. */
.h0-rule-stops { font-size:.84rem; opacity:.75; }

.h0-fstep { margin-bottom:.5rem; }
/* bar and its value share a row, so a bar too narrow to hold the number can
   put it alongside instead of being padded out to fit */
.h0-fbarrow { display:flex; align-items:center; gap:.5rem; }
.h0-fbar { height:26px; border-radius:5px; display:flex; align-items:center;
           padding-left:.55rem; font-size:.78rem; font-weight:600;
           color:#fff; white-space:nowrap; min-width:2.6rem; }
/* no floor on the narrow ones - the floor is what made 215 and 59 identical */
.h0-fbar.h0-narrow { min-width:0; padding-left:0; }
.h0-fout { font-size:.78rem; font-weight:700; white-space:nowrap; }
.h0-flabel { font-size:.95rem; font-weight:600; margin-bottom:.2rem; }
.h0-fnote { font-size:.82rem; opacity:.75; margin-top:.1rem; }
</style>
"""


def inject(container=None):
    """Load the stylesheet once per page."""
    (container or _st()).markdown(CSS, unsafe_allow_html=True)


def _st():
    import streamlit as st
    return st


def _e(v):
    return html.escape(str(v))


def rule_cards(container, rules, per_row=3):
    """The six rules as cards: number, name, threshold, what it stops.

    Rendered the same way wherever they appear. The content already comes from
    one place - text.rules() - and the layout now does too, because two pages
    drawing the same list two ways is the same drift in a different coat: a
    reader who meets them as cards on one page and a table on the next has to
    work out whether they are the same six.

    Tried as a table first and the cards win on this content. Each rule is a
    name, one threshold and a sentence, which is a card; in a table the
    thresholds line up in a narrow column and the sentences wrap three deep.

    ITS OWN GRID RATHER THAN st.columns, so the six boxes come out the same
    size. st.columns(3) does not lay out two rows of three - it lays out three
    columns of two, so rule 4 sits under rule 1 and each box takes the height of
    its own sentence. The six rendered 252, 162, 185, 185, 210 and 162 pixels
    tall. Streamlit's own wrapper cannot be styled around that either: the same
    testid carries the metric row and the section blocks on the same page, so
    there is nothing to target that means "a rule card".
    """
    # Lowercased at render, not in text.rules(). The sentence reads as the tail
    # of "Stops:" here, but the same string stands alone elsewhere and would
    # look like a typo starting in lower case there.
    cards = "".join(
        f'<div class="h0-rule">'
        f'<div class="h0-rule-name">{i}. {_e(name)}</div>'
        f'<div>{chip(req, INFO)}</div>'
        f'<div class="h0-rule-stops"><b>Stops:</b> '
        f'{_e(stops[:1].lower() + stops[1:])}</div>'
        f'</div>'
        for i, (name, req, stops) in enumerate(rules, 1))
    container.markdown(
        f'<div class="h0-rules" style="--h0-cols:{per_row}">{cards}</div>',
        unsafe_allow_html=True)


def equal_cards(container, min_height="16.5rem"):
    """Make bordered cards stacked in st.columns come out the same size.

    Streamlit sizes a bordered container to its own content and pins it to the
    top of its column, so a row of cards ends up as ragged as its captions.

    Three things are needed and none of them alone is enough:

    - the column's inner block becomes a flex column, so the cards in it are
      flex items rather than blocks stacked at the top;
    - flex:1 on each card, so they divide the column instead of hugging their
      own text;
    - a min-height, because flex:1 CANNOT grow the column. A flex item will not
      shrink below its own content - min-height:auto is the default - so the
      column ends up as tall as its two cards' content and the taller card
      simply keeps its height. Measured: 188 and 262 in one column, with
      flex:1 1 0% correctly applied to both.

    So min_height is a floor, not a fixed size. Set it at or above the tallest
    card's content and every column becomes twice it, which flex then splits
    evenly. If a caption later outgrows it the layout degrades gently: that
    card takes what it needs, its column grows, the others stretch to match.

    Emitted by the page that wants it rather than living in the app-wide sheet,
    so it holds only while that page renders. Pairs with a single st.columns()
    call holding the cards column-major - two separate rows of three cannot
    equalise against each other whatever the CSS says, because they are two
    independent flex containers.
    """
    container.markdown(f"""<style>
[data-testid="stColumn"] > div {{ height: 100%; display: flex;
    flex-direction: column; gap: .75rem; }}
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] {{
    flex: 1; min-height: {min_height}; }}
/* The card's own contents fill it, and the last element - the link out - is
   pushed to the floor. Left where it fell, the link sat directly under a
   two-line caption on one card and a three-line one on the next, so six links
   landed at four different heights and the eye had nothing to follow across. */
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] > div {{
    height: 100%; }}
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] > div
    > [data-testid="stElementContainer"]:last-child {{ margin-top: auto; }}
</style>""", unsafe_allow_html=True)


def align_table_columns(container, markdown_pct=30, table_pct=70):
    """Put every table on this page on one column grid. Call once, near the top.

    Stacked tables that do not share a grid read as unrelated objects. Both
    HTML table flavours size columns to their content, so two tables one above
    the other land 15-35px apart on the first column - close enough to look
    like a mistake rather than a choice. table-layout:fixed takes the width
    from here instead of from the longest cell.

    Emitted as a style block by the page rather than living in the app-wide
    sheet, because it only holds while the page that called it is rendered.
    A fixed label column suits a page of like-shaped tables and would crop one
    that happens to carry a long value, so this stays opt-in.

    Markdown tables and st.table get different widths because they carry
    opposite shapes: a markdown table here is label-and-prose and wants a
    narrow first column, an st.table is label-and-figures and wants a wide one.
    """
    container.markdown(f"""<style>
[data-testid="stMarkdownContainer"] table,
[data-testid="stTable"] table {{ table-layout: fixed; width: 100%; }}
[data-testid="stMarkdownContainer"] table th:first-child,
[data-testid="stMarkdownContainer"] table td:first-child {{
    width: {markdown_pct}%; }}
[data-testid="stTable"] table th:first-child,
[data-testid="stTable"] table td:first-child {{ width: {table_pct}%; }}
</style>""", unsafe_allow_html=True)


def tinted(text, colour):
    """Colour the words themselves, rather than putting a key beside them.

    Where a caption IS the legend - two questions, one per series - colouring
    the question in its series' colour removes the indirection entirely. There
    is no swatch to map to a bar; the sentence is the mapping.
    """
    return f'<span style="color:{colour}">{_e(text)}</span>'


def caption_line(container, html):
    """A caption whose coloured spans survive.

    A real st.caption, so the block height, spacing and weight are identical to
    every other caption on the page. The stylesheet above is what lets the
    colours through; plain text inside still comes out muted on its own.
    """
    container.caption(html, unsafe_allow_html=True)


def chip(label, colour):
    return (f'<span class="h0-chip" style="color:{colour};border-color:{colour};'
            f'background:{colour}1a">{_e(label)}</span>')


def gate_rail(container, gates):
    """The six rules, with this unit's own figure against each.

    Only the FIRST failure is marked as the blocker. The rest are still shown
    with their real values rather than greyed out, because "it failed on the
    hours floor by two hours" and "it failed on everything" are different
    situations and a reviewer needs to tell them apart.
    """
    blocker = next((i for i, g in enumerate(gates) if not g["passed"]), None)
    rows = []
    for i, g in enumerate(gates):
        ok = g["passed"]
        colour = PASS if ok else (FAIL if i == blocker else MUTE)
        mark = "&#10003;" if ok else ("&#10005;" if i == blocker else "&ndash;")
        stop = (f'<div class="h0-stop" style="color:{FAIL}">stopped here</div>'
                if i == blocker else "")
        rows.append(
            f'<div class="h0-step">'
            f'<div class="h0-dot" style="background:{colour}">{mark}</div>'
            f'<div class="h0-txt"><div class="h0-name">{_e(g["name"])}</div>'
            f'<div class="h0-val">{_e(g.get("value", ""))}</div>{stop}</div>'
            f'</div>')
    container.markdown(f'<div class="h0-rail">{"".join(rows)}</div>',
                       unsafe_allow_html=True)
    return blocker


def verdict_banner(container, verdict, kind, detail=""):
    """kind: 'act' | 'review' | 'caution' | 'hold' | 'blocked' | 'unknown'.

    Amber covers 'review' and 'caution' and nothing else, so it keeps one
    meaning: do not act on this as it stands. 'unknown' was borrowing amber to
    get itself noticed, which gave the colour a second meaning - no verdict
    recorded - and the legend only promises the first.
    """
    colour = {"act": PASS, "review": WARN, "caution": WARN, "hold": INFO,
              "blocked": MUTE, "unknown": MUTE}.get(kind, INFO)
    sub = f'<div class="h0-b-sub">{_e(detail)}</div>' if detail else ""
    container.markdown(
        f'<div class="h0-banner" style="border-color:{colour};'
        f'background:{colour}14"><div class="h0-b-title" '
        f'style="color:{colour}">{_e(verdict)}</div>{sub}</div>',
        unsafe_allow_html=True)


def funnel(container, sections, scale_to=None):
    """sections: list of (heading, unit_label, [(label, count, note), ...]).

    The whole analysis is a narrowing, and showing it as one makes the shape of
    the process legible before anybody reads a number: most of what was measured
    never becomes an action, and that is the design working rather than
    something missing.

    SECTIONS EXIST BECAUSE THE UNIT CHANGES MIDWAY. The first stages count
    labour tickets, the later ones count part x routing-step combinations, and
    there is no conversion between them - one part-step is however many tickets
    happened to run it. Drawn on one scale it read as ten thousand work orders
    being thrown away. Each section is now scaled to its own first bar and says
    what it is counting.
    """
    # scale_to fixes the 100% mark for every bar, across sections and across
    # funnels. Left None, each section renormalises to its own first bar.
    #
    # Per-section was right while this was ONE funnel spanning the regrouping:
    # the units differ either side of it, and a shared scale made a change of
    # unit look like evidence being thrown away. Split in two, that reverses -
    # per-section drew 8,656 standards at full width in the second half and at
    # 42% in the first, so the same number changed length between two charts on
    # one page. Passing the same scale_to to both keeps a count the same width
    # wherever it appears, which is the only way the two read as one narrowing.
    top_all = (scale_to or
               max((c for _, _, stages in sections
                    for _, c, _ in stages if c), default=1) or 1)
    out = []
    for heading, unit_label, stages in sections:
        top = top_all if scale_to else (
            max((c for _, c, _ in stages if c), default=1) or 1)
        out.append(f'<div class="h0-fhead">{_e(heading)} · counted in '
                   f'{_e(unit_label)}</div>')
        for i, (label, count, note) in enumerate(stages):
            # The floor used to be 4% so the number always had a bar to sit in.
            # On one scale that collapsed the tail: 215 and 59 both bottomed out
            # at 4% and drew identical, though one is three and a half times the
            # other. Below the readable width the number moves outside the bar
            # instead, so the bar can keep shrinking and stay honest.
            raw = 100.0 * (count or 0) / top
            inside = raw >= 8.0
            pct = max(0.3, raw)
            last = (heading, i) == (sections[-1][0], len(stages) - 1)
            colour = PASS if last else INFO
            val = num(count)
            out.append(
                f'<div class="h0-fstep">'
                f'<div class="h0-flabel">{_e(label)}</div>'
                f'<div class="h0-fbarrow">'
                f'<div class="h0-fbar{"" if inside else " h0-narrow"}" '
                f'style="width:{pct:.1f}%;background:{colour}">'
                f'{val if inside else ""}</div>'
                + ("" if inside else
                   f'<div class="h0-fout" style="color:{colour}">{val}</div>')
                + f'</div><div class="h0-fnote">{_e(note)}</div></div>')
    container.markdown(f'<div class="h0-funnel">{"".join(out)}</div>',
                       unsafe_allow_html=True)


def legend(container):
    container.markdown(
        chip("✓ rule passed", PASS) + chip("✕ stopped here", FAIL)
        + chip("! needs a human before keying", WARN)
        + chip("– failed, but not the blocker", MUTE),
        unsafe_allow_html=True)


def summary_rail(container, items):
    """A plain counted summary. Deliberately NOT gate_rail.

    Reusing the six-rule rail for a count of "what we found about this part"
    put a green tick beside "0 steps tested" and a red cross beside a part with
    nothing wrong with it - the same visual language carrying the opposite
    meaning one page over. Counts are not verdicts and must not look like them.
    """
    rows = []
    for label, value, note in items:
        rows.append(
            f'<div class="h0-count"><div class="h0-cval">{_e(value)}</div>'
            f'<div class="h0-txt"><div class="h0-name">{_e(label)}</div>'
            f'<div class="h0-val">{_e(note)}</div></div></div>')
    container.markdown(f'<div class="h0-rail">{"".join(rows)}</div>',
                       unsafe_allow_html=True)


def review_warning(container, current, suggested, ratio, lo, hi):
    """The banner that has to appear before anyone keys an extreme value."""
    container.warning(
        f"**Check this one by hand before keying it in.** The evidence points "
        f"at {fmt(current)} → {fmt(suggested)}, a ratio of {fmt(ratio, '.2f')} "
        f"— outside the {lo}–{hi} band the analysis treats as ordinarily "
        f"believable. A change this large is usually a standard that never "
        f"described the job rather than a process that drifted, so it wants a "
        f"human who knows the step before it reaches the ERP.",
        icon=":material/pan_tool:")


def direction_note(target, run_type):
    """The sentence that stops a rate being corrected like a duration."""
    if target == "RUN" and run_type == "PCS/HR":
        return ("**RUN_MASTER is a rate** (pieces per hour). Hours = quantity "
                "÷ rate, so the correction **divides**: a job running "
                "slower means a *lower* rate.")
    field = "SETUP_HRS" if target == "SETUP_HRS" else "RUN (hours per load)"
    return (f"**{field} is a duration.** The correction **multiplies**: a job "
            f"running slower means a *longer* allowance.")


def fmt(v, spec=",.2f", dash="—"):
    """Format a number, Swiss style: apostrophe for thousands, point for the
    decimal. Pass a spec containing a comma to get grouping."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return dash
    return format(v, spec).replace(",", "'")


def num(v, dec=0, dash="—"):
    """1'234 — the common case, with grouping."""
    return fmt(v, f",.{dec}f", dash)


def hrs(v, dec=0, dash="—"):
    """1'234 h."""
    out = num(v, dec, dash)
    return out if out == dash else f"{out} h"


def swiss_grid(df, specs):
    """A dataframe styled with Swiss separators that still sorts numerically.

    st.column_config.NumberColumn takes printf specs only, which cannot group
    with an apostrophe, and its "localized" option follows the VIEWER's browser
    locale - en-GB gives commas, it-IT gives dots, so the same table reads
    differently for each person in the room.

    A pandas Styler formats the display while streamlit keeps the underlying
    numeric values for sorting, which is the only route that gets both.

    specs: {column: format spec}, e.g. {"HOURS_DELTA": ",.0f"}.
    """
    live = {c: s for c, s in specs.items() if c in df.columns}
    return df.style.format(
        {c: (lambda v, sp=s: fmt(v, sp)) for c, s in live.items()},
        na_rep="—")
