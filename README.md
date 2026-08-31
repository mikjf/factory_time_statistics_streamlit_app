# Master time review — the tool

A browser view over the master-time analysis, so project management, finance and
supply chain can read the proposed standard changes, open up the work orders
behind any one of them, and see where those work orders actually sit against the
master.

**The analysis itself lives in a separate repository:**
<https://github.com/mikjf/factory_time_statistics>

That is where the SQL extract and the Python that produces the workbooks live.
This repository is only the viewer. It computes no standard of its own — it
reads what the analysis wrote and, for one unit at a time, rebuilds the evidence
from the extract so the two can be compared.

## What it needs to run

The analysis outputs, sitting in a folder next to this one:

```
fts.parquet             the extract, cached
fts.xlsx                the extract as exported
FTS_UPDATE_LIST.xlsx    the consolidated decisions
FTS_SETUP.xlsx          optional
FTS_LOAD.xlsx           optional
FTS_<OPERATION>_PARTS.xlsx / _FAMILY.xlsx   one pair per operation
```

**None of those are in this repository, and none ever should be.** They contain
part numbers, customer-identifiable family names, work order numbers and real job
durations. `ftsapp/paths.py` resolves them relative to the parent folder; set
`FTS_ROOT` to point somewhere else.

```bash
python -m pip install -r requirements.txt
```

```bash
streamlit run Overview.py --server.address localhost
```

**Keep `--server.address localhost`.** Streamlit binds every interface by
default and prints a LAN and an external URL on startup. There is no
authentication in this tool, and what is on screen is the confidential data
above. Serving it to other people is a decision to take deliberately, not one to
inherit from a default.

## The idea

The analysis applies **six rules** in order, and a standard only changes if it
passes all of them. So the six rules are the spine of the interface: on
**Inspect**, "How this was decided" shows all six with the selected unit's own
figures, directly under the verdict and above the chart, with the rule that
stopped it marked `(STOPPED)`.

That is what makes the *absence* of a recommendation explicable. "Why isn't my
part on the list" is answered on screen — tested and it holds, or never enough
evidence to say — instead of by whoever built the analysis.

| Page | |
|---|---|
| **Overview** | Headline numbers, and where the hours sit by operation and family |
| **Review queue** | Every standard proposed for change, filterable |
| **Inspect** | One recommendation opened up: how it was decided, the work orders behind it, and where each sits against the master |
| **By part** | Everything proposed for one part — and every step examined and left alone, with the reason |
| **Additional findings** | Hours charged for work with no evidence it happened. Real, but a routing and booking question |
| **How to read it** | How to read a recommendation, worked through one real unit |
| **Methodology** | The method, and what the numbers are computed over |

## It writes nothing

No caches on disk, no exports, and deliberately no parquet rebuild — the
analysis has a `load()` that rebuilds its cache when the extract is newer, and
rotates the previous one away in the process. That previous copy is what the
pipeline uses to report a change of scope between extracts, and somebody opening
a dashboard must not be able to destroy it. `ftsapp/pipeline.py` calls everything
in the analysis scripts *except* that function.

`sys.dont_write_bytecode` is set too, so importing them leaves no `.pyc` beside
them. Downloads go to the browser.

## It refuses stale results

A stale workbook looks completely normal. So before anything renders, the file
ordering is checked:

| | |
|---|---|
| extract newer than the cached parquet | **stop** — the analysis has not caught up |
| update list older than the parquet | **stop** — the deliverable predates its data |
| a per-operation workbook older than the extract | warning on that operation |
| setup / HRS-LOAD workbooks missing | those sections hidden |

Every file's timestamp is shown on the Overview whether or not the check passed.

## It checks its own numbers

The run analysis persists per-work-order rows only for the units it acted on, so
the evidence behind everything else has to be rebuilt from the extract. That
turns out to be the better answer: a viewer that read the numbers back out of the
workbook could only ever agree with it.

This one recomputes, using the analysis's own functions, and compares — on every
unit, every time. It reports by exception: a unit that reproduces says nothing,
and a unit that does not gets an error telling the reader not to key the number
in. A mismatch means the workbook was written from a different extract, or an
exclusion rule here has drifted, and either way the number about to go into the
ERP is not the number the current data supports.

The comparison is always against the workbook that **computed** the figure, never
the consolidated update list, whose ratios are rounded to three decimals for
reading.

## Vocabulary and colour

Two words, everywhere, never paraphrased: **master** for the standard the ERP
holds, **actual** for what was booked. They are the names the workbook and the
query use, so any figure on screen can be traced back without translation.

Colour carries meaning and is never decoration:

