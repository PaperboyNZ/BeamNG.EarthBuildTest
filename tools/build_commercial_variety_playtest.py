"""Assemble an isolated r6-based playtest containing only the variety changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parent
BASE=WORKSPACE/'BeamNG.Earth-v2-world-architecture-r6-20261102'
NAME='BeamNG.Earth-v2-commercial-variety-r7-20261102'
TARGET=WORKSPACE/NAME
CHANGES=(
    'server/buildgen/presets.py','server/buildgen/inference.py','server/buildgen/plan.py',
    'server/buildgen/commercial.py','server/buildgen/facades.py','server/buildgen/commercial_forms.py',
    'server/buildgen/catalog/commercial_forms.json','server/buildgen/catalog/environments.json',
    'server/tests/test_buildgen_commercial_forms.py','server/tests/test_buildgen_presets.py',
    'tools/commercial_variety_preview.py','docs/COMMERCIAL_SPARSE_DATA_VARIETY.md')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble():
    TARGET.mkdir(exist_ok=False)
    inventory=json.loads((BASE/'SOURCE_MANIFEST.json').read_text())
    for name,expected in inventory.items():
        if name=='BUILD_ID.json' or name.startswith('validation/'):continue
        source=BASE/name
        assert sha(source)==expected, f'Base changed: {name}'
        destination=TARGET/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    for name in CHANGES:
        destination=TARGET/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,destination)
    launcher=(BASE/'test_v2.bat').read_text().replace(BASE.name,NAME)
    (TARGET/'test_v2.bat').write_text(launcher,encoding='utf-8')
    (TARGET/'PLAYTEST.md').write_text(
        '# Commercial and industrial variety r7\n\n'
        'Run `test_v2.bat`, then start BeamNG. Close the previous Earth server and '
        'restart BeamNG when switching builds. Schema 24 invalidates older generated building plans.\n\n'
        'Includes the r6 architecture/streaming work and eight sparse-data commercial/industrial '
        'compositions. Footprint geometry, storeys, wall height and observed neighbours weight the '
        'choices; detailed building tags and zoning are optional. Specific business uses retain '
        'their dedicated paths. See `docs/COMMERCIAL_SPARSE_DATA_VARIETY.md`.\n\n'
        'Compare broad industrial/commercial districts and untagged buildings with surrounding '
        'land-use evidence. Look for multi-bay halls, clerestories, windowed workhalls, industrial '
        'window grids, glazed pavilions, display halls, pier frontages and ribbon blocks. '
        'Check narrow, sloping, irregular and attached buildings while approaching and retreating.\n\n'
        'Native appearance and performance acceptance remain pending. Offline tests and rendered '
        'mesh previews do not establish game acceptance. Shared-court pilots remain off by default.\n',encoding='utf-8')
    # Reuse installed dependencies locally; virtualenv is excluded from archives.
    if (BASE/'.venv').is_dir():
        shutil.copytree(BASE/'.venv',TARGET/'.venv',ignore=shutil.ignore_patterns('__pycache__'))
    print(TARGET)


def finalize():
    logs=ROOT/'build/commercial-variety/package-tests'
    paths=sorted(logs.glob('test_*.log'))
    assert paths, 'Missing package test results'
    counts={}
    for p in paths:
        text=p.read_text(encoding='utf-8')
        found=re.search(r'Ran (\d+) tests?.*?\n\s*OK(?:\s*\([^\n]+\))?\s*\n',text,re.S)
        assert found, f'Failed test module: {p}'
        counts[p.stem]=int(found[1])
    validation=TARGET/'validation'
    validation.mkdir(exist_ok=True)
    for name in ('preview.png','coverage.json'):
        shutil.copyfile(WORKSPACE/'artifacts/commercial-variety-r7'/name,validation/name)
    for path in paths:
        out=validation/'tests'/path.name
        out.parent.mkdir(exist_ok=True)
        shutil.copyfile(path,out)
    sys.path.insert(0,str(TARGET/'server'))
    import codefiles
    h=hashlib.sha256()
    for name in codefiles.source_files(TARGET/'server'):
        h.update(name.encode()+b'\0'+(TARGET/'server'/name).read_bytes())
    status=dict(build=NAME,base_build=BASE.name,building_schema=24,source_sha256=h.hexdigest(),
        changes=list(CHANGES),tests=dict(modules=len(counts),tests=sum(counts.values()),module_counts=counts,
        scope='Offline tests against the assembled r7 package; native engine not included'),
        native_game_acceptance='pending; offline synthetic validation only',
        shared_court_pilot='bundled; disabled in normal launcher',facade_baking='disabled',
        exact_vertex_sharing='disabled',variety=dict(commercial_families=4,industrial_families=4,
        population_seeds_per_use=128,coverage='validation/coverage.json'))
    (TARGET/'BUILD_ID.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    (validation/'status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    # Inventory every archive payload, including the native modules retained from r6.
    inventory={}
    for path in sorted(TARGET.rglob('*')):
        rel=path.relative_to(TARGET)
        if not path.is_file() or any(p in ('.venv','__pycache__') for p in rel.parts) or path.suffix=='.pyc':continue
        if rel.as_posix()=='SOURCE_MANIFEST.json':continue
        inventory[rel.as_posix()]=sha(path)
    (TARGET/'SOURCE_MANIFEST.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    archive=WORKSPACE/(NAME+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in [*inventory,'SOURCE_MANIFEST.json']:z.write(TARGET/name,NAME+'/'+name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in inventory.items():assert hashlib.sha256(z.read(NAME+'/'+name)).hexdigest()==digest,name
    archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n',encoding='ascii')
    result=dict(status,folder=NAME,archive=archive.name,archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        launcher='Play latest buildings.bat',source='BeamNG.EarthBuildTest',manifest_files=len(inventory),archive_inventory='passed')
    (WORKSPACE/'artifacts/commercial-variety-r7/verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (WORKSPACE/'CURRENT_PLAYTEST.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (WORKSPACE/'Play latest buildings.bat').write_text('@echo off\ncall "%~dp0'+NAME+'\\test_v2.bat" %*\n',encoding='utf-8')
    (WORKSPACE/'World tour.bat').write_text('@echo off\ncall "%~dp0'+NAME+'\\World tour.bat" %*\n',encoding='utf-8')
    (WORKSPACE/'START-HERE.md').write_text(
        '# Current private playtest\n\nRun `Play latest buildings.bat`, then start BeamNG. Close the previous '
        'Earth server and restart BeamNG when switching updates. The launcher updates the matching mod.\n\n'
        'Current package: `'+NAME+'` (schema 24). Includes r6 architecture and streaming plus eight '
        'commercial/industrial compositions selected from footprints and observed surroundings without '
        'requiring zoning or detailed tags. See `'+NAME+'/PLAYTEST.md`. Native game acceptance remains pending.\n',encoding='utf-8')
    print(json.dumps(dict(folder=NAME,tests=sum(counts.values()),modules=len(counts),archive_sha256=sha(archive)),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--finalize',action='store_true');a=p.parse_args()
    finalize() if a.finalize else assemble()
