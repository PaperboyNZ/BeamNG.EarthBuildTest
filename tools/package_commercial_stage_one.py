"""Package a reviewable source overlay against the preserved stage-one baseline."""
from pathlib import Path
import hashlib,json,tarfile,zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT.parent
BASE='22ac393ffc1484c351a607480802f7a4ac6c12d7'


def sha(value):return hashlib.sha256(value).hexdigest()


def main():
    before={}
    with tarfile.open(STAGE/'baseline.tar') as archive:
        for entry in archive:
            if entry.isfile():before[entry.name]=sha(archive.extractfile(entry).read())
    changed=[]
    for folder in ('server','mod','tools','docs'):
        for path in sorted((ROOT/folder).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.pyo'):continue
            name=path.relative_to(ROOT).as_posix();digest=sha(path.read_bytes())
            if before.get(name)!=digest:
                changed.append(dict(path=name,sha256=digest,baseline_sha256=before.get(name),bytes=path.stat().st_size))
    manifest=dict(baseline_commit=BASE,format='source-overlay-v1',files=changed,
        instructions='Apply source/ paths only to the matching baseline or review/merge the changes. This is not a compiled executable or a live installation.',
        validation='See included test logs and benchmarks; native BeamNG visual acceptance remains unverified.')
    raw=(json.dumps(manifest,indent=2)+'\n').encode()
    (STAGE/'change-manifest.json').write_bytes(raw)
    destination=STAGE/'commercial-properties-stage-one.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('change-manifest.json',raw)
        for row in changed:archive.write(ROOT/row['path'],'source/'+row['path'])
        for name in ('font-preview.png','detail-benchmark.json','programme-benchmark.json','buildgen-tests-final.log'):
            archive.write(STAGE/name,'review/'+name)
        for path in sorted((STAGE/'review').glob('*')):
            if path.suffix in ('.png','.json','.cdae'):archive.write(path,'review/geometry/'+path.name)
    with zipfile.ZipFile(destination) as archive:
        for row in changed:
            if sha(archive.read('source/'+row['path']))!=row['sha256']:raise RuntimeError('overlay checksum mismatch')
        if archive.testzip() is not None:raise RuntimeError('invalid archive')
    print(json.dumps(dict(path=str(destination),changed_files=len(changed),bytes=destination.stat().st_size,
                         sha256=sha(destination.read_bytes())),indent=2))


if __name__=='__main__':main()
