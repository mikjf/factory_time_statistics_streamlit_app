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

The pipeline repository, `factory_time_statistics`, cloned beside this one and
run at least once. The app imports its code, and the run writes everything the
app reads:

```
factory_time_statistics/    the pipeline, and after a run:
  fts.parquet               the extract, cached
  fts.xlsx                  the extract as exported
  FTS_UPDATE_LIST.xlsx      the consolidated decisions
  FTS_SETUP.xlsx            optional
  FTS_RUN_HRS_LOAD.xlsx     optional
  outputs_run_pcs_hr/       one FTS_<OPERATION>_PARTS.xlsx / _FAMILY.xlsx
                            pair per operation, PCS/HR run only
factory_time_statistics_streamlit_app/    this repository
```

**None of those data files are in either repository, and none ever should be.**
They contain part numbers, customer-identifiable family names, work order
numbers and real job durations. `ftsapp/paths.py` finds the pipeline on its own -
beside this repository, or in the folder above it - and `FTS_ROOT` overrides
both, which is how a container or any other layout points it somewhere else.

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

### Refreshing what it reads

This tool never refreshes anything itself — see
[It writes nothing](#it-writes-nothing). Every file above is produced by the
analysis repository, and a new ERP export goes in **there**, not here:

| | |
|---|---|
| put the export in the analysis folder as **`fts_new.xlsx`** | and the query beside it as **`fts_new.sql`** if the query changed |
| `python new_extract.py --dry-run` | validates the incoming workbook and changes nothing |
| `python new_extract.py` | archives the outgoing generation, promotes the new one, runs the whole pipeline |

The `_new` names matter. `new_extract.py` looks for them, and the point of the
two-name dance is that the incoming file is validated and the outgoing
generation archived **before** anything is overwritten — so a bad export is
caught while it is still just a file with a funny name.

If somebody has already renamed the export to `fts.xlsx` by hand, that route is
closed: `new_extract.py` will not find a `_new` file, and `python run_all.py` is
what re-runs the pipeline over whatever is in place. It refuses until the
outgoing generation has been banked with `python archive_current.py`, which is a
guard rather than an obstacle — one generation was lost that way.

The full procedure, including what happens when the columns change, is in the
analysis repository's README under **Running it**. It is deliberately not
repeated here: two copies of a refresh procedure is how they stop agreeing.

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
| **Overview** | Headline numbers, how much of them today's master already carries, and where the hours sit by operation and family |
| **Review queue** | Every standard proposed for change, filterable, with Std WO, Std today and whether it is already done; the master row updater file |
| **Inspect** | One recommendation opened up: how it was decided, the work orders behind it, where each sits against the master, and today's master part by part |
| **By part** | Everything proposed for one part, with today's master and status per row — and every step examined and left alone, with the reason |
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

**After every new extract, run `python app_checks.py`** from this folder. It
renders every page headless and checks what the screen and the downloads say
against the update list: Std today and Status per decision, the two copies of
today's master on every action, Status on every part row, the whole-family
values on Inspect and By part, and every statement in the master row updater.
One line per check, exit 0 when all pass. It is the app's counterpart to the
pipeline's `fts_checks.py`, and the pipeline's `run_all.py` runs both for you
when this folder sits beside it.

## Vocabulary and colour

Two words, everywhere, never paraphrased: **master** for the standard the ERP
holds, **actual** for what was booked. They are the names the workbook and the
query use, so any figure on screen can be traced back without translation.

The master comes in two copies, and the app names them apart:

| | |
|---|---|
| **Std WO** | the work orders' own copy of the routing — what the jobs ran with, and what the six rules test against |
| **Std today** | the master as it stands in the latest extract, on each part's current revision |

On a **whole family**, Std WO, Std today and Suggested show the one value every
part holds, and stay empty where the parts differ. There is then no single
number to key, and By part, the Review queue's row card and the master row
updater show each part's own. Inspect's Standard WO tile shows the number of
values instead, Change it to reads *per part*, and Measured shows the ratio
itself (× or ÷). The decision table below them keeps the arithmetic on the
pool's own figure — an hours-weighted rate on PCS/HR, the average per work
order on HRS/LOAD, the median across the setups on setup — and says which.

**Std WO comes from a timed job.** It is the value on the latest work order
with time booked on it; a token booking (closed at 0.02 h or less) does not
set it, in the app as in the pipeline.

**Already done** means today's master has moved and now sits within the
materiality threshold (rule 5) of the value proposed, so there is nothing left
to key. An action that is already done **stays an action** — on the list and in
every count — and is marked as done. Methodology explains all three.

Colour carries meaning and is never decoration:

| | |
|---|---|
| **green ✓** | the rule was satisfied |
| **red ✕** | the rule was not |
| **amber !** | passed everything, but large enough to want a human first — or far from what today's master holds |
| **blue** | information, not a rule outcome: a standard left alone, or a fact about the ERP — already done, partly done, the master moved |

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

On a setup row the standard line and master hours both show the work order's
own setup value (`SETUP_HRS_MASTER`, since 9 Oct 2026), whoever booked it. A
**crew-mismatch** row is excluded because the people who booked were not the
crew the routing plans for, not because of a gap between the two figures. A
setup run under a value the part has since replaced shows as *ran under a
standard since replaced*, as on the run analyses.

## Two scales, one table

The chart's axis is a ratio. The thing somebody keys into the ERP is a rate or a
duration. Inspect and "How to read it" both carry the mapping between them:

| | ratio | as the jobs ran it |
|---|---|---|
| **standard** | 1.000 | Run 10.00 PCS/HR |
| **measured** | 1.181 (+18.1%) | Run 8.47 PCS/HR (−15.3%) |
| **95% band** | 1.067 – 1.244 | excludes 1.000 |
| **to key** | | 8.47 — edit `RUN_MASTER` |
| **master today** | | Run 10.00 PCS/HR — unchanged since the jobs ran |
| **judged at** | | one part, or family as a whole |

**"As the jobs ran it", because the standard row is the work orders' own copy
of the routing** — what the six rules test against. The master can have moved
since: **master today** is the routing line on the part's current revision as
it stands in the latest extract, and says whether it moved. On an action it is
read from the update list, which also says whether the change is already done;
on any other unit it is rebuilt from the extract with the same definitions, and
on an action the page checks the two copies agree.

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

## The master row updater

The Review queue's second download is the file somebody keys from: **one row per
routing row** rather than per decision, so a family decision covering many parts
becomes one row for each of them. It follows the page's filters. Columns, in
order:

| | |
|---|---|
| `MASTER_OPS_ROWID` | the routing row the value is keyed against |
| `FAMILY`, `PART_ID`, `PART_DESCRIPTION`, `PART_TYPE` | which part |
| `OPERATION`, `STEP`, `ANALYSIS`, `APPLIES_TO` | which step, which analysis, part or whole family |
| `STANDARD_WO` | what the work orders ran with |
| `STANDARD_TODAY` | what the routing row holds in today's master |
| `SUGGESTED` | the value to key |
| `RATIO`, `EFFECT` | the measurement, and which way it moves the time allowed |
| `TODAY_STATUS` | *already done* or *to key* |
| `HOW_TO_APPLY` | the workbook's own instruction |
| `SQL_UPDATE` | a ready-made `UPDATE` statement |

`SQL_UPDATE` is a **spreadsheet formula**, not finished text: it reads the
`SUGGESTED` and `MASTER_OPS_ROWID` cells of its own row, so correcting a value
in the sheet corrects the statement with it. Its column letters are derived
from the column order, so a reordered file still points at the right cells. It
is **left empty on a row already done**, so there is nothing to run by accident;
the row stays in the file. Nothing here runs anything — it produces the SQL and
leaves running it to a person who has read it.

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
app_checks.py             run after every extract: pages render, figures match

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
