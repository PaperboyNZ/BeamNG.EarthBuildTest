"""Retain shared close/middle/sky plan integration and scoped evidence."""
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
    match=re.search(r'Ran (\d+) tests?.*?\n\s*OK\s*\n',path.read_text(encoding='utf-8'),re.S)
    assert match,path
    return int(match[1])


def main():
    architecture=sorted((BASE/'p3-sky-plan-architecture').glob('*.log'))
    protocol=sorted((BASE/'p3-sky-plan-protocol').glob('*.log'))
    graphics=sorted((BASE/'p3-sky-plan-graphics').glob('*.log'))
    assert len(architecture)==70 and len(protocol)==3 and len(graphics)==2
    counts={p.stem:passed(p) for p in architecture}
    stream=BASE/'p3-sky-plan-streaming.log'
    lua=re.findall(r'(test_\w+): (\d+) passed, (\d+) failed',stream.read_text(encoding='utf-8'))
    assert len(lua)==15 and all(int(f)==0 for _,_,f in lua)
    review=BASE/'p3-accepted-representations-r2'
    pictures=json.loads((review/'results.json').read_text(encoding='utf-8'))
    for name,sha in pictures['source_hashes'].items():assert digest(ROOT/name)==sha,name
    shapes=[]
    for row in pictures['fixtures']:
        for tier,record in row['representations'].items():
            path=review/(row['family']+'-'+tier+'.cdae')
            assert digest(path)==record['sha256'],path
            shapes.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(path)))
    previous=json.loads((BASE/'p3-far-plan-checkpoint/manifest.json').read_text(encoding='utf-8'))
    names=sorted({r['path'] for r in previous['sources']} | {
        'server/buildgen/distant.py','server/buildings.py','server/geotiles.py','server/buildgen/geometry.py',
        'server/tests/test_buildgen_sky_plan.py','tools/review_accepted_representations.py',
        'tools/record_sky_plan_checkpoint.py'})
    for name in names:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'))
    destination=BASE/'p3-sky-plan-checkpoint';destination.mkdir(exist_ok=False)
    records=[]
    for name in names:
        source=ROOT/name;target=destination/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=digest(source)))
    report=dict(scope='shared-plan source implementation; not packaged or native accepted',
                base_playtest='playtest-r5/checkpoint',sources=records,
                source_sha256=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                architecture_tests=sum(counts.values()),architecture_modules=counts,
                python_streaming=passed(stream),lua_assertions=sum(int(n) for _,n,_ in lua),
                lua_suites={k:int(n) for k,n,_ in lua},
                protocol_tests=sum(passed(p) for p in protocol),graphics_tests=sum(passed(p) for p in graphics),
                logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in [*architecture,*protocol,*graphics,stream]],
                review=dict(report_sha256=digest(review/'results.json'),image_sha256=digest(review/'representations.png'),
                            path=review.relative_to(ROOT).as_posix(),shapes=shapes),
                cache='persistent accepted plans and far-building products; hybrid skyline uses session memo and distinct output/dependency identity',
                remaining='native LOD/grazing/night-texture acceptance; import and memory calibration; M1 shared-site runtime ownership',
                original_checklist_rows_complete=16,target=28)
    assert report['architecture_tests']==656 and report['python_streaming']==152 and report['lua_assertions']==3191
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    path=BASE/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    assert programme['completed_tasks']==16
    programme['in_progress_p3']=dict(checkpoint='p3-sky-plan-checkpoint/manifest.json',
        implementation='common accepted-plan close/middle/distant products complete',status=report['remaining'])
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('source_sha256','architecture_tests','python_streaming','lua_assertions','protocol_tests','graphics_tests')}))


if __name__=='__main__':main()
