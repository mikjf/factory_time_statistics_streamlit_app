"""Where the analysis lives.

Every path is resolved from this file's own location, so the app behaves the
same whatever directory streamlit was launched from. Relative paths would work
by accident when run from the project root and break silently anywhere else -
and "silently" is the failure mode this whole project is built to avoid.

H0_ROOT overrides the root. That exists so the freshness guard can be tested
against a scratch copy of the project: proving the guard fires by making the
real folder stale would put it into exactly the state the guard refuses.

This module deliberately imports nothing from the analysis scripts. It is the
one piece that has to work before anything else does.
"""

import datetime as _dt
import os
import pathlib

APP_DIR = pathlib.Path(__file__).resolve().parent.parent
ROOT = pathlib.Path(os.environ.get("H0_ROOT") or APP_DIR.parent).resolve()

EXTRACT = ROOT / "h0_v2.xlsx"          # the export out of the ERP
CACHE = ROOT / "h0_v2.parquet"         # what every script actually reads
# The per-operation workbooks moved out of the root on 2026-08-28 - see
# the note in h0_v2_analysis.py. The three deliverables did not.
OUTPUTS = ROOT / "outputs"
UPDATE_LIST = ROOT / "H0_v2_UPDATE_LIST.xlsx"
SETUP = ROOT / "H0_v2_SETUP.xlsx"      # optional input, same as in the pipeline
LOAD = ROOT / "H0_v2_LOAD.xlsx"        # optional input, same as in the pipeline


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
    stale-artefact failure the parquet mtime check in h0_v2_analysis.load()
    exists to prevent - just relocated into the viewer.
    """
    return tuple((str(p), (mtime(p) or _dt.datetime.min).timestamp())
                 for p in paths)
