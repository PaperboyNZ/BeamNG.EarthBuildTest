"""Freeze far-building accepted-plan reuse and retain exact verification scope."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/world-architecture-programme'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def passed(path):
    content=path.read_text(encoding='utf-8')
    match=re.search(r'Ran (\d+) tests?.*?\n\s*OK\s*\n',content,re.S)
    assert match, path
    return int(match[1])


def main():
    architecture=sorted((BASE/'p3-far-plan-architecture-final').glob('*.log'))
    assert len(architecture)==69
    counts={p.stem:passed(p) for p in architecture}
    protocol=sorted((BASE/'p3-far-plan-protocol-fixed').glob('*.log'))
    graphics=sorted((BASE/'p3-far-plan-graphics-fixed').glob('*.log'))
    assert len(protocol)==3 and len(graphics)==2
    protocol_count=sum(passed(p) for p in protocol);graphics_count=sum(passed(p) for p in graphics)
    stream=BASE/'p3-far-plan-final-streaming.log'
    lua=re.findall(r'(test_\w+): (\d+) passed, (\d+) failed',stream.read_text(encoding='utf-8'))
    assert len(lua)==15 and all(int(f)==0 for _,_,f in lua)
    previous=json.loads((BASE/'p3-deep-middle-checkpoint/manifest.json').read_text(encoding='utf-8'))
    names=sorted({r['path'] for r in previous['sources']} | {
        'server/buildgen/products.py','server/blockworker.py','server/earthd.py','server/roads.py',
        'server/vegetation.py','server/tests/test_buildgen_far_plan.py','server/tests/test_far_plan_lifecycle.py',
        'docs/DISTANT_PLAN_REUSE_PROGRESS.md','tools/record_far_plan_checkpoint.py'})
    for name in names:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'))
    destination=BASE/'p3-far-plan-checkpoint';destination.mkdir(exist_ok=False)
    records=[]
    for name in names:
        source=ROOT/name;target=destination/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=digest(source)))
    report=dict(scope='source-only far-building reuse; skyline integration and native acceptance open',
                base_playtest='playtest-r5/checkpoint',sources=records,
                source_sha256=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                architecture_tests=sum(counts.values()),architecture_modules=counts,
                python_streaming=passed(stream),lua_assertions=sum(int(n) for _,n,_ in lua),
                lua_suites={k:int(n) for k,n,_ in lua},protocol_tests=protocol_count,graphics_tests=graphics_count,
                logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in [*architecture,*protocol,*graphics,stream]],
                retained_initial_issues=['p3-far-plan-integrated/test_graphics.log: Windows asyncio socket-pair blocked in sandbox; process subsequently absent',
                    'p3-far-plan-protocol/test_protocol_agreement.SessionsAgreementTest.log: old hello fixture invoked with v2; corrected legacy run passes'],
                remaining='mixed accepted/cold skyline children; native transitions, import, contact and memory calibration',
                original_checklist_rows_complete=15,target=28)
    assert report['architecture_tests']==641 and report['python_streaming']==137
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    path=BASE/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    programme['in_progress_p3']=dict(checkpoint='p3-far-plan-checkpoint/manifest.json',status=report['remaining'])
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('source_sha256','architecture_tests','python_streaming','lua_assertions','protocol_tests','graphics_tests')}))


if __name__=='__main__':main()
