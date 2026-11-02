#!/usr/bin/env python3
"""Worldwide architectural A/B capture using the existing benchmark.py game harness.

list / plan / validate work without BeamNG. run requires the running Earth level
and BeamNG's built-in MCP (Options > Advanced > MCP). See docs/world_tour.html.
"""
import argparse
from collections import Counter
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import signal
import sys

import benchmark as bm

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'docs/world_tour.json'
RUNS = ROOT / 'docs/research/world-tour'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def select(data, args):
    rows = data['places']
    if args.group != 'all':
        rows = [p for p in rows if p['group'] == args.group]
    if args.theme:
        rows = [p for p in rows if (p.get('theme') or p.get('routed_theme')) == args.theme]
    if args.tag:
        rows = [p for p in rows if set(args.tag).issubset(p['tags'])]
    if args.places:
        ids = set(args.places.split(','))
        unknown = ids - {p['id'] for p in data['places']}
        if unknown:
            raise ValueError('Unknown places: ' + ', '.join(sorted(unknown)))
        rows = [p for p in rows if p['id'] in ids]
    return rows[args.offset:None if args.limit is None else args.offset + args.limit]


def safe_image(run, name):
    if not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name:
        return False
    path = Path(run) / name
    return path.is_file() and path.stat().st_size > 0


def complete(place, folder, expected):
    """Never skip an incomplete/timed-out place or one whose pictures were deleted."""
    if not place.get('ok') or place.get('load', {}).get('timedOut'):
        return False
    views = {v['name']: v for v in place.get('views', [])}
    return bool(expected) and all(
        name in views and not views[name].get('timedOut')
        and safe_image(folder, views[name].get('file')) for name in expected)


def skip_completed(rows, data, folders, build):
    expected = {p['id']: [v['name'] for v in p.get('views', data['defaults']['views'])] for p in rows}
    done = set()
    for folder in folders:
        rec = read_json(Path(folder) / 'run.json')
        if rec.get('setDigest') != digest(data) or rec.get('tourBuild') != build:
            raise ValueError(f'{folder}: different catalog or build; refusing to mix captures')
        for p in rec.get('places', []):
            if p['id'] in expected and complete(p, folder, expected[p['id']]):
                done.add(p['id'])
    return [p for p in rows if p['id'] not in done]


def validate(data, routing=False):
    bm.validate_set(data)
    profiles = read_json(ROOT / 'server/buildgen/catalog/regional_profiles.json')['profiles']
    core = [p for p in data['places'] if p['group'] == 'core']
    counts = Counter(p['theme'] for p in core)
    if set(counts) != set(profiles) or any(n != 1 for n in counts.values()):
        raise ValueError('Core must contain exactly one place for each installed regional profile')
    if routing:
        sys.path.insert(0, str(ROOT / 'server'))
        from buildgen.regional_geography import locate
        for p in data['places']:
            actual = locate(p['lat'], p['lon'])
            if p['group'] == 'core' and actual.theme != p['theme']:
                raise ValueError(f"{p['id']}: expected {p['theme']}, routed to {actual.theme or 'neutral'}")
            if actual.theme != p.get('routed_theme') or actual.method != p.get('routing_method'):
                raise ValueError(f"{p['id']}: routing changed; review and refresh catalog metadata")
    return len(core)


def write_html(data, rows, output):
    esc = html.escape
    table = []
    for p in rows:
        theme = p.get('theme') or p.get('routed_theme') or 'unresolved / neutral'
        reference = f' <a href="{esc(p["reference"], quote=True)}">reference</a>' if p.get('reference') else ''
        url = f'https://www.openstreetmap.org/?mlat={p["lat"]}&mlon={p["lon"]}#map=17/{p["lat"]}/{p["lon"]}'
        table.append(f'<tr><td>{esc(p["group"])}</td><td><b>{esc(p["name"])}</b><br>{esc(p["country"])}<br><code>{esc(p["id"])}</code></td>'
                     f'<td>{esc(theme)}</td><td><a href="{url}">{p["lat"]:.4f}, {p["lon"]:.4f}</a></td>'
                     f'<td>{esc(", ".join(p["tags"]))}</td><td>{esc(p["why"])}{reference}</td></tr>')
    countries = Counter(p['country'] for p in data['places'])
    text = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>BeamNG.Earth world tour</title>
