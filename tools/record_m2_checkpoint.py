"""Freeze the verified source-only M2 transaction slice and its scoped evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/world-architecture-programme'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='m2-transaction-checkpoint')
    parser.add_argument('--stream-log',default='m2-transaction-final-streaming.log')
    parser.add_argument('--protocol-dir',default='m2-transaction-final-protocol')
    options=parser.parse_args()
    assert Path(options.out).name==options.out and options.out.startswith('m2-transaction-checkpoint'), 'checkpoint must be a local programme leaf'
    assert Path(options.stream_log).name==options.stream_log and options.stream_log.endswith('.log'), 'streaming log must be a local programme file'
    assert Path(options.protocol_dir).name==options.protocol_dir, 'protocol logs must be a local programme folder'
    previous=json.loads((BASE/'m2-resource-checkpoint/manifest.json').read_text(encoding='utf-8'))
    sources=sorted({r['path'] for r in previous['sources']} | {
        'mod/beamng_earth/lua/ge/extensions/beamngEarth/physicalhandover.lua',
        'mod/tests/test_physical_handover.lua','tools/record_m2_checkpoint.py',
        'mod/beamng_earth/lua/ge/extensions/beamngEarth/buildingprogress.lua',
        'mod/tests/test_resource_patches.lua','mod/tests/test_building_progress.lua',
        'tools/update_world_programme.py','docs/GENERATION_IMPLEMENTATION_CHECKLIST.md'})
    stream=BASE/options.stream_log
    result=stream.read_text(encoding='utf-8')
    python=re.search(r'Ran (\d+) tests.*?\n\s*OK\s*\n',result,re.S)
    lua=re.findall(r'(test_\w+): (\d+) passed, (\d+) failed',result)
    assert python and len(lua)==13 and all(int(f)==0 for _,_,f in lua), 'streaming checks incomplete'
    protocol=sorted((BASE/options.protocol_dir).glob('*.log'))
    assert len(protocol)==3
    protocol_count=0
    for path in protocol:
        log=path.read_text(encoding='utf-8')
        match=re.search(r'Ran (\d+) tests?.*?\n\s*OK\s*\n',log,re.S)
        assert match, f'protocol check incomplete: {path}'
        protocol_count+=int(match[1])
    destination=BASE/options.out
    destination.mkdir(exist_ok=False)
    records=[]
    for name in sources:
        source=ROOT/name;target=destination/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    logs=[]
    for path in [stream,*protocol]:
        logs.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    remaining='shared-site ownership; oversized-sector and native memory/contact calibration'
    report=dict(scope='source implementation only; not packaged and no native acceptance',
                sources=records,logs=logs,python_streaming=int(python[1]),
                lua_suites={name:int(n) for name,n,_ in lua},lua_assertions=sum(int(n) for _,n,_ in lua),
                focused_protocol_tests=protocol_count,remaining=remaining,
                native='pending existing warning approval',playtest='BeamNG.Earth-v2-world-architecture-r5-20261102')
    report['source_sha256']=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    path=BASE/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    programme['in_progress_m2']=dict(checkpoint=options.out+'/manifest.json',status=remaining,
                                   implemented='whole-content and skin/exact subset transactions, metadata ownership, source folders and deletion-debt admission')
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('source_sha256','python_streaming','lua_assertions','focused_protocol_tests')}))


if __name__=='__main__':main()
