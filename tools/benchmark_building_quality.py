"""Offline building quality audit. CPU timings are not native-game FPS."""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'server'), str(ROOT/'server/tests')]
import buildings as b
import cdae
from buildgen import freeze_items
from buildgen.progressive import DETAIL, shell
from test_buildgen_regions import building as house
from test_buildgen_regional_blocks import building as block
from test_buildgen_city import make as city
from test_buildgen_churches import make as church
from test_buildgen_commercial_roofs import fixture as factory
from test_buildgen_visible_landscaping import example as frontage


def fixtures():
    return [('nz_house', lambda: house('nz_temperate')),
            ('regional_block_6', block), ('apartment_49', lambda: block(floors=49)),
            ('office_16', lambda: city()[0]),
            ('glass_tower_80', lambda: city(material='glass', floors=80)[0]),
            ('church', lambda: church()[0]), ('industrial', factory), ('frontage', frontage)]


def digest(mesh):
    if mesh is None:return None
    h=hashlib.sha256()
    for value in mesh[:6]:
        h.update(value.tobytes() if isinstance(value,np.ndarray) else repr(value).encode())
    return h.hexdigest()


def encode(mesh):
    return cdae.encode(mesh[0],mesh[2],uvs=mesh[1],material=mesh[4],tri_materials=mesh[3],colors=mesh[5])


def measure(fn, repeats):
    fn()
    times=[]
    for _ in range(repeats):
        start=time.perf_counter();value=fn();times.append((time.perf_counter()-start)*1000)
    return value, dict(median_ms=statistics.median(times), samples_ms=times)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--repeats',type=int,default=5)
    ap.add_argument('--tiers',nargs='+',default=['full'])
    args=ap.parse_args()
    report=dict(scope='Synthetic warm CPU: fixture planning, freeze, shell, near/lite, collision, in-memory CDAE. No downloads, disk, game imports or GPU. Profile inclusive times overlap.',
                repeats=args.repeats, fixtures=[],sources={})
    for name,make in fixtures():
        spec,planning=measure(make,args.repeats)
        items,freeze=measure(lambda:freeze_items([(spec,0.,0.)]),args.repeats)
        _,shell_time=measure(lambda:shell(items),args.repeats)
        collision,collision_time=measure(lambda:b.collision_mesh(items),args.repeats)
        row=dict(name=name,planning=planning,freeze=freeze,shell=shell_time,collision=collision_time,
                 collision_digest=digest(collision),tiers={})
        for tier in args.tiers:
            token=DETAIL.set(tier)
            try:
                near,near_time=measure(lambda:b.build(items),args.repeats)
                lite,lite_time=measure(lambda:b.build(items,lite=True),args.repeats)
                blob,encoding=measure(lambda:encode(near),args.repeats)
                prof=cProfile.Profile();prof.runcall(b.build,items)
                calls=[]
                for entry in prof.getstats():
                    code=entry.code
                    if isinstance(code,str) or not ('buildgen' in code.co_filename or code.co_filename.endswith('buildings.py')):continue
                    calls.append(dict(file=Path(code.co_filename).name,function=code.co_name,calls=entry.callcount,
                                      self_ms=entry.inlinetime*1000,inclusive_ms=entry.totaltime*1000))
                row['tiers'][tier]=dict(near=near_time,lite=lite_time,encoding=encoding,vertices=len(near[0]),
                    triangles=len(near[2]),material_primitives=len(np.unique(near[3])),bytes=len(blob),digest=digest(near),
                    lite_digest=digest(lite),profile=sorted(calls,key=lambda x:-x['self_ms']))
            finally:DETAIL.reset(token)
        report['fixtures'].append(row)
        print(name, {k:round(v['near']['median_ms'],2) for k,v in row['tiers'].items()},flush=True)
    for path in [ROOT/'server/buildings.py',*sorted((ROOT/'server/buildgen').glob('*.py'))]:
        report['sources'][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
