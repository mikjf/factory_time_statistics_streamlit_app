"""Check the app against the pipeline's outputs. Run after every new extract.

    python app_checks.py            (from this folder, in the fts env)

The pipeline has fts_checks.py for the figures its prose quotes. This is the
app's equivalent, and it checks what the screen and the downloads SAY rather
than how they look: every page is rendered headless through Streamlit's own
test harness, and the figures that matter for keying are compared with the
update list they came from.

    1. every page renders without an error - Overview, Review queue in three
       states, Inspect on every action and a sample of held units, By part on
       a sample of parts, Additional findings, How to read it, Methodology
    2. Review queue: Std today and Status equal the update list, decision by
       decision, and "Flagged for manual review" counts both reasons - the
       ratio band and the check against today's master
    3. Inspect: the two copies of today's master - update list and extract -
       agree on every action (the red cross-check never fires), on every
       part row of the "part by part" table Status follows from the row itself,
       and on every whole-family action the Standard WO tile is its parts' one
       value or their count. By part: on the lower table's whole-family rows
       that are decisions, Std WO, Std today and Suggested are the parts' one
       value or blank
    4. the master row updater: as many rows as the "Operations rows to edit"
       tile, every statement pointing at its own row's SUGGESTED and
       MASTER_OPS_ROWID, empty on exactly the rows already done
    5. Overview: the "already done" pills equal the update list's counts

Prints one line per check and exits 0 when all pass, 1 otherwise. Takes a few
minutes: Inspect is rendered once per unit.

NO PART NUMBERS IN THIS FILE. Every unit and part it looks at is chosen from
the workbooks at run time - the commit guard refuses identifiers in code, and a
check pinned to one part would stop checking anything the day it left scope.
"""

import contextlib
import io
import logging
import pathlib
import random
import sys
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

APP = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(APP))

import pandas as pd  # noqa: E402
import streamlit  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from ftsapp import paths, pipeline  # noqa: E402

# ---- the harness ------------------------------------------------------------
# st.page_link raises inside AppTest and aborts the script; a no-op here lets
# every page run to the end. st.download_button is replaced by a recorder, so
# the files a page offers can be checked like anything else it shows.
DOWNLOADS = []
streamlit.page_link = lambda *a, **k: None


def _record(label, data, *a, **k):
    # Text downloads are decoded; a binary one (the .xlsx updater) is kept as
    # bytes.
    if isinstance(data, bytes) and not k.get("file_name", "").endswith(".xlsx"):
        data = data.decode("utf-8")
    DOWNLOADS.append((k.get("file_name"), data))
    return False


streamlit.download_button = _record

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" - {detail}" if detail else ""),
          flush=True)


def render(page, unit=None, setup=None):
    """Run one page; return the AppTest after it finished, downloads collected.

    THE PAGE'S OWN PRINTING IS SWALLOWED. The analysis functions a page calls
    print as they go - "token bookings dropped: ..." on every rebuild - and
    run from run_all those lines buried the PASS and FAIL lines between them.
    What a page SHOWS is still checked in full; only its console chatter goes.
    """
    DOWNLOADS.clear()
    at = AppTest.from_file(str(APP / page), default_timeout=300)
    if unit is not None:
        at.session_state["unit"] = unit
    with contextlib.redirect_stdout(io.StringIO()):
        at.run()
        if setup is not None and not at.exception:
            setup(at)
            at.run()
    return at


def frame(df_element):
    """The table's data. ui.swiss_grid stores an empty number cell as +inf in
    the copy it shows, so the grid draws "—" rather than "None"; it is turned
    back into the empty value here, so a check compares what the page means."""
    v = df_element.value
    v = v.data if hasattr(v, "data") else v
    return v.replace(float("inf"), float("nan"))


def errors(at):
    return [e.message for e in at.exception]


