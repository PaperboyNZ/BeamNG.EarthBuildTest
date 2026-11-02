"""Compare staged compilation against the saved pre-change implementation.

Synthetic geometry only: excludes planning, I/O, engine imports and frame time.
Full-quality mesh arrays, LOD arrays, materials and bounds must remain identical.
"""
import hashlib
import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
os.environ['BNE_BUILDING_GENERATOR']='v2'
import numpy as np
from buildgen import progressive,regional_architecture,regional_blocks
from test_buildgen_progressive import ProgressiveTests
from test_buildgen_regions import building as house
from test_buildgen_regional_blocks import variants
from test_buildgen_band_frame import reference_frame,reference_paint


def fingerprint(value):
    h=hashlib.sha256()
    def add(v):
        if isinstance(v,np.ndarray):h.update(str((v.dtype,v.shape)).encode());h.update(v.tobytes())
        elif isinstance(v,(tuple,list)):
            h.update(b'[')
            for item in v:add(item)
            h.update(b']')
        else:h.update(repr(v).encode())
    add(value);return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=7)
    args=parser.parse_args()
    if args.repeats<1:parser.error('--repeats must be positive')
    os.chdir(ROOT)
    baseline=ROOT/'build/streaming-optimization/original/server/buildgen/progressive.py'
    spec=importlib.util.spec_from_file_location('buildgen._streaming_baseline',baseline)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    fixtures=[('houses25',ProgressiveTests().items(25)),
              ('regional64',[(house(k),0.,0.) for k in regional_architecture.catalogue()]),
              ('blocks24',[(s,0.,0.) for k in list(regional_blocks.catalogue())[:8] for s in variants(k)])]
    report={'scope':__doc__,'repeats':args.repeats,'fixtures':[]}
    for name,items in fixtures:
        samples={m:[] for m in ('before','full','lite')};first={m:[] for m in samples};hashes={}
        for rep in range(args.repeats+1):
            for mode in (('before','full','lite') if rep%2 else ('lite','full','before')):
                state=progressive.DETAIL.set('lite' if mode=='lite' else 'full')
                p=(old if mode=='before' else progressive).Publisher('unused','/vfs',None,'a'*32)
                active=progressive.ACTIVE.set(p)
                first_ready=[];start=time.perf_counter()
                def publish(group,stage,meshes,names=None):
                    if stage==2 and not first_ready:first_ready.append((time.perf_counter()-start)*1000)
                try:
                    with patch.object(p,'publish',side_effect=publish),patch.object(regional_architecture,'band_frame',
                            reference_frame if mode=='before' else regional_architecture.band_frame), \
                         patch.object(regional_blocks,'paint_cells',reference_paint if mode=='before' else regional_blocks.paint_cells):
                        meshes,mapping=p.build(items)
                    elapsed=(time.perf_counter()-start)*1000
                finally:progressive.ACTIVE.reset(active);progressive.DETAIL.reset(state)
                hashes[mode]=fingerprint((meshes,mapping))
                if rep:samples[mode].append(elapsed);first[mode].append(first_ready[0])
        assert hashes['before']==hashes['full'],name+' changed full quality geometry'
        row={'fixture':name,'full_geometry_identical':True,'full_sha256':hashes['full'],
             'compile_median_ms':{k:statistics.median(v) for k,v in samples.items()},
             'first_final_group_median_ms':{k:statistics.median(v) for k,v in first.items()},'samples_ms':samples}
        report['fixtures'].append(row)
        print(name,json.dumps({k:row[k] for k in ('compile_median_ms','first_final_group_median_ms')}),flush=True)
    path=ROOT/'build/streaming-optimization/benchmark.json'
    path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