<style>body{font:15px/1.5 system-ui;margin:32px;color:#203044;background:#f7f9fc}main{max-width:1600px;margin:auto}
h1{font-size:32px}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #dde3ec;vertical-align:top}th{position:sticky;top:0;background:#203044;color:white}code{font-size:12px}input{padding:12px;width:min(640px,90%);margin:20px 0}a{color:#125ab0}pre{background:#e9eef5;padding:16px;overflow:auto}.note{border-left:4px solid #d58c23;padding-left:15px}</style>
<main><h1>BeamNG.Earth: 128-place world tour</h1>
<p><b>64 regional checks + 64 additional stress cases.</b> Every implemented geographic style has one core location.
Five places are in the USA; one is in New Zealand. The remaining 122 span the rest of the world.</p>
<p class="note">These are candidate neighbourhood anchors, not surveyed vehicle spawn points or game-verified camera compositions.
Scout a small batch before the full run. Four cardinal street views plus one elevated district view reduce dependence on a single heading.
Move obstructed anchors in world_tour.json and freeze the revised catalog before capturing both builds.</p>
<p>Core routing was checked against the bundled geographic polygons. The Lagos market and Funafuti stress anchors deliberately retain unresolved routing: test neutral fallback and missing small-island/coastal coverage.
Routing success does not prove that building footprints or imagery exist. A missing-data result is useful evidence, not automatically a generator failure.</p>
<h2>What to compare</h2><p>Footprint and height fidelity; regional roofs/materials/window proportions; entrances and garage access; roads and sidewalk clearance;
courtyards and water exclusions; paving/planting; and loading/LOD consistency. A <b>stretch</b> tag marks geometry the current implementation may not support,
such as stilt houses, sunken homes or distinctive roof structures. Judge its fallback and record the missing capability separately from regressions.</p>
<h2>Capture workflow</h2><p>From the workspace root in PowerShell, use the launcher below. Start the desired build and Earth level first, enable
<b>Options &gt; Advanced &gt; MCP</b>, park the vehicle, keep the game focused and leave it alone while capturing. Stop the server and restart BeamNG when switching builds.</p>
<pre>.\\"World tour.bat" list
.\\"World tour.bat" check
.\\"World tour.bat" plan --limit 3
.\\"World tour.bat" run --label original --build ORIGINAL_BUILD_ID --limit 3
# After inspecting the pilot and selecting the original build again:
.\\"World tour.bat" run --label original-full --build ORIGINAL_BUILD_ID
# Switch both server and mod to the modified build, then:
.\\"World tour.bat" run --label modified-full --build MODIFIED_BUILD_ID
.\\"World tour.bat" compare "PATH_TO_ORIGINAL_RUN" "PATH_TO_MODIFIED_RUN" --out "PATH_TO_REPORT"</pre>
<p>Use an exact version/checkpoint identifier for <code>--build</code>. It records your declaration; the runner does not install, switch or authenticate a build.
Keep resolution, graphics settings, render distances, vehicle, traffic and cache conditions consistent. The capture harness fixes the date, local solar time and clear weather.</p>
<pre># Filters combine; repeated --tag means all those tags must match.
.\\"World tour.bat" run --label industrial --build BUILD_ID --tag industrial
.\\"World tour.bat" run --label regional --build BUILD_ID --group core
.\\"World tour.bat" run --label next-batch --build BUILD_ID --offset 16 --limit 16
.\\"World tour.bat" run --label retry --build BUILD_ID --skip-completed "PREVIOUS_RUN"
.\\"World tour.bat" merge "MERGED_RUN" "PREVIOUS_RUN" "RETRY_RUN"
.\\"World tour.bat" restore "INTERRUPTED_RUN"</pre>
<p>Each full run requests <b>640 screenshots</b> (five per location). JPG is the default; <code>--png</code> is available.
Allow several hours: the default settle and measurement windows alone total about 3.6 hours, before downloads and loading. Start with a small pilot or use batches.
Terrain/road/import readiness is polled, followed by a 15-second settle per view. This does not prove every progressive building has reached final detail:
inspect results and use <code>--wait-backlog</code> with a companion server started with <code>--status-interval 1</code> when available.
Timeouts remain visible in the run record and are not accepted by resume/merge as completed captures.</p>
<p>Runs go to <code>BeamNG.EarthBuildTest/docs/research/world-tour/</code>, with a unique folder, screenshots, catalog snapshot, build label,
<code>run.json</code> and restore state. Ctrl+C triggers the existing harness's restore logic. If the process is killed, use <code>restore</code>.
Resuming writes a new run and never overwrites previous images. Merge only combines the same build, catalog and capture settings.</p>
<p>A/B reports contain paired images, difference heatmaps and performance figures. Visual change is not automatically improvement.
AGL camera placement can change when geometry beneath the camera changes; the report flags differing actual camera positions and timed-out views.
The original build must expose the Earth core APIs used by tools/benchmark.lua; run <code>check</code> first. No captures have been claimed merely from offline validation.</p>
<h2>Itinerary</h2><input id="query" placeholder="Filter by place, country, style, density, industry, slope..." aria-label="Filter itinerary"><span id="count"></span>
<table><thead><tr><th>Set</th><th>Place</th><th>Regional style</th><th>Latitude, longitude</th><th>Coverage</th><th>A/B target</th></tr></thead><tbody>ROWS</tbody></table>
<p>Country / territory counts: COUNTRIES</p></main>
<script>const q=document.querySelector('#query'), rows=[...document.querySelectorAll('tbody tr')];function filter(){let n=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(q.value.toLowerCase());if(!r.hidden)n++}document.querySelector('#count').textContent=n+' places'}q.addEventListener('input',filter);filter()</script></html>'''
    text = text.replace('ROWS', '\n'.join(table)).replace('COUNTRIES', esc(', '.join(f'{k}: {v}' for k, v in sorted(countries.items()))))
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(text, encoding='utf-8')


def merge_runs(output, folders):
    records = [(Path(f), read_json(Path(f) / 'run.json')) for f in folders]
    first = records[0][1]
    if not first.get('tourBuild') or not first.get('setDigest'):
        raise ValueError('Merge requires world-tour run records')
    for folder, rec in records:
        for key in ('tourBuild', 'setDigest', 'captureSettings'):
            if rec.get(key) != first.get(key):
                raise ValueError(f'{folder}: different {key}')
    catalog_path = records[0][0] / 'catalog.json'
    catalog = read_json(catalog_path) if catalog_path.exists() else first['tourCatalog']
    expected = {p['id']: [v['name'] for v in p.get('views', catalog['defaults']['views'])] for p in catalog['places']}
    chosen = {}
    for folder, rec in records:
        for p in rec['places']:
            if p['id'] in expected and complete(p, folder, expected[p['id']]):
                chosen[p['id']] = (folder, p)
    if not chosen:
        raise ValueError('No complete captures to merge')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    result = {k: copy.deepcopy(v) for k, v in first.items() if k not in ('places', 'home', 'restore', 'aborted', 'finished', 'started')}
    result.update(label=out.name, mergedFrom=[str(f.resolve()) for f, _ in records], places=[])
    for p in catalog['places']:
        if p['id'] not in chosen:
            continue
        folder, place = chosen[p['id']]
        item = copy.deepcopy(place)
        item['sourceRun'] = str(folder.resolve())
        for view in item['views']:
            shutil.copyfile(folder / view['file'], out / view['file'])
        result['places'].append(item)
    bm._write_json(out / 'catalog.json', catalog)
    bm._write_json(out / 'run.json', result)
    print(f'Merged {len(result["places"])} complete places into {out}')


def compare_runs(a, b, out):
    if Path(out).exists():
        raise ValueError('Comparison output already exists; choose a new folder')
    report = bm.compare(a, b, out)
    runs = [read_json(Path(folder) / 'run.json') for folder in (a, b)]
    lookup = [{p['id']: p for p in r['places']} for r in runs]
    for row in report['places']:
        places = [r.get(row['id'], {}) for r in lookup]
        views = [{v['name']: v for v in p.get('views', [])} for p in places]
        for shot in row['views']:
            pair = [v.get(shot['name'], {}) for v in views]
            notes = [shot['note']] if shot.get('note') else []
            if any(p.get('load', {}).get('timedOut') or v.get('timedOut') for p, v in zip(places, pair)):
                notes.append('INCOMPLETE: loading timed out; do not treat this as a settled A/B pair')
            xyz = [v.get('placed', {}) for v in pair]
            if all(all(isinstance(p.get(k), (float, int)) for k in ('x', 'y', 'z')) for p in xyz):
                if any(abs(xyz[0][k] - xyz[1][k]) > 0.05 for k in ('x', 'y', 'z')):
                    notes.append('ACTUAL CAMERA MOVED: ground/roof height or placement changed; inspect before judging differences')
            if notes:
                shot['note'] = '; '.join(notes)
    bm._write_json(Path(out) / 'compare.json', report)
    (Path(out) / 'index.html').write_text(bm.compare_html(report), encoding='utf-8')
    print(f'Report: {Path(out) / "index.html"}')


def nonnegative(value):
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError('must be nonnegative')
    return n


def positive(value):
    n = float(value)
    if not math.isfinite(n) or n <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='cmd', required=True)
    for cmd in ('list', 'plan', 'run'):
        p = subs.add_parser(cmd)
        p.add_argument('--group', choices=('all', 'core', 'stress'), default='all')
        p.add_argument('--theme')
        p.add_argument('--tag', action='append', default=[])
        p.add_argument('--places', help='comma-separated place IDs')
        p.add_argument('--offset', type=nonnegative, default=0, help='zero-based offset after filtering')
        p.add_argument('--limit', type=nonnegative)
    subs.choices['list'].add_argument('--html', help='write a searchable itinerary')
    rp = subs.choices['run']
    rp.add_argument('--label', required=True)
    rp.add_argument('--build', required=True, help='exact identity of the build YOU have loaded')
    rp.add_argument('--runs', default=str(RUNS))
    rp.add_argument('--skip-completed', action='append', default=[], metavar='RUN_FOLDER')
    rp.add_argument('--timeout', type=positive, default=600)
    rp.add_argument('--view-timeout', type=positive, default=180)
    rp.add_argument('--settle', type=positive, default=15)
    rp.add_argument('--png', action='store_true')
    rp.add_argument('--wait-backlog', action='store_true')
    subs.add_parser('check')
    vp = subs.add_parser('validate')
    vp.add_argument('--routing', action='store_true', help='requires the server Python environment (shapely)')
    cp = subs.add_parser('compare')
    cp.add_argument('original')
    cp.add_argument('modified')
    cp.add_argument('--out', required=True)
    mp = subs.add_parser('merge')
    mp.add_argument('output')
    mp.add_argument('runs', nargs='+')
    subs.add_parser('restore').add_argument('run')
    a = parser.parse_args(argv)
    if a.cmd == 'check':
        return bm.main(['check'])
    if a.cmd == 'restore':
        return bm.main(['restore', a.run])
    if a.cmd == 'compare':
        compare_runs(a.original, a.modified, a.out)
        return 0
    if a.cmd == 'merge':
        merge_runs(a.output, a.runs)
        return 0
    data = read_json(CATALOG)
    count = validate(data, a.cmd == 'validate' and a.routing)
    if a.cmd == 'validate':
        print(f'{len(data["places"])} places; {count}/64 regional styles; catalog valid' + ('; routing checked' if a.routing else ''))
        return 0
    rows = select(data, a)
    if a.cmd == 'run':
        rows = skip_completed(rows, data, a.skip_completed, a.build)
    if not rows:
        print('No places selected (or all selected places already captured).')
        return 0
    if a.cmd == 'list':
        for p in rows:
            print(f'{p["id"]:30} {p["lat"]:9.4f}, {p["lon"]:10.4f}  {p["name"]} | {p["why"]}')
        print(f'{len(rows)} places')
        if a.html:
            write_html(data, rows, a.html)
            print(f'Itinerary: {a.html}')
        return 0
    planned = bm.plan({**data, 'places': rows}, 'all')
    if a.cmd == 'plan':
        bm.print_plan(planned)
        return 0
    opts = bm.options(timeout=a.timeout, view_timeout=a.view_timeout, settle=a.settle, png=a.png, backlog=a.wait_backlog)
    settings = {'settle': a.settle, 'png': a.png, 'wait_backlog': a.wait_backlog}
    out = bm.run_dir(a.runs, a.label)
    meta = dict(label=a.label, tourBuild=a.build, set=str(CATALOG), setDigest=digest(data),
                captureSettings=settings, selectedIds=[p['id'] for p in rows], tourCatalog=data, git=bm.git_info())
    signal.signal(signal.SIGTERM, bm._sigterm)
    print(f'Capturing {len(rows)} places / {sum(len(p["views"]) for p in planned)} views -> {out}', flush=True)
    try:
        rec = bm.run(bm.Game(), planned, out, opts, meta=meta)
    finally:
        if out.is_dir():
            bm._write_json(out / 'catalog.json', data)
    expected = {p['id']: [v['name'] for v in p['views']] for p in planned}
    done = sum(complete(p, out, expected[p['id']]) for p in rec['places'])
    print(f'Complete: {done}/{len(planned)} places. Run: {out}')
    return 0 if done == len(planned) and not rec.get('aborted') and rec.get('restore', {}).get('ok') else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nStopped. Check run.json restore status; use restore if necessary.', file=sys.stderr)
        raise SystemExit(130)
    except (ValueError, OSError, RuntimeError, ImportError) as e:
        print(f'World tour: {e}', file=sys.stderr)
        raise SystemExit(1)
