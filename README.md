# SokkerScore — rating pipeline and backend

SokkerScore gives every player in a [Sokker](https://sokker.org) match a Sofascore-style rating from 3.0 to 10.0, with the stats
behind it (expected goals, passes, duels, dribbles, defending, goalkeeping). A browser extension shows it as an extra tab in
Sokker's match report. This repository is the part that runs on a server: the code that rates a match and the shared database.

## How it works
1. The extension uploads a match's raw data (the viewer bundle and Sokker's match report) to a Supabase project and queues it.
2. A GitHub Actions job (`.github/workflows/rate.yml`, every five minutes) runs `backend/worker/rate_queue.py`: it takes the
   queued matches, rates each with `sokkerscore/live/rate_match_v2.py`, publishes the result as a JSON file and stores the
   players' rows and totals in the database.
3. The extension reads the result and shows the tab; player profiles and comparison groups come from the same database.

## What is here
```
sokkerscore/            the rating pipeline (Python, numpy only): bundle decoder, detectors, xG / xA models with their
                        training data, the rating formula. Only the files rating a match needs; file names carry version
                        numbers because every change to an analysis file is a new file.
sokkerscore/live/rate_match_v2.py    rates one match:  bundle + report  ->  the match object the extension renders
backend/sql/001_schema.sql           the database: tables, storage buckets, access rules, functions (Supabase / PostgreSQL)
backend/worker/rate_queue.py         the worker
backend/worker/result_payload.py     rated match -> what the database stores
backend/test/regression_check.py     rates the matches in regression/ and compares with the stored results
regression/<match id>/               bundle, report and expected result of a few matches
```

## Rating a match yourself
```
pip install -r requirements.txt
python -X utf8 -I sokkerscore/live/rate_match_v2.py regression/43784593/bundle.txt regression/43784593/report.json out.json
```
A match takes about half a minute.

## Setting up the worker
Run `backend/sql/001_schema.sql` once in the Supabase SQL editor, then add two repository secrets (Settings → Secrets and
variables → Actions): `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (the secret service key, never the public one).

The rating formula is public: see the docstrings of `sokkerscore/poss/ratings_v*.py`.
