"""Where the analysis lives.

Every path is resolved from this file's own location, so the app behaves the
same whatever directory streamlit was launched from. Relative paths would work
by accident when run from the project root and break silently anywhere else -
and "silently" is the failure mode this whole project is built to avoid.

THE ROOT IS FOUND IN THIS ORDER, and the first match wins:

  1. FTS_ROOT, if it is set. Taken as given and never second-guessed: a wrong
     FTS_ROOT has to fail on THAT folder, loudly, not fall through quietly to
     some other folder that happens to hold a pipeline. It is the setting a
     container will use. It also lets the freshness guard be tested against a
     scratch copy of the project - proving the guard fires by making the real
     folder stale would put it into exactly the state the guard refuses.
  2. The folder above the app, if the pipeline is there: the original layout,
     with the app nested inside the project as streamlit_app/.
  3. factory_time_statistics beside the app: the two repositories cloned side
     by side, which is how they are published. Until 2026-09-11 this layout
     resolved to the folder ABOVE both clones and died importing fts_analysis.

"The pipeline is there" means its CODE is there - MARKER - not its data. A
clone that has not been run yet is still found, so the freshness guard can say
"no extract here" about the right folder, instead of the app failing to import
from the wrong one.

This module deliberately imports nothing from the analysis scripts. It is the
one piece that has to work before anything else does.
"""

import datetime as _dt
import os
import pathlib

APP_DIR = pathlib.Path(__file__).resolve().parent.parent
PIPELINE_REPO = "factory_time_statistics"
MARKER = "fts_analysis.py"          # the first module pipeline.py imports


def _find_root():
    """(root, how it was found). The order is in the module docstring."""
    explicit = os.environ.get("FTS_ROOT")
    if explicit:
        return pathlib.Path(explicit).resolve(), "FTS_ROOT"
    for where, how in (
            (APP_DIR.parent, "the folder above the app"),
            (APP_DIR.parent / PIPELINE_REPO, f"{PIPELINE_REPO} beside the app")):
        if (where / MARKER).exists():
            return where.resolve(), how
    # Nothing found: name the layout the repositories are published in, so the
    # error points at the folder that is actually missing.
    return ((APP_DIR.parent / PIPELINE_REPO).resolve(),
            f"nowhere - expected {PIPELINE_REPO} beside the app, or FTS_ROOT")


ROOT, ROOT_FOUND_BY = _find_root()

EXTRACT = ROOT / "fts.xlsx"          # the export out of the ERP
CACHE = ROOT / "fts.parquet"         # what every script actually reads
# The per-operation workbooks moved out of the root on 2026-08-28, and the
# folder was renamed from `outputs` on 2026-09-10 to say which run type it
# holds - see the note in fts_analysis.py. The three deliverables did not
# move, and no other run type is in there.
OUTPUTS = ROOT / "outputs_run_pcs_hr"
UPDATE_LIST = ROOT / "FTS_UPDATE_LIST.xlsx"
SETUP = ROOT / "FTS_SETUP.xlsx"         # optional input, same as the pipeline
LOAD = ROOT / "FTS_RUN_HRS_LOAD.xlsx"   # optional input, same as the pipeline


def mtime(path):
    """Last-modified time, or None if the file is not there."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    return _dt.datetime.fromtimestamp(p.stat().st_mtime)


def stamp(path):
    """Modification time as a string, for display."""
    t = mtime(path)
    return t.strftime("%Y-%m-%d %H:%M") if t else "missing"


def cache_key(*paths):
    """A cache key that changes when any of these files does.

    Passed to every cached loader. Keying on the path alone would leave the app
    showing a workbook that had been rewritten underneath it, which is the same
    stale-artefact failure the parquet mtime check in fts_analysis.load()
    exists to prevent - just relocated into the viewer.
    """
    return tuple((str(p), (mtime(p) or _dt.datetime.min).timestamp())
                 for p in paths)
