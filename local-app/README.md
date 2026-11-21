# Local app

A version of the phrase search that runs on your own computer, over the full DuckDB database. Counts of example lines are exact here.

1. Get `phrases.duckdb` (1.1 GB) from the Haifa server: `/nas/archive/haifa-data/noam/fgp_report/phrases.duckdb`. Put it in `local-app/data/`, together with `data/pgp_links.json` from this repository (for the Princeton links).
2. Double-click `start.command`. On a Mac it sets up Python the first time and opens http://localhost:8770. From a terminal: `.venv/bin/python app.py`.

`search.py` can also be used from Python or the command line; see `../docs/TECHNICAL.md`, section 8.