# ---- the reference: the update list, read directly --------------------------
UL = paths.UPDATE_LIST
acts = pd.read_excel(UL, "01_Actions")
EXEC = {("RUN", "PCS/HR"): ("02_RunUpdateList", "RM_RECOMMENDED"),
        ("SETUP_HRS", "-"): ("03_SetupUpdateList", "SETUP_HRS_RECOMMENDED"),
        ("RUN", "HRS/LOAD"): ("04_LoadUpdateList", "RUN_RECOMMENDED")}
ex = pd.concat([pd.read_excel(UL, s).assign(TARGET=t, RUN_TYPE=r,
                                             RECOMMENDED=lambda d, c=c: d[c])
                for (t, r), (s, c) in EXEC.items()], ignore_index=True)
for c in ("FAMILY", "PART_TYPE", "OPERATION", "PART_ID"):
    acts[c] = acts[c].astype(str).str.strip()
    ex[c] = ex[c].astype(str).str.strip()


def one(s):
    """The value every part holds, or NaN - the whole-family rule, written out
    again here rather than imported, so the check does not test the app's code
    against itself."""
    s = pd.to_numeric(s, errors="coerce")
    return (float(s.iloc[0]) if len(s) and s.notna().all()
            and s.round(4).nunique() == 1 else float("nan"))


def same_value(a, b):
    a, b = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    return (pd.isna(a) and pd.isna(b)) or (
        not pd.isna(a) and not pd.isna(b) and abs(a - b) <= 1e-4)


def family_rows(family, part_type, operation, seq, target, run_type):
    """The update list's rows for one whole-family decision."""
    return ex[(ex.FAMILY == family) & (ex.PART_TYPE == part_type)
              & (ex.OPERATION == operation) & (ex.SEQ == seq)
              & (ex.TARGET == target) & (ex.RUN_TYPE == run_type)
              & (ex.ROUTE.astype(str).str.upper() == "FAMILY")]


