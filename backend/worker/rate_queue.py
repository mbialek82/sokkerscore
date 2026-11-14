"""rate_queue.py — the worker: rates the matches waiting in the SokkerScore database. GitHub Actions runs it (.github/workflows/rate.yml).

For each match handed out by ss_claim:
  1. download its raw files from the private bucket ss-raw (report.json, bundle.txt or bundle.txt.gz, lineup.json if there);
  2. rate it with sokkerscore/live/rate_match_v3;
  3. check that bundle and report are the same match (same score; after a shootout the report carries the shootout score);
  4. write matches/<id>.json to the public bucket ss-results;
  5. store the match with ss_store_result (match row, player rows, comparison-group totals, in one transaction).
A match that cannot be rated is reported with ss_fail and its error. A network failure (download, upload, database call) sends it back
to the queue, up to three attempts; anything else (the bundle does not decode, bundle and report are different matches, the pipeline
stops on it) would fail the same way again, so the match is marked failed at once.

Environment: SUPABASE_URL, SUPABASE_SERVICE_KEY (the secret service key, never the public one).
Optional:    SS_BATCH (matches per claim, default 5), SS_MAX_MINUTES (take no new match after this long, default 40).
Only the standard library and numpy (for the pipeline) are needed.
usage: python -X utf8 -I backend/worker/rate_queue.py"""
import sys, os, json, gzip, time, tempfile, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
BATCH = int(os.environ.get('SS_BATCH', '5'))
MAX_MINUTES = float(os.environ.get('SS_MAX_MINUTES', '40'))
# Kinds of match that are rated (competition.type in Sokker's report): league, promotion play-off, national cup, international
# cup, national-team qualifiers, World Cup and national-team friendlies. Club friendlies, arcade and junior-league matches are
# not (owner's decision, 13 Nov 2026). The extension has the same list (extension/src/config.js) and does not send the others;
# this check is for anything uploaded some other way.
RATED = {'league', 'qual', 'cup', 'international', 'wc_qual', 'wc_group', 'nt_friendly'}


class Transient(Exception):
    """A failure of the network or of Supabase: the same match may well work on the next attempt."""


def http(method, path, body=None, headers=None, ok404=False):
    h = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY}
    h.update(headers or {})
    req = urllib.request.Request(URL + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        text = e.read().decode('utf-8', 'replace')[:500]
        if ok404 and e.code in (400, 404) and ('not_found' in text or 'not found' in text.lower() or e.code == 404):
            return None                            # Supabase storage answers a missing object with 400 {"error": "not_found"}
        raise Transient(f'{method} {path}: HTTP {e.code} {text}') from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise Transient(f'{method} {path}: {e}') from None


def rpc(name, args):
    out = http('POST', '/rest/v1/rpc/' + name, json.dumps(args, ensure_ascii=False).encode('utf-8'), {'Content-Type': 'application/json'})
    return json.loads(out) if out and out.strip() else None


def raw(path, required=False):
    b = http('GET', '/storage/v1/object/ss-raw/' + path, ok404=not required)
    return b


def put_result(path, data):
    http('POST', '/storage/v1/object/ss-results/' + path, data,
         {'Content-Type': 'application/json', 'x-upsert': 'true', 'cache-control': 'max-age=300'})


def rate_one(mid, R, RP):
    report = json.loads(raw(f'{mid}/report.json', required=True).decode('utf-8'))
    if int(report.get('id') or 0) != mid:
        raise ValueError(f'the report is for match {report.get("id")}')
    kind = (report.get('competition') or {}).get('type')
    if kind not in RATED:
        raise ValueError(f'not a rated kind of match ({kind}); only official matches are rated')
    b = raw(f'{mid}/bundle.txt')
    if b is None:
        b = gzip.decompress(raw(f'{mid}/bundle.txt.gz', required=True))
    lu = raw(f'{mid}/lineup.json')
    lineup = json.loads(lu.decode('utf-8')) if lu else None
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, f'match_{mid}.txt')
        with open(path, 'wb') as f: f.write(b)
        m = R.rate(path, report, lineup=lineup)
    rs = [report['home']['score'], report['away']['score']]
    if m['score'] != rs and m.get('shootout') != rs:
        raise ValueError(f'the bundle ends {m["score"]}, the report says {rs}: not the same match')
    put_result(f'matches/{mid}.json', json.dumps(m, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    meta, players = RP.payload(m, report)
    rpc('ss_store_result', dict(p_match_id=mid, p_pipeline=m['pipeline'], p_meta=meta, p_players=players))
    return m


def main():
    if not URL or not KEY:
        print('SUPABASE_URL and SUPABASE_SERVICE_KEY must be set'); return 2
    sys.path.insert(0, os.path.join(PROJECT, 'sokkerscore', 'live')); sys.path.insert(0, HERE)
    import result_payload as RP
    import rate_match_v3 as R                      # changes the working directory to sokkerscore/
    t0 = time.time(); done = failed = 0
    while time.time() - t0 < MAX_MINUTES * 60:
        ids = rpc('ss_claim', dict(p_limit=BATCH)) or []
        if not ids: break
        for mid in ids:
            mid = int(mid); t1 = time.time()
            try:
                m = rate_one(mid, R, RP)
                done += 1
                print(f'rated {mid} {m["home"]} {m["score"][0]}:{m["score"][1]} {m["away"]} in {time.time() - t1:.0f} s', flush=True)
            except Exception as e:
                failed += 1
                msg = f'{type(e).__name__}: {e}'
                print(f'FAILED {mid}: {msg[:300]}', flush=True)
                try: rpc('ss_fail', dict(p_match_id=mid, p_error=msg[-1500:], p_final=not isinstance(e, Transient)))
                except Exception as e2: print(f'  and ss_fail failed too: {e2}', flush=True)
    print(f'worker done: {done} rated, {failed} failed, {time.time() - t0:.0f} s', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
