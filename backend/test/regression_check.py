"""regression_check.py — rates every match in regression/<match id>/ (bundle.txt + report.json) with sokkerscore/live/rate_match_v4 and
compares the result with expected.json in the same folder, field by field. The expected files are written by
backend/tools/export_repo.py on the machine the pipeline was validated on, so in the public repository this check shows whether
GitHub's runner gives the same ratings (and whether any pipeline file is missing).
usage (from the repository root): python -X utf8 -I backend/test/regression_check.py [--write] [--dir <regression folder>]
--write stores the results as the new expected.json; --dir points at a regression folder elsewhere. export_repo.py runs the
project's copy with both (expected results from the validated pipeline) and then the export's copy without them."""
import sys, os, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REG = os.path.join(REPO, 'regression')


def diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b: out.append((f'{path}.{k}', a.get(k, '<absent>'), b.get(k, '<absent>')))
            else: diff(a[k], b[k], f'{path}.{k}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append((path + '[len]', len(a), len(b))); return
        for i, (x, y) in enumerate(zip(a, b)): diff(x, y, f'{path}[{i}]', out)
    elif a != b:
        out.append((path, a, b))


if __name__ == '__main__':
    write = '--write' in sys.argv
    if '--dir' in sys.argv: REG = os.path.abspath(sys.argv[sys.argv.index('--dir') + 1])
    sys.path.insert(0, os.path.join(REPO, 'sokkerscore', 'live'))
    import rate_match_v4 as R                      # changes the working directory to sokkerscore/
    bad = 0
    for mid in sorted(os.listdir(REG)):
        d = os.path.join(REG, mid)
        if not os.path.isfile(os.path.join(d, 'bundle.txt')): continue
        t0 = time.time()
        report = json.load(open(os.path.join(d, 'report.json'), encoding='utf-8'))
        m = R.rate(os.path.join(d, 'bundle.txt'), report)
        if write:
            json.dump(m, open(os.path.join(d, 'expected.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
            print(f'{mid}: wrote expected.json ({m["home"]} {m["score"]} {m["away"]}, {time.time() - t0:.0f} s)'); continue
        exp = json.load(open(os.path.join(d, 'expected.json'), encoding='utf-8'))
        out = []; diff(exp, m, 'm', out)
        print(f'{mid}: {m["home"]} {m["score"]} {m["away"]} — {"identical" if not out else str(len(out)) + " DIFFERENCES"} ({time.time() - t0:.0f} s)')
        for p, a, b in out[:25]: print(f'   {p}: expected {a!r}, got {b!r}')
        bad += bool(out)
    sys.exit(1 if bad else 0)