| | |
|---|---|
| **green ✓** | the rule was satisfied |
| **red ✕** | the rule was not |
| **amber !** | passed everything, but large enough to want a human first |

Where more than one rule fails, all of them are red and the **first** is marked
`(STOPPED)`. That is not a display nicety: `recommend()` returns at the
first failing condition, so the reason written into the update list is that rule
and no other, and the page has to be able to point at it. Colour answers the
question asked once per rule — did it pass — and the label answers the one asked
once per unit.

Every colour is paired with a symbol, because roughly one man in twelve cannot
separate the green from the red.

## The dot you hover

Each dot on a distribution chart is one work order, and its tooltip is meant to
be readable detached from the page that drew it — it names the part, the work
order, the date and the routing step before any arithmetic.

It also shows the standard **in the unit the routing holds it in**, which is the
unit somebody has to go and change:

| route | standard | achieved |
|---|---|---|
| Run PCS/HR | `Run 10.00 PCS/HR` | `8.26 PCS/HR` |
| Run HRS/LOAD | `Run 5.00 HRS/LOAD` | *— see below* |
| Setup | `Setup 1.00 h` | *— see below* |

Every value carries its unit beside the number — `master` / `6.00 h`, not
`master h` / `6.00` — and every value is held to two decimals, the precision the
ERP stores hours at, whole numbers included.

The ratio keeps three decimals, alone: it is computed rather than stored, and
rounding a genuinely-off 1.004 to `1.00` would misread the one value the chart
is drawn against.

The achieved rate appears for PCS/HR only. Every tested HRS/LOAD work order is
single-load by construction, so hours per load and hours worked are the same
number; the load count is shown instead, which is what explains where an
excluded multi-load dot sits. Setup standards are already durations, so achieved
setup hours are the actual hours already on the line above.

A field that is empty for every dot on a chart is dropped rather than shown as a
row of dashes, so setup charts carry no quantity and no achieved rate.

On a **crew-mismatch** setup row the standard line shows the routing's own value
while master hours show the crew-scaled one — `Setup 0.50 h` against a master of
`0.33 h` — and that gap is the reason the row was excluded.

## Two scales, one table

The chart's axis is a ratio. The thing somebody keys into the ERP is a rate or a
duration. Inspect and "How to read it" both carry the mapping between them:

| | ratio | as the routing holds it |
|---|---|---|
| **standard** | 1.000 | Run 10.00 PCS/HR |
| **measured** | 1.181 (+18.1%) | Run 8.47 PCS/HR (−15.3%) |
| **95% band** | 1.067 – 1.244 | excludes 1.000 |
| **to key** | | 8.47 — edit `RUN_MASTER` |
| **judged at** | | one part, or family as a whole |

Read down either column and the correction directions are simply there: the
ratio rises 18.1%, the rate falls 15.3%, one event. A duration moves the same
way as its ratio, which is the whole distinction, visible without a sentence
explaining it.

**Measured is derived, not read.** Every workbook writes its `SUGGESTED` column
only for the units it recommends changing — the setup rollup and both load
sheets leave it empty on *all* of their no-change rows — so it is computed as
`current ÷ ratio` for a rate and `current × ratio` for a duration. Where the
pipeline does write a value, the derivation reproduces it, so no unit shows one
number as measured and another as the value to key.

The band row states whether it **excludes 1.000**, which is rule 4 and the
band's only job. Where the line falls relative to the band is deliberately not
reported: the two estimators can disagree, and nothing depends on it.

## Layout

```
Overview.py               headline numbers, where the hours sit
pages/1_Review_queue.py   every standard proposed for change
pages/2_Inspect.py        one recommendation: how it was decided,
                                 then the evidence
pages/3_By_part.py        one part, changed and unchanged steps alike
pages/4_Additional_findings.py  hours charged for work with no evidence
pages/5_How_to_read_it.py how to read a recommendation
pages/6_Methodology.py    the method, and what it is computed over

ftsapp/paths.py      where the analysis lives; imports nothing from it
ftsapp/pipeline.py   imports the analysis scripts; re-exports their thresholds
ftsapp/freshness.py  the staleness guard
ftsapp/data.py       cached workbook readers, keyed on file mtime
ftsapp/evidence.py   per-work-order evidence for each of the four routes
ftsapp/charts.py     the distribution chart and the rankings
ftsapp/text.py       the six rules, and the shared prose
ftsapp/ui.py         the visual language: colours, the rule cards, the funnel
```

Thresholds (`MIN_WO`, `MAD_K`, `TOKEN_HOURS`, the materiality gates) are
**imported from the analysis scripts, never re-declared here**. If one changes,
this tool moves with it rather than describing a rule that stopped applying.
