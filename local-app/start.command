#!/bin/bash
# Double-click to start the Geniza phrase search, then it opens in your browser. Close this window to stop it.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv && .venv/bin/pip install -q duckdb pandas; fi
(sleep 3; open "http://localhost:8770") &
exec .venv/bin/python app.py --port 8770
