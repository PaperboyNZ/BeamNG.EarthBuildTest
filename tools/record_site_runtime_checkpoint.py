"""Freeze the live legacy site-record boundary without claiming shared acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'build/world-architecture-programme'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passed(path):
    match = re.search(r'Ran (\d+) tests?.*?\n\s*OK\s*\n', path.read_text(encoding='utf-8'), re.S)
    assert match, path
    return int(match[1])


def main():
    previous_path = BASE/'p3-sky-plan-checkpoint/manifest.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    architecture = sorted((BASE/'m1-record-dispatch-architecture').glob('*.log'))
    counts = {p.stem: passed(p) for p in architecture}
    assert set(counts) == set(previous['architecture_modules']) | {'test_sitegen_runtime_records'}
    assert sum(counts.values()) == 663
    stream = BASE/'m1-record-dispatch-streaming.log'
    lua = re.findall(r'(test_\w+): (\d+) passed, (\d+) failed', stream.read_text(encoding='utf-8'))
    assert len(lua) == 15 and all(int(f) == 0 for _, _, f in lua)
    assert passed(stream) == 152 and sum(int(n) for _, n, _ in lua) == 3191
    names = sorted({r['path'] for r in previous['sources']} | {
        'server/sitegen/adapters.py', 'server/buildgen/site_data.py', 'server/buildgen/plan.py',
        'server/buildings.py', 'server/tests/test_buildgen_sites.py',
        'server/tests/test_sitegen_runtime_records.py', 'docs/SITE_RECORD_RUNTIME_PROGRESS.md',
        'tools/record_site_runtime_checkpoint.py'})
    for name in names:
        if name.endswith('.py'):
            ast.parse((ROOT/name).read_text(encoding='utf-8'))
    destination = BASE/'m1-record-dispatch-checkpoint'
    destination.mkdir(exist_ok=False)
    sources = []
    for name in names:
        source = ROOT/name
        target = destination/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        sources.append(dict(path=name, sha256=digest(source)))
    report = dict(
        scope='schema 23 live one-owner record dispatch; shared-site producer and native acceptance remain open',
        base_playtest='playtest-r5/checkpoint', previous_checkpoint=str(previous_path.relative_to(ROOT)),
        previous_manifest_sha256=digest(previous_path), sources=sources,
        source_sha256=hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        architecture_tests=sum(counts.values()), architecture_modules=counts,
        python_streaming=passed(stream), lua_assertions=sum(int(n) for _, n, _ in lua),
        lua_suites={k: int(n) for k, n, _ in lua},
        logs=[dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p)) for p in [*architecture, stream]],
        current_playtest='BeamNG.Earth-v2-world-architecture-r5-20261102', playtest_schema=22, source_schema=23,
        original_checklist_rows_complete=16, target=28,
        remaining='canonical shared producer, proposal collection/common fitting, cross-tile references/residency and station identity; native acceptance')
    (destination/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    path = BASE/'programme.json'
    programme = json.loads(path.read_text(encoding='utf-8'))
    assert programme['completed_tasks'] == 16
    programme['in_progress_m1'] = dict(checkpoint='m1-record-dispatch-checkpoint/manifest.json',
        implementation='live one-owner compatibility path consumes immutable site records with exact emitter parity',
        status=report['remaining'])
    path.write_text(json.dumps(programme, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('source_sha256', 'architecture_tests', 'python_streaming', 'lua_assertions')}))


if __name__ == '__main__':
    main()
