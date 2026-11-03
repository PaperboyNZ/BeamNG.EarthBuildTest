"""Retain exact source and verification for the deep-middle representation slice."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/world-architecture-programme'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def successful(path):
    text=path.read_text(encoding='utf-8')
    match=re.search(r'Ran (\d+) tests?.*?\n\s*OK\s*\n',text,re.S)
    assert match, path
    return int(match[1])


def main():
    previous=json.loads((BASE/'p6-priced-import-checkpoint/manifest.json').read_text(encoding='utf-8'))
    sources=sorted({r['path'] for r in previous['sources']} | {
        'server/buildgen/facades.py','server/buildgen/regional_openings.py',
        'server/tests/test_buildgen_middle_recess.py','server/tests/test_buildgen_residential_structures.py',
        'server/tests/test_buildgen_facades.py','tools/review_middle_recess.py',
        'tools/building_preview.py','tools/record_middle_checkpoint.py'})
    logs={p.stem:p for p in (BASE/'p3-deep-middle-integrated').glob('*.log')}
    assert len(logs)==67
    logs['test_buildgen_band_frame']=BASE/'p3-deep-middle-band-frame-fixed/test_buildgen_band_frame.log'
    counts={k:successful(p) for k,p in logs.items()}
    stream=BASE/'p3-deep-middle-streaming.log'
    python_streaming=successful(stream)
    lua=re.findall(r'(test_\w+): (\d+) passed, (\d+) failed',stream.read_text(encoding='utf-8'))
    assert len(lua)==15 and all(int(f)==0 for _,_,f in lua)
    review_dir=BASE/'p3-deep-middle-review-r2'
    review=json.loads((review_dir/'results.json').read_text(encoding='utf-8'))
    assert len(review['fixtures'])==26
    for path,sha in review['source_hashes'].items():assert digest(ROOT/path)==sha, path
    for row in review['fixtures']:
        for tier,data in row['representations'].items():
            assert digest(review_dir/(row['family']+'-'+tier+'.cdae'))==data['sha256']
    destination=BASE/'p3-deep-middle-checkpoint';destination.mkdir(exist_ok=False)
    records=[]
    for name in sources:
        source=ROOT/name;target=destination/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=digest(source)))
    report=dict(scope='source continuation; not packaged; no new original checklist row completed',
                base_playtest='playtest-r5/checkpoint',sources=records,
                source_sha256=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                python_tests=sum(counts.values()),python_modules=counts,
                python_streaming=python_streaming,lua_assertions=sum(int(n) for _,n,_ in lua),
                lua_suites={k:int(n) for k,n,_ in lua},
                logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in [*logs.values(),stream]],
                review=dict(path=review_dir.relative_to(ROOT).as_posix(),sha256=digest(review_dir/'results.json'),
                            preview_sha256=digest(review_dir/'comparison.png'),families=26,
                            deep_openings=sum(r['deep_openings'] for r in review['fixtures'])),
                invocation_correction='initial band-frame module failed to load without server PYTHONPATH; three actual tests pass with required path; original failed log retained',
                remaining='common accepted-plan reuse across separate distant requests; native transitions, contact, import and memory acceptance')
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    path=BASE/'programme.json';programme=json.loads(path.read_text(encoding='utf-8'))
    programme['in_progress_p3']=dict(checkpoint='p3-deep-middle-checkpoint/manifest.json',status=report['remaining'])
    path.write_text(json.dumps(programme,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('source_sha256','python_tests','python_streaming','lua_assertions')}))


if __name__=='__main__':main()