def main():
    print(f"app_checks - update list of {paths.stamp(UL)}, "
          f"{len(acts)} decisions, {len(ex)} routing rows\n", flush=True)
    if "STANDARD_TODAY" not in ex.columns:
        print("  the update list predates STANDARD_TODAY (fts_update_list.py "
              "before 2026-09-28) - nothing to check against. Re-run the "
              "pipeline.")
        sys.exit(1)

    # ---- Overview -------------------------------------------------------
    print("Overview", flush=True)
    at = render("Overview.py")
    check("renders", not at.exception, "; ".join(errors(at)))
    if not at.exception:
        m = {x.label: x for x in at.metric}
        n_done = int((acts.ACTION_STATUS == "already done").sum())
        r_done = int(ex.TODAY_STATUS.astype(str).str.startswith("already done").sum())
        want0 = f"{n_done:,} already done".replace(",", "'") if n_done else ""
        want2 = f"{r_done:,} already done".replace(",", "'") if r_done else ""
        check("'already done' pills equal the update list",
              (m["Standards to review"].delta or "") == want0
              and (m["Operations rows to edit"].delta or "") == want2,
              f"{m['Standards to review'].delta!r} / "
              f"{m['Operations rows to edit'].delta!r}")

    # ---- Review queue ---------------------------------------------------
    print("Review queue", flush=True)
    at = render("pages/1_Review_queue.py")
    check("renders", not at.exception, "; ".join(errors(at)))
    if not at.exception:
        t = frame(at.dataframe[0])
        # The reference per decision, straight from the execution sheets.
        e = ex.assign(_PK=ex.PART_ID.where(ex.ROUTE == "PART", ""),
                      SEQUENCE=ex.SEQ, LEVEL=ex.ROUTE)
        k = ["FAMILY", "PART_TYPE", "OPERATION", "SEQUENCE", "TARGET",
             "RUN_TYPE", "LEVEL", "_PK"]
        ref = (e.groupby(k).STANDARD_TODAY
               .agg(lambda s: s.iloc[0] if s.notna().all()
                    and s.round(4).nunique() == 1 else float("nan"))
               .rename("REF").reset_index())
        a = acts.assign(_PK=acts.PART_ID.where(acts.LEVEL == "PART", ""))
        a = a.merge(ref, on=k, how="left")
        got = pd.to_numeric(t.STANDARD_TODAY, errors="coerce").values
        same = ((pd.Series(got).round(4) == a.REF.round(4).values)
                | (pd.Series(got).isna() & a.REF.isna().values))
        check("Std today equals the update list, decision by decision",
              len(t) == len(a) and bool(same.all()),
              f"{int((~same).sum())} of {len(a)} differ")
        st_short = t.STATUS.astype(str)
        st_ref = acts.ACTION_STATUS.astype(str)
        agree = ((st_short == "already done") == (st_ref == "already done")) \
            & (st_short.str.startswith("partly") == st_ref.str.startswith("partly"))
        check("Status equals ACTION_STATUS", bool(agree.all()),
              f"{int((~agree).sum())} differ")
        # FLAGGED FOR MANUAL REVIEW counts a decision once for either reason
        # (2026-10-07): its ratio outside the band, or any of its routing rows
        # flagged against today's master. The pill counts the second.
        ft = (e.assign(_F=e.REVIEW_FLAG_TODAY.notna()
                       & (e.REVIEW_FLAG_TODAY.astype(str).str.strip() != ""))
              .groupby(k)["_F"].any().rename("FT").reset_index())
        a2 = a.merge(ft, on=k, how="left")
        on_today = a2.FT.fillna(False).astype(bool)
        band = (a2.RATIO < pipeline.REVIEW_LO) | (a2.RATIO > pipeline.REVIEW_HI)
        want_n, want_t = int((band | on_today).sum()), int(on_today.sum())
        flag_tile = next(x for x in at.metric
                         if x.label == "Flagged for manual review")
        check("Flagged for manual review counts both reasons",
              flag_tile.value == f"{want_n:,}".replace(",", "'")
              and (flag_tile.delta or "") == (f"{want_t} against today"
                                              if want_t else ""),
              f"tile {flag_tile.value} / {flag_tile.delta!r}, update list "
              f"{want_n} ({want_t} against today)")

        # The master row updater.
        up = [(n, d) for n, d in DOWNLOADS if n and "updater" in n]
        if not up:
            check("master row updater offered", False, "no download recorded")
        else:
            # Read as written, formulas as their text: openpyxl without
            # data_only returns a formula cell's formula, not a cached value.
            from openpyxl import load_workbook
            name, wb = up[-1][0], load_workbook(io.BytesIO(up[-1][1]))
            ws = wb.active
            # The extract it was made from, in its name and on its INFO sheet,
            # with the updater still the sheet it opens on.
            taken = paths.mtime(paths.EXTRACT)
            said = ({r[0]: r[1] for r in wb["INFO"].iter_rows(
                min_row=2, values_only=True)} if "INFO" in wb.sheetnames
                else {})
            check("updater carries the extract's date in its name and INFO",
                  taken is not None and ws.title == "updater"
                  and name.endswith(f"_{taken:%Y-%m-%d}.xlsx")
                  and said.get("extract taken (fts.xlsx)")
                  == f"{taken:%Y-%m-%d %H:%M}",
                  f"{name}, opens on {ws.title!r}, INFO says "
                  f"{said.get('extract taken (fts.xlsx)')!r}")
            rows = list(ws.iter_rows(values_only=True))
            u = pd.DataFrame([["" if v is None else str(v) for v in r]
                              for r in rows[1:]], columns=rows[0])
            tile = next(x for x in at.metric
                        if x.label == "Operations rows to edit").value
            check("updater rows equal the 'Operations rows to edit' tile",
                  f"{len(u):,}".replace(",", "'") == tile,
                  f"{len(u)} rows, tile {tile}")
            L = {c: chr(65 + i) for i, c in enumerate(u.columns)}
            done = u.TODAY_STATUS == "already done"
            # VALUE_TO_KEY reads its own row's REVIEW, SUGGESTED and status,
            # and keys nothing on a row already done unless REVIEW says so;
            # SQL_UPDATE reads its own row's VALUE_TO_KEY and routing row, and
            # names the field its analysis edits.
            def _own(n, k, s, a):
                rv, sg = f"{L['REVIEW']}{n}", f"{L['SUGGESTED']}{n}"
                st_, vk = f"{L['TODAY_STATUS']}{n}", f"{L['VALUE_TO_KEY']}{n}"
                field = "SETUP_HRS" if a == "Setup" else "RUN"
                return (k == f'=IF(UPPER(TRIM({rv}))="SKIP","",IF({rv}<>"",'
                             f'{rv},IF({st_}="already done","",{sg})))'
                        and s.startswith(f'=IF({vk}="","","UPDATE OPERATION '
                                         f"SET {field} = '")
                        and f"FIXED({vk},2,TRUE)" in s
                        and s.endswith(f'&{L["MASTER_OPS_ROWID"]}{n}&";")'))
            own = [_own(n, k, s, a) for n, (k, s, a) in enumerate(
                zip(u.VALUE_TO_KEY, u.SQL_UPDATE, u.ANALYSIS), 2)]
            check("every statement points at its own row, a done row keys "
                  "nothing unless reviewed",
                  all(own), f"{own.count(False)} wrong")
            check("updater 'already done' rows equal the update list",
                  int(done.sum()) == int(ex.TODAY_STATUS.astype(str)
                                         .str.startswith("already done").sum()),
                  f"{int(done.sum())} rows")

    def toggle(label):
        def f(at):
            next(x for x in at.sidebar.toggle if x.label == label).set_value(True)
        return f

    for label in ("Hide already done", "Only flagged for manual review"):
        at = render("pages/1_Review_queue.py", setup=toggle(label))
        check(f"renders with '{label}' on", not at.exception,
              "; ".join(errors(at)))

    # ---- Inspect --------------------------------------------------------
    print("Inspect", flush=True)
    units = []
    for r in acts.itertuples():
        units.append(dict(FAMILY=r.FAMILY, PART_TYPE=r.PART_TYPE,
                          OPERATION=r.OPERATION, SEQ=int(r.SEQUENCE),
                          TARGET=r.TARGET,
                          RUN_TYPE=None if r.TARGET == "SETUP_HRS" else r.RUN_TYPE,
                          PART_ID=r.PART_ID if r.LEVEL == "PART" else None))
    rnd = random.Random(20261006)
    held = []
    if paths.SETUP.exists():
        s = pd.read_excel(paths.SETUP, "01_FamilyRollup")
        sq = "OPERATION_SEQUENCE" if "OPERATION_SEQUENCE" in s else "SEQUENCE"
        for r in s.sample(min(10, len(s)), random_state=1).to_dict("records"):
            held.append(dict(FAMILY=r["FAMILY"], PART_TYPE=r["PART_TYPE"],
                             OPERATION=r["OPERATION"], SEQ=int(r[sq]),
                             TARGET="SETUP_HRS", RUN_TYPE=None, PART_ID=None))
    if paths.LOAD.exists():
        ld = pd.read_excel(paths.LOAD, "01_PartUnits")
        sq = "OPERATION_SEQUENCE" if "OPERATION_SEQUENCE" in ld else "SEQUENCE"
        for r in ld.sample(min(10, len(ld)), random_state=2).to_dict("records"):
            held.append(dict(FAMILY=r["FAMILY"], PART_TYPE=r["PART_TYPE"],
                             OPERATION=r["OPERATION"], SEQ=int(r[sq]),
                             TARGET="RUN", RUN_TYPE="HRS/LOAD",
                             PART_ID=r["PART_ID"] if rnd.random() < .5 else None))
    books = sorted(paths.OUTPUTS.glob("FTS_*_PARTS.xlsx"))
    for b in rnd.sample(books, min(6, len(books))):
        u = pd.read_excel(b, "05_AllUnits_WithEvidence")
        if u.empty or "OPERATION" not in u:
            continue
        sq = next(c for c in ("SEQUENCE", "SEQ", "OPERATION_SEQUENCE") if c in u)
        for r in u.sample(min(4, len(u)), random_state=3).to_dict("records"):
            held.append(dict(FAMILY=r["FAMILY"], PART_TYPE=r["PART_TYPE"],
                             OPERATION=u.OPERATION.iloc[0], SEQ=int(r[sq]),
                             TARGET="RUN", RUN_TYPE="PCS/HR",
                             PART_ID=r["PART_ID"] if rnd.random() < .4 else None))
    # THE STANDARD WO TILE ON A WHOLE-FAMILY ACTION: the one value its parts
    # ran with, or "n vals" where they differ (2026-10-07).
    tile_want = {}
    for i, r in enumerate(acts.itertuples()):
        if r.LEVEL == "PART":
            continue
        f = family_rows(r.FAMILY, r.PART_TYPE, r.OPERATION, int(r.SEQUENCE),
                        r.TARGET, r.RUN_TYPE)
        if len(f):
            v = one(f.STANDARD_WO)
            tile_want[i] = (f"{v:,.2f}".replace(",", "'") if pd.notna(v) else
                            f"{f.STANDARD_WO.round(4).nunique()} vals")
    failed, disagree, rows, bad_rows, bad_tile, tiles = [], [], 0, 0, [], 0
    eff = pipeline.MIN_EFFECT
    for i, unit in enumerate(units + held, 1):
        at = render("pages/2_Inspect.py", unit=unit)
        if at.exception:
            failed.append((unit["FAMILY"], unit["OPERATION"], unit["SEQ"]))
            continue
        if i - 1 in tile_want:
            tiles += 1
            got = next((m.value for m in at.metric
                        if m.label == "Standard WO"), None)
            if got != tile_want[i - 1]:
                bad_tile.append((unit["OPERATION"], unit["SEQ"], got,
                                 tile_want[i - 1]))
        if any("disagrees between the update list and the extract" in x.value
               for x in at.error):
            disagree.append((unit["FAMILY"], unit["OPERATION"], unit["SEQ"]))
        for d in at.dataframe:
            t = frame(d)
            if {"PART_ID", "WO_REV", "SUGGESTED", "STATUS"} <= set(t.columns):
                wo = pd.to_numeric(t.STANDARD_WO, errors="coerce")
                td = pd.to_numeric(t.STANDARD_TODAY, errors="coerce")
                sg = pd.to_numeric(t.SUGGESTED, errors="coerce")
                exp = ((wo - td).abs() > 0.005) & ((sg / td - 1).abs() < eff)
                rows += len(t)
                bad_rows += int((exp != (t.STATUS == "already done")).sum())
        if i % 50 == 0:
            print(f"    {i} of {len(units) + len(held)} units", flush=True)
    check(f"renders on all {len(units)} actions and {len(held)} held units",
          not failed, f"{len(failed)} failed, first {failed[:1]}")
    check("today's master agrees between update list and extract",
          not disagree, f"{len(disagree)} units, first {disagree[:1]}")
    check("every part row's Status follows from the row itself",
          rows > 0 and bad_rows == 0, f"{bad_rows} of {rows} part rows")
    check("Standard WO on every whole-family action is its parts' one value "
          "or their count", bool(tile_want) and tiles == len(tile_want)
          and not bad_tile,
          f"{len(bad_tile)} of {tiles} read differ ({len(tile_want)} "
          f"expected), first {bad_tile[:1]}")

    # ---- By part --------------------------------------------------------
    print("By part", flush=True)
    done_parts = ex[ex.TODAY_STATUS.astype(str).str.startswith("already")] \
        .PART_ID.unique().tolist()
    flagged = ex[ex.REVIEW_FLAG_TODAY.notna()
                 & (ex.REVIEW_FLAG_TODAY.astype(str).str.strip() != "")] \
        .PART_ID.unique().tolist()
    edited = sorted(set(ex.PART_ID))
    known = sorted(pd.read_parquet(paths.CACHE, columns=["PART_ID"])
                   .PART_ID.str.strip().unique())
    unedited = sorted(set(known) - set(edited))
    parts = (done_parts[:5] + flagged + rnd.sample(edited, min(8, len(edited)))
             + rnd.sample(unedited, min(4, len(unedited)))
             + ["NOT-A-PART-NUMBER"])
    failed, no_box, fam_rows, fam_bad = [], [], 0, []
    # The lower table names its analysis in words; this maps them back.
    from ftsapp import ui
    by_name = {ui.analysis_name(t, r): (t, r) for t, r in EXEC}

    def typed(p):
        return lambda at: at.text_input(key="by_part_typed").set_value(p)

    for p in dict.fromkeys(parts):
        at = render("pages/3_By_part.py", setup=typed(p))
        if at.exception:
            failed.append(p)
            continue
        if p in flagged and not any(
                w.value.startswith("**Check this against today's master.**")
                for w in at.warning):
            no_box.append(p)
        # THE LOWER TABLE'S WHOLE-FAMILY ROWS that are decisions on the update
        # list: Std WO, Std today and Suggested are the one value the family's
        # parts hold there, or blank (2026-10-07). Held rows have no list to
        # compare with and are left to the render check.
        low = [frame(d) for d in at.dataframe if "VERDICT" in frame(d).columns]
        for r in (low[0].itertuples() if low else []):
            if not str(r.APPLIES_TO).startswith("whole family"):
                continue
            t, rt = by_name.get(r.ANALYSIS, (None, None))
            mine = ex[(ex.PART_ID == p) & (ex.OPERATION == r.OPERATION)
                      & (ex.SEQ == int(r.SEQUENCE)) & (ex.TARGET == t)
                      & (ex.RUN_TYPE == rt)
                      & (ex.ROUTE.astype(str).str.upper() == "FAMILY")]
            if mine.empty:
                continue
            f = family_rows(mine.FAMILY.iat[0], mine.PART_TYPE.iat[0],
                            r.OPERATION, int(r.SEQUENCE), t, rt)
            fam_rows += 1
            wo = one(f.STANDARD_WO)
            want = (wo, one(f.STANDARD_TODAY),
                    one(f.RECOMMENDED) if pd.notna(wo) else float("nan"))
            if not all(same_value(g, w) for g, w in
                       zip((r.NOW, r.TODAY, r.SUGGESTED), want)):
                fam_bad.append((r.OPERATION, int(r.SEQUENCE),
                                (r.NOW, r.TODAY, r.SUGGESTED), want))
    check(f"renders on {len(dict.fromkeys(parts))} parts", not failed,
          f"{len(failed)} failed")
    check("the amber check appears on every part flagged against today",
          not no_box, f"{len(no_box)} without it")
    check("lower table: whole-family decisions show their parts' one value "
          "or blank", fam_rows > 0 and not fam_bad,
          f"{len(fam_bad)} of {fam_rows} rows differ, first {fam_bad[:1]}")

    # ---- the rest -------------------------------------------------------
    print("Other pages", flush=True)
    for page in ("pages/4_Additional_findings.py", "pages/5_How_to_read_it.py",
                 "pages/6_Methodology.py"):
        at = render(page)
        check(f"{page.split('/')[-1]} renders", not at.exception,
              "; ".join(errors(at)))

    ok = all(RESULTS)
    print(f"\n{'OK' if ok else 'FAILED'} - {RESULTS.count(True)} of "
          f"{len(RESULTS)} checks passed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    # A Windows console defaults to cp1252, which cannot print every character
    # an error message may carry - and a check that dies printing its own
    # failure reports nothing.
    sys.stdout.reconfigure(encoding="utf-8")
    main()
