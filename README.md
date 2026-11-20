# Factory time statistics: the Streamlit review app

#### -- Project Status: [Completed]

## Objective

A Streamlit app over a statistical review of manufacturing time standards. The analysis checks
the routing standards held in the ERP (how long setup and run should take, per part and
operation) against the hours actually booked on labour tickets, and proposes the standards that
should change. This app lets project management, finance and supply chain read those proposals,
open up the work orders behind any one of them, and see why a standard was changed or left alone.

**The analysis itself lives in a separate repository:**
<https://github.com/mikjf/factory_time_statistics>

That is where the SQL extract and the Python that produces the workbooks live.
This repository is only the viewer. It computes no standard of its own — it
reads what the analysis wrote and, for one unit at a time, rebuilds the evidence
from the extract so the two can be compared.

### What this project demonstrates

- **A multipage Streamlit app on top of an existing pipeline**, reusing its functions and
  thresholds instead of re-implementing them, so the two cannot drift apart
- **Explaining a decision, not just showing it:** the six rules a standard must pass are the
  spine of the interface, so "why isn't my part on the list" is answered on screen
- **A viewer that checks its own numbers:** every figure is recomputed from the extract and
  compared with the workbook that produced it; a headless check script renders every page after
  each new extract
- **Refusing stale results:** file ordering is checked before anything renders
- **Read-only by design:** no caches, no exports to disk, nothing written to the ERP; the review
  file generates the SQL `UPDATE` statements as Excel formulas for a person to check and run
- **Accessible charts:** Altair distributions where every colour is paired with a symbol

### Tech stack

- Python 3.12
- Streamlit and Altair
- pandas, NumPy, SciPy
- pyarrow, openpyxl

### Data

The app runs on confidential production data (ERP routings and labour tickets). None of it is in
this repository, and the repository holds no screenshots of it: the data stays inside the
company. Running the app needs the analysis repository and an ERP extract, described below.

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

This tool never refreshes anything itself. Every file above is produced by the
analysis repository, and a new ERP export goes in **there**, not here:

| | |
|---|---|
| put the export in the analysis folder as **`fts_new.xlsx`** | and the query beside it as **`fts_new.sql`** if the query changed |
| `python new_extract.py --dry-run` | validates the incoming workbook and changes nothing |
| `python new_extract.py` | archives the outgoing generation, promotes the new one, runs the whole pipeline |

Why the `_new` names, what to do when the export was already renamed, and the full
procedure are in [DESIGN.md](DESIGN.md#refreshing-what-it-reads) and in the analysis
repository's README under **Running it**.

## The pages

The analysis applies **six rules** in order, and a standard only changes if it
passes them all. So the six rules are the spine of the interface: on
**Inspect**, "How this was decided" shows all six with the selected unit's own
figures, directly under the verdict and above the chart, with the rule that
stopped it marked `(STOPPED)`.

| Page | |
|---|---|
| **Overview** | Headline numbers, how much of them today's master already carries, and where the hours sit by operation and family |
| **Review queue** | Every standard proposed for change, filterable, with Std WO, Std today and whether it is already done; the master row updater file |
| **Inspect** | One recommendation opened up: how it was decided, the work orders behind it, where each sits against the master, and today's master part by part |
| **By part** | Everything proposed for one part, with today's master and status per row — and every step examined and left alone, with the reason |
| **Additional findings** | Hours charged for work with no evidence it happened. Real, but a routing and booking question |
| **How to read it** | How to read a recommendation, worked through one real unit |
| **Methodology** | The method, and what the numbers are computed over |

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

## Design notes

How the app keeps itself honest and why it looks the way it does - it writes nothing, it
refuses stale results, it checks its own numbers, the vocabulary and colours, the chart
tooltips, the two scales and the master row updater file - is in [DESIGN.md](DESIGN.md).
