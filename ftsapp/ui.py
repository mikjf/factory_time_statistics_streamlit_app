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
import re

import numpy as np
import pandas as pd
import streamlit as st

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
.fts-rail { margin: .2rem 0 .6rem 0; }
.fts-step { display:flex; gap:.55rem; padding:.3rem 0 .3rem .1rem;
           position:relative; align-items:flex-start; }
.fts-step:not(:last-child)::before {
    content:""; position:absolute; left:6px; top:20px; bottom:-4px;
    width:2px; background:rgba(140,140,140,.30); }
.fts-dot { width:14px; height:14px; border-radius:50%; flex:0 0 14px;
          margin-top:2px; display:flex; align-items:center;
          justify-content:center; font-size:9px; font-weight:700;
          color:#fff; line-height:1; z-index:1; }
/* Sized up deliberately. These were .78/.72rem and measured 12.5px and
   11.5px on screen - a third the size of the metrics they qualify, on the
   one element the whole design exists to surface, in a tool meant to be
   read across a meeting room. */
.fts-txt { font-size:.95rem; line-height:1.35; min-width:0; }
.fts-name { font-weight:600; }
.fts-val { opacity:.85; font-size:.88rem; }
.fts-stop { font-size:.78rem; font-weight:700; letter-spacing:.04em;
           text-transform:uppercase; }

.fts-banner { border-radius:10px; padding:.85rem 1rem; margin:.2rem 0 .9rem 0;
             border-left:5px solid; }
.fts-banner .fts-b-title { font-size:1.05rem; font-weight:700; }
.fts-banner .fts-b-sub { font-size:.85rem; opacity:.85; margin-top:.15rem; }


/* STREAMLIT'S OWN HELP ICON, reproduced. Copied from the live DOM rather than
   drawn by hand: st.metric(help=...) renders a 16x16 Feather "help-circle" SVG
   stroked at 60% of the current text colour, vertical-align middle,
   cursor:pointer. Those exact values are below, so the marker beside a rule is
   the same glyph a reader meets on every tile and picker in the app.

   WHY NOT JUST USE help=. Streamlit only attaches it to a whole element, and
   these six cards are ONE markdown block - which is what lets them share
   `grid-auto-rows:1fr` and come out the same height. Splitting them into six
   elements to get six help= arguments was tried on 2026-08-27 and cost the
   grid; this keeps both.

   WHAT IS STILL NOT THE SAME: the tooltip body. Streamlit's is a BaseWeb React
   component rendered into a portal on hover, and nothing in a markdown block
   can summon it - so the text arrives as the browser's own title tooltip. The
   ICON matches exactly; the panel it opens does not. */
.fts-help { display:inline-flex; align-items:center; vertical-align:middle;
           margin-left:.35rem; cursor:pointer; }
/* stroke-width 2.25, not the 2 in the SVG attribute: Streamlit overrides it in
   CSS and the computed value is what the eye compares. Measured against a live
   st.metric help icon on the same page - everything else already matched. */
.fts-help svg { width:16px; height:16px; stroke-width:2.25px;
               stroke: color-mix(in srgb, currentColor 60%, transparent); }
.fts-help:hover svg { stroke: currentColor; }

.fts-chip { display:inline-block; padding:.12rem .55rem; border-radius:999px;
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

.fts-count { display:flex; gap:.6rem; align-items:baseline; padding:.35rem 0; }
.fts-cval { font-size:1.35rem; font-weight:700; min-width:3.2rem;
           text-align:right; }

/* Sized up with the rail. The funnel is the one graphic a director actually
   looks at, and it had become the smallest text on the landing page. */
.fts-funnel { margin:.4rem 0 .2rem 0; }
.fts-fhead { font-size:.85rem; font-weight:700; letter-spacing:.06em;
            text-transform:uppercase; opacity:.7; margin:.9rem 0 .4rem 0; }
/* st.divider draws an <hr> with equal 32px margins, but the vertical block it
   sits in is a flex container with gap:16px - and the gap lands on one side
   only. The result is 48px above every rule and 33px below it, so a divider
   hugs whatever follows it. Most visible around a single boxed element between
   two rules, where it reads as the box being pushed upward.

   Taking the gap out of the top margin evens it: 16 + 24 = 40 above, 40 + 1 =
   41 below. */
[data-testid="stElementContainer"] hr { margin-top: 24px; margin-bottom: 40px; }

/* ...but NOT in the sidebar. That 40px was measured against the main column's
   16px flex gap; the sidebar's blocks sit tighter, so the same rule left a 46px
   trough between a divider and the heading under it - the divider stopped
   reading as "these two blocks are separate" and started reading as "something
   is missing here". Even margins, no gap to compensate for. */
[data-testid="stSidebar"] [data-testid="stElementContainer"] hr {
    margin-top: 20px; margin-bottom: 20px; }

/* st.warning paints itself rgba(255,255,18,.2) - a pure yellow, and not the
   amber this tool defines as "a human has to look". The review flag is that
   state, the ! dot in the legend is that colour, and the box explaining it was
   arriving in a different one.
   Recoloured app-wide rather than per call: every st.warning here means the
   same thing, so they should all read as the same thing. The alert layout is
   untouched - only the tint moves, so warning boxes still match every other
   alert in shape and differ only in colour.
   stAlertContentWarning is the hook; the container above it carries the
   background, hence :has(). */
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
    background-color: rgba(221, 157, 61, .18) !important; }

/* Streamlit reserves 6rem above the first element of every page to clear its
   floating header. The header is 60px, so 36 of those 96 pixels were slack, and
   the page title then added 20 more of its own padding on top of a 16px block
   gap - 132px before the first word on a page whose first word says which unit
   you are looking at.
   4rem keeps 20px of clearance under the header, which the Deploy button sits
   in, and gives back half a screen-inch on every page. Below 4rem the title
   starts to tuck under that toolbar on a narrow window. */
[data-testid="stMainBlockContainer"] { padding-top: 4rem; }
[data-testid="stHeading"] h1 { padding-top: 0; }

/* The help "?" beside a widget label, next to the label instead of adrift on
   the far right. Streamlit wraps the icon in a spacer div set to flex:1, so on
   a 260px selectbox the question mark landed 190px away from the word it
   explains and read as belonging to the box below it rather than to the label.
   Scoped to stWidgetLabel: st.metric already places its icon against the text,
   and this must not move it. */
[data-testid="stWidgetLabel"] > div:has([data-testid="stTooltipIcon"]) {
    flex: 0 0 auto; margin-left: .375rem;
}

/* A metric whose delta reads beside its value rather than under it. Streamlit
   stacks label / value / delta in one block column, which cost a whole line and
   left a metric carrying a delta 27px taller than its neighbours - a row of
   five sitting at two heights.
   Laid out as a wrapping flex line, the label keeps a row of its own and the
   value and the delta share the next one on a common baseline. Two consequences
   worth having: every metric in the row is the same height again, and the
   alignment of the two pills is now a fact of the layout rather than a negative
   margin matched to Streamlit's furniture by eye. On a narrow window the delta
   wraps back under the value instead of overflowing its column.
   The pill sits ON the number's baseline: its bottom edge and the bottom of the
   digits are the same line. Neither of the two alignments CSS offers by name
   gives that. flex-end aligns the pill to the bottom of the value's LINE BOX,
   which on a 36px Source Sans runs 1rem below the baseline, so the pill hung
   low; baseline aligns the two texts' baselines, which drops the pill's own
   background a descender lower still - and worse, a delta carrying an arrow is
   a flex row whose first item is the SVG, and a flex container takes its
   baseline from its first item, so the arrowed pill sat 3px off the other one:
   the exact misalignment this whole change exists to remove.
   So: flex-end, lifted by that 1rem of below-baseline leading. In rem because
   Streamlit sizes the metric value in rem too, so the two scale together.
   The delta's wrapper is display:contents rather than a box of its own - it
   carries 4px under the pill that would otherwise have to be subtracted here,
   and dissolving it keeps the arithmetic to one term.
   OPT-IN, by st.container(key="fts-inline-delta-..."), which Streamlit renders
   as a .st-key- class. Applied globally it would also catch every other
   metric's delta. (The review queue's filtered "of 238" sat under its count
   for that reason until 2026-10-06, when its tile joined the inline pills at
   the user's request, sharing the pill with "n already done".) */
/* A CAPTION AND THE BUTTON IT NAMES, read as one thing. Streamlit's block gap
   separates every element by the same amount, which is right between sections
   and far too much between a sentence ending "clear it to go back" and the
   Clear button that sentence is pointing at. Opt-in by key so no other pair
   moves. */
/* BOTH SELECTORS ON PURPOSE. st.container(key=...) puts the st-key- class on a
   wrapper in some Streamlit versions and on the vertical block itself in
   others, and the flex `gap` only exists on the block. Setting it on the
   wrapper alone did nothing at all - the first attempt at this rule. */
[class*="st-key-fts-tight"],
[class*="st-key-fts-tight"] [data-testid="stVerticalBlock"] { gap:.35rem; }

[class*="st-key-fts-inline-delta"] [data-testid="stMetric"] > div {
    display: flex; flex-wrap: wrap; align-items: flex-end; column-gap: .5rem;
}
[class*="st-key-fts-inline-delta"] [data-testid="stMetricLabel"] { flex: 0 0 100%; }
[class*="st-key-fts-inline-delta"] [data-testid="stMetric"] > div
    > div:has(> [data-testid="stMetricDelta"]) { display: contents; }
[class*="st-key-fts-inline-delta"] [data-testid="stMetricDelta"] {
    margin-bottom: 1rem;
    /* Streamlit gives the pill 4px of left padding and 6px of right, which is
       enough for a percentage flanked by an arrow and too tight for a word:
       "faster" sat against both ends of its own background. Horizontal only -
       growing it vertically would move the bottom edge off the baseline the
       rule above puts it on.
       .5rem and no more: a row of five metrics on a 1280px window gives each
       column 146px, and value + gap + pill has to fit inside it. At .625rem
       both pills tipped over and wrapped back under their value, which costs
       the whole point of the change to buy 2px of air. */
    padding-left: .5rem; padding-right: .5rem;
}

/* "faster" and "slower" are words, not arithmetic. Streamlit picks the delta
   arrow from a leading minus, so both readings carry the same UP arrow - an
   arrow pointing up beside the word "faster". The word already says the
   direction; the arrow can only contradict it. */
.st-key-fts-inline-delta-hours [data-testid="stMetricDelta"] svg,
.st-key-fts-inline-delta-today [data-testid="stMetricDelta"] svg { display: none; }
/* The "n already done" pills on Overview and the Review queue, beside the value
   like the ones above (same container prefix, same spacing): a count, not a
   trend, so no arrow either. */
[class*="st-key-fts-inline-delta-pill"] [data-testid="stMetricDelta"] svg { display: none; }

/* The line under a page title that says WHICH unit this is: part type, step,
   and whether one part or a whole family. It was st.caption - 14px at 60%
   opacity, the same treatment as a footnote under a chart - and it is not a
   footnote, it is the identity of everything below it.
   Set to match st.subheader exactly - 28px, weight 600, full opacity, the same
   -0.14px tracking - so the identity of the unit carries the same weight as the
   section headings below it rather than less. Measured off the rendered h3
   rather than guessed, because Streamlit's heading sizes are not the browser
   defaults, and pulled up so it reads as part of the heading rather than as the
   first line of content. */
.fts-subtitle { font-size:1.75rem; font-weight:600; line-height:1.2;
               letter-spacing:-.005em; opacity:1; margin:-.4rem 0 1rem; }

/* Markdown tables fill whatever holds them, like every other block in this app.
   Streamlit leaves them at width:auto, so a table sized to its own content and
   stopped short of the column edge - fine at a narrow window, where the content
   wanted more room than there was, and visibly ragged on a wide one, where a
   half-width column ended 100px before the block beside it did.
   Scoped to stMarkdown so it cannot reach the Vega tooltip, which is also a
   table and is appended outside the app tree. */
[data-testid="stMarkdown"] table { width: 100%; }
/* THE DECISION TABLE'S COLUMNS, fixed (user, 2026-10-06): Inspect's "How this
   was decided" table and its copy on How to read it. Left to the browser, the
   long third column took the width and "master today" or "2.016 (+101.6%)"
   wrapped, differently on every unit. Only tables inside this keyed container. */
.st-key-fts-decided-table table { table-layout:fixed; }
.st-key-fts-decided-table th:nth-child(1) { width:18%; }
.st-key-fts-decided-table th:nth-child(2) { width:20%; }
.st-key-fts-decided-table th:nth-child(3) { width:62%; }

/* Vega draws its tooltip as a two-column table and leaves the cells at the
   default vertical-align:middle. Fine while every value is one line; wrong the
   moment one wraps, because the label floats to the MIDDLE of its paragraph
   instead of sitting beside the line it names. Top-aligned, a label always
   starts level with the first line of what it labels.
   #vg-tooltip-element is appended to document.body, outside the app tree, so
   this is the only place it can be reached from. max-width keeps a long note
   from stretching into a single line across the window. */
#vg-tooltip-element td.key,
#vg-tooltip-element td.value { vertical-align: top !important; }
#vg-tooltip-element td.value { max-width: 340px; }

/* The six rules, 3 x 2. grid-auto-rows:1fr is what makes every box the same
   height - rows size to the tallest card rather than to their own content.
   FIXED AT THREE COLUMNS, not auto-fit: auto-fit packs in as many as will fit,
   so a wide window laid the six out 5 + 1 and the pairing of rows 1-3 and 4-6
   disappeared. Stepped down explicitly instead, so a narrow pane still works. */
.fts-rules { display:grid; gap:.7rem; grid-auto-rows:1fr;
            grid-template-columns:repeat(var(--fts-cols, 3), 1fr); }
@media (max-width: 900px) {
    .fts-rules { grid-template-columns:repeat(2, 1fr); } }
@media (max-width: 600px) {
    .fts-rules { grid-template-columns:1fr; } }
/* FILL - the six results end level with the table beside them (Inspect, since
   the "master today" row made that table a row taller than the cards). The
   column already stretches to the row's height; these carry that height down
   through Streamlit's wrappers to the grid, whose 1fr rows then share it. */
[data-testid="stElementContainer"]:has(.fts-rules-fill) { flex:1 1 auto; }
[data-testid="stElementContainer"]:has(.fts-rules-fill) > [data-testid="stMarkdown"],
[data-testid="stMarkdown"]:has(.fts-rules-fill) > div,
[data-testid="stMarkdownContainer"]:has(> .fts-rules-fill),
.fts-rules-fill { height:100%; }
/* Streamlit centres that wrapper and gives the markdown block a -1rem bottom
   margin, which together push the grid 8px below the table's top edge. */
[data-testid="stMarkdown"]:has(.fts-rules-fill) > div { align-items:flex-start; }
[data-testid="stMarkdownContainer"]:has(> .fts-rules-fill) { margin-bottom:0; }
/* Stretched, each card is taller than its two lines, so they sit in its
   middle rather than at its top (user, 2026-10-06). */
.fts-rules-fill .fts-rule { justify-content:center; }
.fts-rule { border:1px solid rgba(128,128,128,.35); border-radius:.55rem;
           padding:.85rem 1rem; display:flex; flex-direction:column;
           gap:.5rem; }
.fts-rule-name { font-weight:700; font-size:1rem; }
/* The result-only variant: a mark, a name and this unit's figure, no sentence.
   Tighter than .fts-rule because there are six of them beside a table rather
   than six across a page, and the explanations live on the full set elsewhere.
   The figure is the thing being read, so it is the one line at full opacity. */
.fts-rule-tight { padding:.55rem .7rem; gap:.28rem; }
.fts-rule-tight .fts-rule-name { font-size:.92rem; }
.fts-rule-val { font-size:.92rem; font-weight:600; }
/* Rides on the rule's own name line, so it inherits the red rather than setting
   it. Smaller and tracked out, so it reads as a stamp on the rule rather than
   as part of what the rule is called. */
.fts-rule-stop { font-size:.72rem; letter-spacing:.05em; }
/* No margin-top:auto here. Pushing this to the foot of the card left a gap of a
   different size under every pill, so six boxes of identical height still read
   as six different layouts. The text follows the pill and the slack collects at
   the bottom, where it is the same shape in each. */
/* THE CARD BODY when the six rules are drawn as native containers rather than
   as the CSS grid. .fts-rule supplies `gap:.5rem` between name, pill and
   sentence; in the container path the name is its own st.markdown - so it can
   carry help= - and only the pill and the sentence are left inside one HTML
   block. Without this they butt straight up against each other. */
.fts-rule-body { display:flex; flex-direction:column; gap:1rem; }
/* 1rem ABOVE the pill as well as below it. The rule name is its own
   st.markdown in that path - so it can carry help= - which means the space
   above the pill comes from Streamlit's own vertical block gap. That is 16px,
   and matching it here rather than cutting it to .5rem keeps the pill sitting
   evenly between the name it belongs to and the sentence under it.

   An earlier version set both to .5rem, which is what .fts-rule uses in the grid
   path. Even, but tighter than the rest of the app; 1rem is Streamlit's own
   rhythm and the card has room for it.

   NO BLOCK-GAP OVERRIDE ANY MORE: 16px is what stVerticalBlock already gives,
   so the only thing to set is this one. */

.fts-rule-stops { font-size:.84rem; opacity:.75; }

/* Key for the distribution chart: every mark it can draw, in two columns.
   Sized off the caption scale because it is a caption in every sense except
   that it happens to contain colour.

   TWO EXPLICIT COLUMNS, not CSS `columns:2`. The split carries meaning - what
   the chart draws and counts on the left, what it drew but left out of the
   test on the right - and a column rule would break wherever the halves
   happened to balance, which is not where the meaning divides. Collapses to
   one column under 40rem so the labels, several of them long, never get a
   column half a sentence wide. */
/* Sidebar label/value blocks. Two levels from weight and opacity, no hue -
   every colour in this tool carries a meaning and a tinted panel would be the
   first thing on screen colouring for looks. Opacity rather than a fixed grey
   so it holds in both light and dark: it is relative to whatever text colour
   the theme already set. */
/* Zero margins on the OUTER edges of these blocks, so the divider between two
   of them is the only thing creating the gap and the space above it equals the
   space below by construction. With a bottom margin on .fts-kv and a top margin
   on .fts-kv-title the two sides were built from different elements - 8px one
   side, 5.6px the other - and the rule sat 2px off centre. Symmetric now
   whatever the font metrics do. */
/* .9375rem, up from .82rem. At .82 the heading was SMALLER than the rail it
   heads - Streamlit's widget labels are 14px - so on Inspect, Review queue and
   By part, whose rails are made of widgets, "What to look at" read as a caption
   over its own controls rather than as their heading. 15px clears the 14px
   labels and the 13.12px kv rows while staying well under the 18px h3 that
   side_title was written to replace.
   ONE RULE FOR ALL EIGHT BLOCKS - every sidebar heading in the app arrives
   here, either through side_title or through kv, so the sizes cannot drift
   apart again.
   .9375rem (15px) after trying 1rem: 16px reads as body text set bold, which
   competes with the rail rather than heading it. 15px sits clear of the 14px
   widget labels without becoming a second voice. */
.fts-kv-title { font-size:.9375rem; font-weight:700; opacity:.9;
               margin:0 0 .35rem; }
/* Small print in a sidebar. st.caption renders at 14px, the h3 a heading would
   use renders at 18px, and the rail below at 15.2 - four sizes in one column,
   none of them the .82rem the key/value blocks settled on. */
.fts-side-note { font-size:.82rem; line-height:1.5; opacity:.72;
                margin:.1rem 0 .55rem; }
/* The explain rendering of the legend, shrunk to match. NOT .fts-rail itself:
   that is Inspect's six-rule rail, which is the main device on that page and
   is meant to be read, not skimmed. Same markup, sidebar-footnote size. */
.fts-rail-sm .fts-name { font-size:.82rem; }
/* Matched to .fts-side-note, not merely to its size. The two were already both
   13.12px at weight 400, so what still separated them was opacity - .85
   against .72 - and a tighter line-height. Two greys a hair apart read as a
   mistake rather than a distinction. */
.fts-rail-sm .fts-val { font-size:.82rem; opacity:.72; line-height:1.5; }
.fts-kv { font-size:.82rem; line-height:1.55; margin:0; }
.fts-kv-row { display:flex; justify-content:space-between; align-items:baseline;
             gap:.9rem; margin:.12rem 0; }
/* The row spacing must not leak out of the block. Zeroing .fts-kv's own margins
   was not enough: the LAST row still carried .12rem below it, inside the block,
   which is the 2px that kept the divider off centre - 22px above against 20
   below. Same at the top, so the gap under a title is the title's to set. */
.fts-kv-row:first-child { margin-top:0; }
.fts-kv-row:last-child { margin-bottom:0; }
/* .62 was too far down on a dark background - and these labels are not
   decoration, "first" against "last" labour ticket is a distinction that has to
   be read. Subordinate to the value, still legible on its own. */
.fts-kv-k { opacity:.72; }
/* The value sits on a tint rather than being bolded. Bold was carrying the
   separation before and it made a column of shouted numbers; a quiet panel
   behind them does the same job without raising the voice.

   rgba(128,128,128,...) on purpose - a mid grey lightens a dark background and
   darkens a light one, so one declaration holds in both themes. A white or
   black tint would vanish in one of them. */
.fts-kv-v { font-weight:400; white-space:nowrap;
           background:rgba(128,128,128,.20); border-radius:4px;
           padding:.05rem .38rem; }

.fts-key { display:grid; grid-template-columns:repeat(2, minmax(0, auto));
          justify-content:start; gap:.35rem 2.4rem; margin:.4rem 0 .2rem;
          font-size:.82rem; opacity:.85; }
.fts-k-col { display:flex; flex-direction:column; gap:.35rem; }
@media (max-width:40rem) { .fts-key { grid-template-columns:minmax(0, 1fr); } }
.fts-k-item { display:inline-flex; align-items:center; gap:.4rem; }
.fts-k-dot { width:.7rem; height:.7rem; border-radius:50%;
            display:inline-block; }
.fts-k-line { width:1.1rem; height:0; display:inline-block; }

.fts-fstep { margin-bottom:.5rem; }
/* bar and its value share a row, so a bar too narrow to hold the number can
   put it alongside instead of being padded out to fit */
.fts-fbarrow { display:flex; align-items:center; gap:.5rem; }
.fts-fbar { height:26px; border-radius:5px; display:flex; align-items:center;
           padding-left:.55rem; font-size:.78rem; font-weight:600;
           color:#fff; white-space:nowrap; min-width:2.6rem; }
/* no floor on the narrow ones - the floor is what made 215 and 59 identical */
.fts-fbar.fts-narrow { min-width:0; padding-left:0; }
.fts-fout { font-size:.78rem; font-weight:700; white-space:nowrap; }
.fts-flabel { font-size:.95rem; font-weight:600; margin-bottom:.2rem; }
.fts-fnote { font-size:.82rem; opacity:.75; margin-top:.1rem; }
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


def rule_cards(container, rules, per_row=3, methods=None):
    """The six rules as cards: number, name, threshold, what it stops.

    TWO RENDERINGS, and which one runs depends on whether `methods` is given.

    WITHOUT methods - one markdown block, own CSS grid. st.columns(3) does not
    lay out two rows of three; it lays out three columns of two, and each box
    takes the height of its own sentence - the six rendered 252, 162, 185, 185,
    210 and 162 pixels tall. `grid-auto-rows:1fr` is what makes them equal.

    WITH methods - six st.container(height=...) in two rows of st.columns, each
    holding an st.markdown(help=...). This is the ONLY way to get Streamlit's
    real help tooltip: `help=` is a property of a Streamlit ELEMENT, rendered as
    a React component beside that element's label, so it cannot be pasted into a
    raw HTML string however faithfully the icon is copied.

    The heights come back a different way. `height=` on a container is an
    explicit pixel box, so all six match by construction rather than by CSS -
    and content longer than the box scrolls inside it instead of stretching the
    row, which is the failure mode to prefer: visibly clipped beats silently
    ragged.

    THREE EARLIER ATTEMPTS, all withdrawn on 2026-08-27 and recorded so nobody
    re-derives them: a hand-drawn "?" glyph with title=; the same on the
    threshold pill; and Streamlit's own help-circle SVG lifted from the DOM,
    matched to 16x16 and 2.25px stroke. All three produced the right ICON and
    the browser's own tooltip panel, which does not look like Streamlit's.
    """
    rules = list(rules)
    methods = list(methods or [])

    def card_html(i, name, req, stops, with_name=True):
        head = (f'<div class="fts-rule-name">{i}. {_e(name)}</div>'
                if with_name else "")
        body = (f'<div>{chip(req, INFO)}</div>'
                f'<div class="fts-rule-stops"><b>Stops:</b> '
                f'{_e(stops[:1].lower() + stops[1:])}</div>')
        # Wrapped only when the name is elsewhere: inside .fts-rule the grid path
        # already spaces these three, and a second flex column would double it.
        return (f'{head}{body}' if with_name
                else f'<div class="fts-rule-body">{body}</div>')

    if methods:
        # 190px, and the longest "stops" sentence (117 chars) still leaves
        # visible space below it at a third of the page width. It was briefly
        # raised to 210 on the assumption that widening the gaps to 1rem would
        # overflow - measured wrong: what got measured was the inner block's
        # scrollHeight, which simply fills the container and says nothing about
        # the text. The card had room all along.
        #
        # A sentence long enough to overflow scrolls inside the box rather than
        # breaking the row - visibly clipped beats silently ragged.
        for start in range(0, len(rules), per_row):
            cols = container.columns(per_row)
            for col, (i, (name, req, stops)) in zip(
                    cols, list(enumerate(rules, 1))[start:start + per_row]):
                with col.container(border=True, height=190):
                    # The NAME carries help=, so the icon lands beside the rule
                    # it explains rather than beside the box.
                    st.markdown(f"**{i}. {name}**",
                                help=methods[i - 1] if i <= len(methods)
                                else None)
                    st.markdown(card_html(i, name, req, stops,
                                          with_name=False),
                                unsafe_allow_html=True)
        return

    cards = "".join(f'<div class="fts-rule">{card_html(i, n, r, s)}</div>'
                    for i, (n, r, s) in enumerate(rules, 1))
    container.markdown(
        f'<div class="fts-rules" style="--fts-cols:{per_row}">{cards}</div>',
        unsafe_allow_html=True)


def rule_results(container, results, per_row=2, fill=False):
    """The six rules with this unit's own figure, and nothing else.

    The same six cards as rule_cards, minus the explanation of what each rule
    stops. That sentence is worth reading once - it is on Methodology, and on
    Inspect where somebody is deciding a single standard - but here the cards sit
    beside the result table as the evidence that the six were checked, and six
    paragraphs would out-weigh the thing they support.

    EVERY FAILURE IS RED; only the first carries "(STOPPED)". Colour answers the
    question a reader asks six times over - did this rule pass - and the stamp
    answers the one they ask once, which rule decided. It matters because
    recommend() returns at the first failing condition, so the reason written
    into the workbook is that rule and no other.

    Its own CSS grid, not st.columns - st.columns(2) lays out two columns of
    three and sizes each box to its own content, so the six come out six
    different heights. grid-auto-rows:1fr is what makes them equal.

    fill=True stretches the grid to the height of its column, so the cards end
    level with whatever sits beside them - see .fts-rules-fill in CSS.
    """
    blocker = next((i for i, g in enumerate(results) if not g["passed"]), None)
    cards = []
    for i, g in enumerate(results):
        ok = g["passed"]
        colour = PASS if ok else FAIL
        mark = "&#10003;" if ok else "&#10005;"
        # INLINE, on the name, rather than a line of its own underneath. The
        # separate line cost every one of the six cards a row of height - the
        # grid sizes them all to the tallest - to mark one of them. Four
        # characters on the end of the name buy the same thing for nothing.
        #
        # No colour of its own: the whole name line is already FAIL-red, since
        # only a failing rule can be the blocker.
        stop = (' <span class="fts-rule-stop">(STOPPED)</span>'
                if i == blocker else "")
        cards.append(
            f'<div class="fts-rule fts-rule-tight">'
            f'<div class="fts-rule-name" style="color:{colour}">'
            f'{mark} {i + 1}. {_e(g["name"])}{stop}</div>'
            f'<div class="fts-rule-val">{_e(g.get("value", ""))}</div>'
            f'</div>')
    container.markdown(
        f'<div class="fts-rules{" fts-rules-fill" if fill else ""}" '
        f'style="--fts-cols:{per_row}">'
        f'{"".join(cards)}</div>', unsafe_allow_html=True)
    return blocker


def chart_key(container):
    """Every mark the distribution chart can draw, whether or not it is drawn.

    The chart's own legend lists only the statuses PRESENT in that unit, which
    is right there and wrong here: a reader learning the chart from one example
    sees two dot colours and no mention of the two rules, which are the marks
    the whole thing is about. Built from charts.COLOURS and the evidence status
    constants, so a status added there appears here without being retyped.

    Two columns, split on whether the label says "excluded": what the chart
    draws and counts on the left, what it drew but kept out of the test on the
    right. DERIVED FROM THE LABEL, not a hard-coded row count - the strings in
    evidence.py already carry that distinction, and a fixed split would put a
    status added later into whichever column the arithmetic happened to land on.
    """
    from . import charts, evidence

    line = ('<span class="fts-k-line" style="border-top:2.5px {0} {1}">'
            '</span>')
    # The two rules head the left column: they are marks the chart always
    # draws, not evidence it set aside.
    # Named exactly as the chart labels them. The red line is "measured", not
    # "the correction": it is drawn on every unit, and on one that produced no
    # action there is no correction for it to be.
    counts = [line.format("dashed", "#555555")
              + "standard — the master as it stands",
              line.format("solid", "#c0392b")
              + "measured — where the jobs actually ran"]
    left_out = []
    for status in evidence.EXCLUDED_FIRST:
        mark = (f'<span class="fts-k-dot" '
                f'style="background:{charts.COLOURS[status]}"></span>'
                f'{_e(status)}')
        (left_out if status.startswith("excluded") else counts).append(mark)

    def _col(items):
        return ('<div class="fts-k-col">'
                + "".join(f'<span class="fts-k-item">{i}</span>' for i in items)
                + "</div>")

    container.markdown('<div class="fts-key">' + _col(counts) + _col(left_out)
                       + "</div>", unsafe_allow_html=True)


def side_title(container, text):
    """A sidebar block heading. One rendering for all of them.

    st.markdown("### ...") gave an 18px h3 next to a 13px block heading in the
    same column - the two blocks on this page were built at different times and
    it showed.
    """
    container.markdown(f'<div class="fts-kv-title">{_e(text)}</div>',
                       unsafe_allow_html=True)


def side_note(container, text):
    """Small print under a sidebar block. st.caption's 14px in .82rem terms."""
    container.markdown(f'<div class="fts-side-note">{text}</div>',
                       unsafe_allow_html=True)


# A unit judged on the whole family rather than on one part. TWO CASINGS: WHOLE
# is a menu option and takes a capital, WHOLE_INLINE runs inside a sentence.
#
# HERE RATHER THAN ON A PAGE, because two now need it - Inspect's "Judged at"
# picker and subtitle, and the Review queue's Applies to column, which reaches
# the same idea from the other side by compacting the workbook's sentence. A
# picker's value is compared against WHOLE, so a second copy differing by a
# space would silently turn a family into a part.
# "Whole family", not "family as a whole". Five characters shorter and it says
# the same thing, which decides it: the phrase now has to fit a table cell on the
# Review queue as well as a picker and a subtitle on Inspect, and a cell is where
# width actually costs something.
WHOLE = "Whole family"
WHOLE_INLINE = "whole family"

def done_pill(n_done):
    """The "n already done" pill on the Standards / Operations rows tiles of
    Overview and the Review queue, or None when there is nothing done. The
    number beside it is unchanged - an action stays an action - and the pill
    says how much of it today's master already carries."""
    return f"{num(n_done)} already done" if n_done else None


def done_help(n_done, n_partly=None, noun="standards"):
    """The sentence those tiles' tooltips gain, or "" - one wording for both
    pages. n_partly only applies to decisions; a routing row is either done
    or not."""
    if not n_done and not n_partly:
        return ""
    first = n_done or n_partly
    verb = "is" if first == 1 else "are"
    if n_done:
        what = f"{num(n_done)} of these {noun} {verb} already done"
        if n_partly:
            what += f" and {num(n_partly)} partly done"
        where = ""
    else:
        what = f"{num(n_partly)} of these {noun} {verb} partly done"
        where = " on some of their parts"
    return (f" In today's master, {what}: it holds the value proposed to "
            f"within 10%{where}. They are still counted here.")


def today_check(container, entries, more, n_type, total, noun, lo, hi):
    """The amber "check this against today's master" box - one wording for
    Inspect (one unit, its parts) and By part (one part, its rows).

    entries  up to three flagged rows as (where, proposed, today, multiple):
             `where` names the row - a part number on Inspect, "<operation>
             step <n> (<analysis>)" on By part - or is None when the unit has
             a single row; proposed and
             today are formatted with their unit; multiple is proposed/today,
             or None when today is zero
    more     how many further band-flagged rows were not named
    n_type   rows whose master no longer holds the analysed run type
    total    how many rows the unit has, and `noun` what they are called
    """
    said = [(f"on {w} the proposal is " if w else "the proposal is ")
            + f"{p} against {t} in today's master"
            + (f" — {m:.1f}×" if m is not None else "")
            for w, p, t, m in entries]
    txt = "; ".join(said)
    if more:
        txt += f"; and {more} more of the {total} {noun}"
    msg = "**Check this against today's master.** "
    if said:
        msg += (txt[0].upper() + txt[1:]
                + f" — outside the {lo}–{hi} band where a change is flagged "
                  f"for manual review.")
    if n_type:
        msg += (f" On {n_type} of {total} {noun} today's master no longer "
                f"holds this run type, so the value proposed does not apply "
                f"as it stands.")
    container.warning(msg, icon=":material/pan_tool:")


def status_name(status):
    """ACTION_STATUS (per decision) or TODAY_STATUS (per routing row) as a
    table cell - the workbook's words, shortened only where they repeat what
    the column header already says.

        already done - within 10% of today's master   -> already done
        partly done - 31 of 32 parts                  -> partly done (31 of 32)
        check - run type changed on today's master    -> check: run type changed
        to key                                        -> to key

    Blank stays blank: an update list written before the pipeline added the
    column has no status, and "to key" would claim one. Anything unrecognised
    passes through unchanged, the same fallback rule as part_tag.
    """
    if status is None or pd.isna(status) or not str(status).strip():
        return ""
    s = str(status).strip()
    if s.startswith("already done"):
        return "already done"
    m = re.match(r"partly done - (\d+) of (\d+)", s)
    if m:
        return f"partly done ({m.group(1)} of {m.group(2)})"
    if s.startswith("check - run type changed"):
        return "check: run type changed"
    return s


def applies_to(part_id, level):
    """A part number, or "whole family", from the workbook's own LEVEL.

    THE PART NUMBER, NOT "this part", which is what By part showed until
    2026-09-01. The argument for the phrase was that the page already names the
    part in its title, so the number down a column restates the heading. The
    argument against it won: the Review queue prints the number in the column
    under this heading, and a reader who learns what that column looks like
    there should not meet a different vocabulary for the same fact one page
    over. Consistency across the tool beats saving a repetition on one screen.

    The Review queue keeps its own applies_to(part_id, level) because 01_Actions
    writes a SENTENCE into PART_ID on family rows - "every part of this family
    that performs the setup" - which has to be compacted before it can sit in a
    cell. Nothing reaches this one but a clean part number and a level, so it
    has no sentence to compact. Both produce the same two shapes.
    """
    return str(part_id) if str(level).upper() == "PART" else WHOLE_INLINE


# WHAT THE VERDICT SHOULD HAVE SAID ALL ALONG: which scope, and which ERP
# field. The pipeline writes five different UPDATE phrasings, and they name its
# own sheets rather than anything the reader can act on:
#
#   UPDATE RUN_MASTER       run PCS/HR,   one part      -> OPERATION.RUN
#   UPDATE RUN              run HRS/LOAD, one part      -> OPERATION.RUN
#   UPDATE FAMILY STANDARD  run PCS/HR,   whole family  -> OPERATION.RUN
#   UPDATE FAMILY RUN       run HRS/LOAD, whole family  -> OPERATION.RUN
#   UPDATE SETUP_HRS        setup,        whole family  -> OPERATION.SETUP_HRS
#
# Four of the five are the same edit to the same column. RUN_MASTER is not an
# ERP field at all - it is this analysis's name for the master's RUN value - so
# "UPDATE RUN_MASTER" beside "UPDATE RUN" invites reading two different fields
# where there is one. Checked over all 2'468 edit rows on 2026-09-02: the
# verdict is fully determined by the analysis and the level, in both
# directions, so nothing is lost by collapsing five strings into three.
#
# WHICH ANALYSIS PRODUCED THE ROW IS NOT THROWN AWAY. It moves to where it was
# already being read - the Analysis column, which says "Run PCS/HR" or "Run
# HRS/LOAD" in the app's own three words rather than in the sheet's.
#
# DISPLAY ONLY, deliberately. These strings are control flow at twenty call
# sites across five pipeline scripts - fts_analysis, fts_family_view,
# fts_setup_view, fts_load_view and fts_update_list all filter frames on them
# by equality. Renaming them at source is a real change needing a full re-run
# and rewriting every workbook; renaming them here is a caption. The workbooks
# therefore keep the five, which matters to anyone filtering the .xlsx by hand.
#
# evidence.outcome() is unaffected either way: it tests startswith("UPDATE"),
# and it reads the raw verdict, not this.
_VERDICTS = {
    "UPDATE RUN_MASTER": "UPDATE PART RUN",
    "UPDATE RUN": "UPDATE PART RUN",
    "UPDATE FAMILY STANDARD": "UPDATE FAMILY RUN",
    "UPDATE FAMILY RUN": "UPDATE FAMILY RUN",
    "UPDATE SETUP_HRS": "UPDATE FAMILY SETUP_HRS",
}


_SHORTER = {"watch - master changed recently, too few work orders on it":
            "watch - master changed recently, too few work orders"}


def verdict_name(verdict, run_type=None):
    """The workbook's verdict, said as scope + field + analysis.

    ONLY THE UPDATE VERDICTS ARE MAPPED. The rest - "insufficient data (n<6)",
    "family OK - not different", "watch - master changed recently" - already
    say what they mean, and they are most of the rows on a table that lists
    every step examined rather than only the ones that change.

    THE ANALYSIS IS NAMED IN THE STRING because scope and field alone do not
    separate the two run analyses, and those two behave OPPOSITELY on the same
    ERP column: PCS/HR RUN is a rate and the correction divides, HRS/LOAD RUN
    is a duration and it multiplies. Without the qualifier a verdict read on
    its own - sorted in a downloaded file, pasted into a mail - covers both.
    The Analysis column beside it says the same thing, and that redundancy is
    the point: each row has to survive being read one row at a time.

    IT COMES FROM THE ROW, not from the mapping. Each workbook string does in
    fact belong to exactly one analysis today, so this could have been folded
    into _VERDICTS - but then the label would keep asserting an analysis the
    row no longer had if that ever stopped being true. RUN_TYPE is the same
    column ui.analysis_name reads, so the two cannot disagree.
    """
    if verdict is None or pd.isna(verdict):
        return verdict
    base = _VERDICTS.get(str(verdict).strip())
    if base is None:
        # SHORTER ON SCREEN (user, 2026-10-08): "on it" dropped, so the
        # longest verdict fits By part's Verdict column. The workbook keeps
        # fts_analysis's own text; nothing matches on this one.
        return _SHORTER.get(str(verdict).strip(), verdict)
    # Setup carries RUN_TYPE "-" and its verdict already names SETUP_HRS, which
    # only one analysis ever writes - so there is nothing to disambiguate.
    if base.endswith("RUN") and run_type is not None and not pd.isna(run_type) \
            and str(run_type) not in ("", "-"):
        return f"{base} ({run_type})"
    return base


def effect_from_ratio(ratio):
    """"slow down" / "speed up" - what the change does to the time the standard
    allows, which is NOT the direction the field's own number moves.

    01_Actions carries this as DIRECTION and the Review queue shows it, with
    " the standard" stripped off. The rollup sheets do not carry it, and most of
    what By part shows comes from them - so it is derived here instead.

    DERIVING IT IS EXACT, not an approximation: checked against all 238 rows of
    01_Actions on 2026-09-01, DIRECTION is "slow down the standard" on every row
    with RATIO > 1 and "speed up the standard" on every row with RATIO < 1,
    without exception. The ratio is actual hours over master hours, so above 1
    the work takes longer than the standard allows and the standard has to slow
    down - whichever way the field's own number then has to move.
    """
    if ratio is None or pd.isna(ratio):
        return ""
    return "slow down" if float(ratio) > 1 else "speed up"


def part_tag(value, with_title=True):
    """ADV / ANDV. The part type only has to disambiguate, not describe.

    LIVES HERE, not in charts.py, because it is no longer only a chart concern:
    the Overview rankings abbreviate it to fit an axis, and Inspect abbreviates
    it in the line under the title. One mapping, so a reader who learns "ADV" in
    one place is not shown "Articolo di vendita" in the other and left to work
    out whether they are the same thing.

    Anything unrecognised falls back to its initials rather than defaulting to
    one of the two, so a third part type shows up as itself instead of silently
    joining a bucket it does not belong to.

    with_title wraps it so hovering restores the full wording. Free where the
    output is HTML; impossible on a Vega axis label, which is why it is optional
    rather than always on.
    """
    t = str(value).strip().lower()
    if t.startswith("articolo"):
        short = "ANDV" if " non " in f" {t} " else "ADV"
    else:
        short = "".join(w[0] for w in str(value).split()).upper() or "?"
    if not with_title:
        return short
    return f'<span title="{_e(value)}">{short}</span>'


def subtitle(container, text):
    """The identity line under a page title - which unit this page is about.

    Not st.caption. A caption is for something subordinate to what it sits
    under, and this is the opposite: every figure below it is only meaningful
    once you know it belongs to this part, this step, this pool.
    """
    container.markdown(f'<div class="fts-subtitle">{text}</div>',
                       unsafe_allow_html=True)


def kv(container, title, pairs):
    """A sidebar block of label/value rows.

    NO HUE. Every colour in this tool means something - green/red/amber are
    rule outcomes, blue is "counted" - and "How to read it" says out loud that
    nothing is coloured for looks. Tinting a provenance panel would be the
    first thing on screen to contradict that.

    The contrast comes from weight and opacity instead: label at 62%, value at
    full strength and semibold. That reads as two levels on any background, and
    it survives the light/dark switch because opacity is relative to whatever
    the theme's text colour already is - a hard-coded grey would not.

    Everything was st.caption before, which is one muted grey throughout, so
    the numbers - the only part anybody scans for - carried no more weight than
    the words around them.
    """
    rows = "".join(
        f'<div class="fts-kv-row"><span class="fts-kv-k">{_e(k)}</span>'
        f'<span class="fts-kv-v">{_e(str(v))}</span></div>'
        for k, v in pairs)
    side_title(container, title)
    container.markdown(f'<div class="fts-kv">{rows}</div>',
                       unsafe_allow_html=True)


def thresholds(container):
    """The numbers the six rules fire on.

    ONE RENDERING, TWO PAGES. Methodology is where the rules are enumerated and
    "How to read it" is where they are explained, so both want them pinned in
    the sidebar while the reader scrolls. Copying the block would be the same
    mistake the two colour legends made - except these are read from the
    analysis modules rather than typed, so the risk is a stale LABEL rather
    than a stale number.

    Imported inside the function, matching chart_key below: ui is the lowest
    layer in this package and pulling pipeline in at module scope would invert
    that.
    """
    from . import pipeline

    kv(container, "Thresholds in force", [
        ("Minimum work orders", pipeline.MIN_WO),
        ("Significance", pipeline.ALPHA),
        ("Minimum deviation", f"{pipeline.MIN_EFFECT:.0%}"),
        ("Minimum impact", f"{pipeline.MIN_HOURS_IMPACT:g} h "
                           f"({pipeline.SETUP_MIN_HOURS:g} h setup)"),
        ("Token booking", f"≤ {pipeline.TOKEN_HOURS} h"),
    ])


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


def help_icon(title):
    """Streamlit's help glyph, for use inside hand-built HTML.

    The SVG is Streamlit's own, lifted from the rendered DOM so the two cannot
    drift apart by redrawing. See the note on .fts-help in CSS for what this
    does and does not reproduce.
    """
    return (f'<span class="fts-help" title="{_e(title)}" role="img" '
            f'aria-label="{_e(title)}">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
            f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true" focusable="false">'
            f'<circle cx="12" cy="12" r="10"></circle>'
            f'<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>'
            f'<line x1="12" y1="17" x2="12.01" y2="17"></line>'
            f'</svg></span>')


def chip(label, colour):
    return (f'<span class="fts-chip" style="color:{colour};border-color:{colour};'
            f'background:{colour}1a">{_e(label)}</span>')


def verdict_banner(container, verdict, kind, detail=""):
    """kind: 'act' | 'review' | 'caution' | 'hold' | 'blocked' | 'unknown'.

    Amber covers 'review' and 'caution' and nothing else, so it keeps one
    meaning: do not act on this as it stands. 'unknown' was borrowing amber to
    get itself noticed, which gave the colour a second meaning - no verdict
    recorded - and the legend only promises the first.
    """
    colour = {"act": PASS, "review": WARN, "caution": WARN, "hold": INFO,
              "blocked": MUTE, "unknown": MUTE}.get(kind, INFO)
    sub = f'<div class="fts-b-sub">{_e(detail)}</div>' if detail else ""
    container.markdown(
        f'<div class="fts-banner" style="border-color:{colour};'
        f'background:{colour}14"><div class="fts-b-title" '
        f'style="color:{colour}">{_e(verdict)}</div>{sub}</div>',
        unsafe_allow_html=True)


def funnel(container, sections, scale_to=None):
    """sections: list of (heading, unit_label, [(label, count, note), ...]).

    The whole analysis is a narrowing, and showing it as one makes the shape of
    the process legible before anybody reads a number: most of what was measured
    never becomes an action, and that is the design working rather than
    something missing.

    SECTIONS EXIST BECAUSE THE UNIT CHANGES MIDWAY. The first stages count
    booking lines, the later ones count part x routing-step combinations, and
    there is no conversion between them - one part-step is however many lines
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
        out.append(f'<div class="fts-fhead">{_e(heading)} · counted in '
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
                f'<div class="fts-fstep">'
                f'<div class="fts-flabel">{_e(label)}</div>'
                f'<div class="fts-fbarrow">'
                f'<div class="fts-fbar{"" if inside else " fts-narrow"}" '
                f'style="width:{pct:.1f}%;background:{colour}">'
                f'{val if inside else ""}</div>'
                + ("" if inside else
                   f'<div class="fts-fout" style="color:{colour}">{val}</div>')
                + f'</div><div class="fts-fnote">{_e(note)}</div></div>')
    container.markdown(f'<div class="fts-funnel">{"".join(out)}</div>',
                       unsafe_allow_html=True)


# THE ONE DEFINITION OF WHAT THE FOUR COLOURS MEAN. Both renderings below read
# it, so Inspect and the reference panel on "How to read it" cannot drift.
#
# They had drifted. Inspect said "rule passed" where the reference panel said
# "Green - the rule was satisfied", and the panel was missing the amber state
# entirely - so the page whose job is to teach the colours taught three of the
# four, in different words than the page that uses them. Amber is not
# hypothetical: it is the review flag, on 85 rows.
#
# (mark, colour, label, what it means on a unit)
# THREE STATES, not four. There was a fourth - a grey dash for "failed, but
# not the first to fail" - and a reader who met it had no way to guess what it
# meant; the dash itself reads as "not applicable" when it meant "failed". Every
# failure is red now, and the rule that decided is named in words on the rail
# and on the cards rather than distinguished by hue.
#
# THE AMBER LABEL IS THE WORKBOOK'S OWN. It read "needs a human before keying",
# which was a fourth name for a state the workbook writes as NEEDS REVIEW into a
# column called REVIEW_FLAG, that "How to read it" heads "Flagged for review",
# and that the Review queue called three further things. This legend renders in
# that page's sidebar, directly beside its own contradicting heading.
#
# "manual" is carried from the Review queue, where plain "flagged for review"
# collides with the page name and with its "Standards to review" tile. One
# string everywhere beats a shorter one that has to be qualified in one place.
STATES = [
    ("✓", PASS, "rule passed", "this unit cleared it"),
    ("✕", FAIL, "rule failed",
     "the first one to fail is marked stopped here"),
    # Terse on purpose, matching the two rows above it - this is a sidebar
    # legend at .82rem, not prose.
    #
    # NO PUNCTUATION IN IT. An em dash after "extreme" reads better and costs a
    # line: it pushes the row onto two in a 230px rail, where the other two
    # states sit on one. A legend that wraps stops looking like a legend.
    ("!", WARN, "flagged for manual review",
     "six rules passed but extreme needs check"),
]


def legend(container, explain=False):
    """The colour key.

    explain=False - compact chips, for a working page where the rail is on
    screen and the reader only needs reminding.
    explain=True  - each state on its own row with what it means, for the
    reference panel, where the rail is NOT on screen and the words are doing
    all the work.
    """
    if not explain:
        container.markdown(
            "".join(chip(f"{m} {label}", c) for m, c, label, _ in STATES),
            unsafe_allow_html=True)
        return
    rows = "".join(
        f'<div class="fts-step">'
        f'<div class="fts-dot" style="background:{c}">{m}</div>'
        f'<div class="fts-txt"><div class="fts-name">{_e(label)}</div>'
        f'<div class="fts-val">{_e(meaning)}</div></div>'
        f'</div>'
        for m, c, label, meaning in STATES)
    container.markdown(f'<div class="fts-rail fts-rail-sm">{rows}</div>',
                       unsafe_allow_html=True)


def summary_rail(container, items):
    """A plain counted summary. Deliberately NOT the six-rule treatment.

    Reusing the rule marks for a count of "what we found about this part"
    put a green tick beside "0 steps tested" and a red cross beside a part with
    nothing wrong with it - the same visual language carrying the opposite
    meaning one page over. Counts are not verdicts and must not look like them.
    """
    rows = []
    for label, value, note in items:
        rows.append(
            f'<div class="fts-count"><div class="fts-cval">{_e(value)}</div>'
            f'<div class="fts-txt"><div class="fts-name">{_e(label)}</div>'
            f'<div class="fts-val">{_e(note)}</div></div></div>')
    container.markdown(f'<div class="fts-rail">{"".join(rows)}</div>',
                       unsafe_allow_html=True)


def review_warning(container, current, suggested, ratio, lo, hi):
    """The banner that has to appear before anyone keys an extreme value.

    On a whole-family decision whose parts run different values there is no
    single current or suggested value, and the banner printed "— → —"
    (2026-10-08). It then names the ratio alone, applied to each part."""
    _what = (f"at {fmt(current)} → {fmt(suggested)}, a ratio of "
             f"{fmt(ratio, '.2f')}"
             if not (pd.isna(current) or pd.isna(suggested)) else
             f"at a ratio of {fmt(ratio, '.2f')}, applied to each part's own "
             f"value")
    container.warning(
        f"**Check this one by hand before keying it in.** The evidence points "
        f"{_what} "
        f"— outside the {lo}–{hi} band the analysis treats as ordinarily "
        f"believable. A change this large is usually a standard that never "
        f"described the job rather than a process that drifted, so it wants a "
        f"human who knows the step before it reaches the ERP.",
        icon=":material/pan_tool:")


def analysis_name(target, run_type):
    """Which of the three analyses a row came from.

    "Run PCS/HR", "Run HRS/LOAD", "Setup" - the same three strings Overview's
    hours table indexes on and data.coverage builds its ROUTE column from. Held
    here because a third copy of a three-way string mapping is how the three
    stop agreeing.

    NOT "Route", which both this screen and Methodology used to head it with.
    In a table carrying Step and Operation columns that word reads as the
    manufacturing routing - and it should, since the app says "routing step",
    "routing row" and "routing line" some forty times over. Analysis is
    Inspect's own word for the same three, and collides with nothing. Both
    screens now say Analysis; the underlying column is still ROUTE.

    THE ROUTE DETERMINES THE FIELD, which is why this can replace a field
    column rather than sit beside one: both run analyses edit RUN and setup
    edits SETUP_HRS, so naming the analysis names the field too. See field_name
    for the mapping and for why RUN_MASTER is not one of them.
    """
    if str(target) == "SETUP_HRS":
        return "Setup"
    return f"Run {run_type}"


def field_name(target, run_type, unit=False):
    """The ERP column an action edits, from what 01_Actions carries.

    THERE ARE ONLY TWO FIELDS, and RUN_MASTER is not one of them. fts.sql
    reads `CAST(O.RUN AS NUMERIC(19,2)) AS RUN_MASTER` from dbo.OPERATION, so
    RUN_MASTER is the EXTRACT'S ALIAS for a column the ERP calls RUN - and the
    pipeline's own TARGET_COLUMN says so, writing RUN on every run edit
    whichever run type it is, and SETUP_HRS on the rest.

    An earlier version of this function returned "RUN_MASTER" for PCS/HR, on the
    reasoning that TARGET alone was ambiguous. The ambiguity is real and the
    conclusion was backwards: one physical column holds both, a rate under
    PCS/HR and a duration under HRS/LOAD, so what the run type resolves is not
    WHICH column but WHICH KIND OF NUMBER is in it. Naming an alias sent a
    reader looking for a column their ERP does not have.

    So the field comes first and the run type qualifies it, which is the shape
    01_Actions itself uses on the HRS/LOAD rows.

    unit=True spells the qualifier out instead - "pieces per hour", "hours per
    load". That is the fact deciding whether a correction divides or multiplies,
    and it is worth the words where there is room. SETUP_HRS takes no
    parenthetical either way: its name already carries the unit.
    """
    if str(target) == "SETUP_HRS":
        return "SETUP_HRS"
    if str(run_type) == "HRS/LOAD":
        return "RUN (hours per load)" if unit else "RUN (HRS/LOAD)"
    return "RUN (pieces per hour)" if unit else "RUN (PCS/HR)"


def keying_instruction(text):
    """The workbook's HOW_TO_APPLY, with RUN's parenthetical in the app's words.

    01_Actions writes "set RUN (hours per load) to SUGGESTED_VALUE". That
    parenthetical is there to say WHICH RUN - the field name alone is ambiguous,
    because RUN_MASTER is the other one - and every other screen in this tool
    names that value HRS/LOAD verbatim: Inspect's radio, Overview's table rows,
    Additional findings' column. "Hours per load" is the same fact spelled out
    and appears nowhere else, which makes it a synonym a reader has to learn for
    one page.

    DELIBERATELY NOT the same choice as field_name(unit=True), which keeps
    "pieces per hour" and "hours per load". There the parenthetical says what
    KIND of number the field holds - a rate or a duration - and that is the fact
    deciding whether a correction divides or multiplies. Here it only says which
    field, and the ERP's own value does that more consistently.

    RUN_MASTER IS ALSO REWRITTEN, and that one is a correction rather than a
    house-style choice. 01_Actions writes "set RUN_MASTER to SUGGESTED_VALUE" on
    178 of the 238 decisions, and RUN_MASTER is the extract's alias for
    dbo.OPERATION.RUN - see field_name. Left verbatim, the app would print the
    Field column as "RUN (PCS/HR)" and the instruction under it as "set
    RUN_MASTER", naming two different columns for one edit on one screen, one of
    which the ERP does not have.

    The workbook still says RUN_MASTER, so the screen and the sheet differ here
    by design. That is the right way round: the sheet's TARGET_COLUMN - the
    field anything automated would read - already says RUN.
    """
    return (str(text).replace("(hours per load)", "(HRS/LOAD)")
            .replace("RUN_MASTER", "RUN (PCS/HR)"))


def direction_note(target, run_type):
    """The sentence that stops a rate being corrected like a duration."""
    if target == "RUN" and run_type == "PCS/HR":
        # "RUN under PCS/HR", not "RUN_MASTER" - see field_name. One ERP column
        # holds both kinds of number, so the run type is what says which.
        return ("**RUN under PCS/HR is a rate** (pieces per hour). Hours = "
                "quantity ÷ rate, so the correction **divides**: a job running "
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


def hrs(v, dec=0, dash="—", sign=False):
    """1'234 h. With sign=True, a signed delta: +30 h as well as -45 h.

    Only for numbers that are a difference. A total of 30 h is 30 h; a delta of
    30 h is 30 h MORE than the master, and printed bare it reads as the total.
    The sign is taken from the ROUNDED figure, so a delta that displays as 0
    stays unsigned rather than claiming a direction it does not have - and a
    small negative that rounds to nothing prints "0 h", not the "-0 h" that
    plain formatting gives it. Callers can therefore read the direction off the
    returned string and be certain it agrees with what the reader sees."""
    out = num(v, dec, dash)
    if out == dash:
        return dash
    if float(out.replace("'", "")) == 0:
        out = num(0, dec)
    elif sign and float(out.replace("'", "")) > 0:
        out = "+" + out
    return f"{out} h"


def swiss_grid(df, specs):
    """A dataframe styled with Swiss separators that still sorts numerically.

    st.column_config.NumberColumn takes printf specs only, which cannot group
    with an apostrophe, and its "localized" option follows the VIEWER's browser
    locale - en-GB gives commas, it-IT gives dots, so the same table reads
    differently for each person in the room.

    A pandas Styler formats the display while streamlit keeps the underlying
    numeric values for sorting, which is the only route that gets both.

    specs: {column: format spec}, e.g. {"HOURS_DELTA": ",.0f"}.

    AN EMPTY NUMBER CELL READS "—", NOT "None" (2026-10-08). The grid prints
    any missing value as a grey "None" and ignores the Styler's na_rep for it -
    tested on Streamlit 1.63 with float NaN, pandas NA, and na_rep "—" and "".
    A formatted cell is drawn from the Styler's text, so in THIS copy only an
    empty number is stored as +inf and formatted as "—". The column stays
    numeric, so it still sorts as numbers - an empty cell sorts as the largest,
    last in ascending order. A text column would draw "—" too but sort
    "1'234.50" before "53.70". The caller's frame, its downloads and every
    computation keep NaN; app_checks.frame() turns the inf back.
    """
    live = {c: s for c, s in specs.items() if c in df.columns}
    shown = df.copy()
    for c in live:
        col = shown[c]
        # An object column of numbers and blanks - left by a row-by-row fill,
        # as By part's lower table is - counts as a number column too.
        if col.dtype == object:
            num = pd.to_numeric(col, errors="coerce")
            if int(num.notna().sum()) == int(col.notna().sum()):
                col = num
        if pd.api.types.is_float_dtype(col):
            shown[c] = col.fillna(np.inf)
    # AN EMPTY TEXT CELL TOO, in every text column the table carries - By
    # part's Effect on a row with no ratio, Inspect's WO rev on a part with no
    # revision read. A text column draws its own text, so "—" is simply put in.
    # Both kinds of text column: object, and the string dtype pandas now gives
    # a column built from strings (Inspect's WO rev is one).
    for c in shown.columns:
        if c not in live and (shown[c].dtype == object
                              or pd.api.types.is_string_dtype(shown[c])):
            shown[c] = shown[c].where(shown[c].notna(), "—")
    return shown.style.format(
        {c: (lambda v, sp=s: "—" if isinstance(v, float) and v == np.inf
             else fmt(v, sp))
         for c, s in live.items()},
        na_rep="—")


def updater_xlsx(df, editable=()):
    """The master row updater as .xlsx bytes, formulas kept as formulas.

    A string starting with "=" is written as a formula, so VALUE_TO_KEY and
    SQL_UPDATE stay live. The header row is frozen and filtered, the columns
    the reviewer fills in are yellow, and the values carry the app's own
    precision: two decimals, three on the ratio. Imported inside, matching
    chart_key: ui is the lowest layer in this package.
    """
    import io
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="updater")
        ws = xw.sheets["updater"]
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
        yellow = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")
        fmt2 = {"STANDARD_WO", "STANDARD_TODAY", "SUGGESTED", "REVIEW",
                "VALUE_TO_KEY"}
        for i, col in enumerate(df.columns, start=1):
            letter = get_column_letter(i)
            ws[f"{letter}1"].font = Font(bold=True)
            # Formula columns are sized for what they show, not for the
            # formula text, which is what the frame holds.
            width = {"SQL_UPDATE": 60, "VALUE_TO_KEY": 14,
                     "REVIEW_NOTE": 30}.get(col) or max(10, min(40, max(
                         len(col) + 2,
                         int(df[col].astype(str).str.len().max() or 0) + 2)))
            ws.column_dimensions[letter].width = width
            spec = "0.000" if col == "RATIO" else (
                "0.00" if col in fmt2 else None)
            if col in editable or spec:
                for (cell,) in ws.iter_rows(min_row=1 if col in editable else 2,
                                            min_col=i, max_col=i):
                    if col in editable:
                        cell.fill = yellow
                    if spec and cell.row > 1:
                        cell.number_format = spec
    return buf.getvalue()

