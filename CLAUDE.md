# factory_time_statistics_streamlit_app

The FTS viewer: a browser view over the master-time analysis, so project management, finance and
supply chain can read the proposed standard changes and the work orders behind them.

## Shared rules - read first

The rules every factory project follows (databases, SQL, data and people, ERP
facts, how to answer, git) are in
`~\GitHub\factory_shared_private\RULES.md`, imported here:

@~/GitHub/factory_shared_private/RULES.md

If that import did not load, read the file before anything else. What follows
is specific to this project.

## This project

- Read first: `README.md`; the analysis itself is in `factory_time_statistics`.
- Private twin: `~\GitHub\factory_time_statistics_streamlit_app_private\` (data, outputs, notes that
  name real parts; never a git repository).
- Python: conda env `fts` (`%LOCALAPPDATA%\miniconda3\envs\fts\python.exe`), built from
  `requirements.txt`; `requirements-lock.txt` pins what it was proven on.
- Saved memory: `~\.claude\projects\<encoded path of the repo>-factory-time-statistics-streamlit-app\memory\`.
