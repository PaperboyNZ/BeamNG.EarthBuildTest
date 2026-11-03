"""Freeze verified shared-governor import pricing; no native performance claim."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/world-architecture-programme'


def main():
    stream=BASE/'p6-priced-import-streaming.log'
    output=stream.read_text(encoding='utf-8')
    python=re.search(r'Ran (\d+) tests.*?\n\s*OK\s*\n',output,re.S)
    lua=re.findall(r'(test_\w+): (\d+) passed, (\d+) failed',output)
    assert python and len(lua)==15 and all(int(f)==0 for _,_,f in lua)
    previous=json.loads((BASE/'m2-transaction-checkpoint-patches/manifest.json').read_text(encoding='utf-8'))
    sources=sorted({r['path'] for r in previous['sources']} | {
        'mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua',
        'mod/beamng_earth/lua/ge/extensions/beamngEarth/stopwatch.lua',
        'mod/tests/test_governor.lua','mod/tests/test_progress_budget.lua',
        'server/buildgen/progressive.py','tools/record_p6_checkpoint.py',
        'docs/PROGRESSIVE_BUILDINGS.md','docs/WORLD_ARCHITECTURE_PROGRAMME.md'})
    destination=BASE/'p6-priced-import-checkpoint'
    destination.mkdir(exist_ok=False)
    records=[]
    for name in sources:
        source=ROOT/name;target=destination/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    report=dict(scope='source implementation; r5 unchanged; native calibration and acceptance pending',
                sources=records,
                logs=[dict(path=stream.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(stream.read_bytes()).hexdigest())],
                python_streaming=int(python[1]),lua_suites={n:int(c) for n,c,_ in lua},
                lua_assertions=sum(int(c) for _,c,_ in lua),
                diagnostics='wall-time imports/queue percentiles over latest 256 attempts; aggregate exposure/waste counters',
                fairness='missing coverage first, then overdue groups in arrival order, then benefit/cost',
                native='engine stubs verify scheduling contracts only; actual frame/import/memory/contact measurements pending')
    report['source_sha256']=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    path=BASE/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    programme['p6_import_pricing']=dict(checkpoint='p6-priced-import-checkpoint/manifest.json',
                                        implementation='complete',native_calibration='pending')
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('source_sha256','python_streaming','lua_assertions')}))


if __name__=='__main__':main()
