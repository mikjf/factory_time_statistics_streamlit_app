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
h0_v2.parquet             the extract, cached
h0_v2.xlsx                the extract as exported
H0_v2_UPDATE_LIST.xlsx    the consolidated decisions
H0_v2_SETUP.xlsx          optional
H0_v2_LOAD.xlsx           optional
H0_v2_<OPERATION>_PARTS.xlsx / _FAMILY.xlsx   one pair per operation
```

**None of those are in this repository, and none ever should be.** They contain
part numbers, customer-identifiable family names, work order numbers and real job
durations. `h0app/paths.py` resolves them relative to the parent folder; set
`H0_ROOT` to point somewhere else.

```bash
python -m pip install -r requirements.txt
```

```bash
streamlit run guided/Overview.py --server.address localhost
```

**Keep `--server.address localhost`.** Streamlit binds every interface by
default and prints a LAN and an external URL on startup. There is no
authentication in this tool, and what is on screen is the confidential data
above. Serving it to other people is a decision to take deliberately, not one to
inherit from a default.

## The idea

The analysis applies **six rules** in order, and a standard only changes if it
passes all of them. So the six rules are the spine of the interface: on
**Inspect** they fill the left rail with the selected unit's own figures, with
the rule that stopped it marked.

That is what makes the *absence* of a recommendation explicable. "Why isn't my
part on the list" is answered on screen — tested and it holds, or never enough
evidence to say — instead of by whoever built the analysis.

| Page | |
|---|---|
| **Overview** | Headline numbers, and where the hours sit by operation and family |
| **Review queue** | Every standard proposed for change, filterable |
| **Inspect** | One recommendation opened up: the six rules with real figures, the work orders behind it, and where each sits against the master |
| **By part** | Everything proposed for one part — and every step examined and left alone, with the reason |
| **Not standards changes** | Hours charged for work with no evidence it happened. Real, but a routing and booking question |
| **How it works** | The method |
| **Dataset** | What the numbers are computed over |

## It writes nothing

No caches on disk, no exports, and deliberately no parquet rebuild — the
analysis has a `load()` that rebuilds its cache when the extract is newer, and
rotates the previous one away in the process. That previous copy is what the
pipeline uses to report a change of scope between extracts, and somebody opening
a dashboard must not be able to destroy it. `h0app/pipeline.py` calls everything
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

This one recomputes, using the analysis's own functions, and compares. Every unit
says whether it reproduces. A mismatch means the workbook was written from a
different extract, or an exclusion rule here has drifted — and either way the
number about to be keyed into the ERP is not the number the current data
supports.

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
| **red ✕** | the rule that stopped this becoming an action |
| **grey –** | also failed, but not the blocker |
| **amber !** | passed everything, but large enough to want a human first |

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
while master hours show the crew-scaled one — `Setup 0.500 h` against a master
of `0.3334` — and that gap is the reason the row was excluded.

## Layout

```
guided/Overview.py              headline numbers, where the hours sit
guided/pages/1_Review_queue.py  every standard proposed for change
guided/pages/2_Inspect.py       one recommendation, with the six-rule rail
guided/pages/3_By_part.py       one part, changed and unchanged steps alike
guided/pages/4_Not_standards.py hours charged for work with no evidence
guided/pages/5_How_it_works.py  the method
guided/pages/6_Dataset.py       what it is all computed over

h0app/paths.py      where the analysis lives; imports nothing from it
h0app/pipeline.py   imports the analysis scripts; re-exports their thresholds
h0app/freshness.py  the staleness guard
h0app/data.py       cached workbook readers, keyed on file mtime
h0app/evidence.py   per-work-order evidence for each of the four routes
h0app/charts.py     the distribution chart and the rankings
h0app/text.py       the six rules, and the shared prose
h0app/ui.py         the visual language: colours, the rail, the funnel
```

Thresholds (`MIN_WO`, `MAD_K`, `TOKEN_HOURS`, the materiality gates) are
**imported from the analysis scripts, never re-declared here**. If one changes,
this tool moves with it rather than describing a rule that stopped applying.
