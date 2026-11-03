"""Compare staged CPU geometry coverage; excludes map I/O, encoding and native rendering."""
from pathlib import Path
import hashlib
import importlib.util
import json
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import numpy as np
from buildgen import progressive
from test_buildgen_progressive import ProgressiveTests
from test_buildgen_regional_blocks import variants
from buildgen import regional_blocks


def fingerprint(meshes):
    """Triangle multiset including UV, colour and material; independent of batching."""
    records=[]
    for m in meshes:
        for tri,mat in zip(m[2],m[3]):
            records.append(m[0][tri].tobytes()+m[1][tri].tobytes()+m[5][tri].tobytes()+str(m[4][int(mat)]).encode())
    return hashlib.sha256(b''.join(sorted(records))).hexdigest()


def main():
    out=ROOT/'build/roadside-streaming-fixes'
    spec=importlib.util.spec_from_file_location('buildgen._coverage_before',out/'original/server/buildgen/progressive.py')
    before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
    fixtures=[('houses60',ProgressiveTests().items(60)),
              ('regional_blocks12',[(s,0.,0.) for k in list(regional_blocks.catalogue())[:4] for s in variants(k)])]
    report={'scope':__doc__,'fixtures':[]}
    for name,items in fixtures:
        modes={}
        for label,module in [('before',before),('after',progressive)]:
            samples=[]
            for _ in range(3):
                with tempfile.TemporaryDirectory(dir=out/'tmp') as tmp:
                    p=module.Publisher(tmp,'/vfs',None,'a'*32)
                    token=progressive.ACTIVE.set(p);stages={};times={};start=time.perf_counter()
                    def publish(group,stage,meshes,names=None):
                        stages[group]=stage
                        times.setdefault('first_shell_ms',(time.perf_counter()-start)*1000)
                        if len(stages)==p.total and all(v>=1 for v in stages.values()):
                            times.setdefault('all_lite_ms',(time.perf_counter()-start)*1000)
                        if stage==2:times.setdefault('first_detail_ms',(time.perf_counter()-start)*1000)
                    try:
                        with patch.object(p,'publish',side_effect=publish):
                            p.shells(items);meshes,groups=p.build(items)
                        times['total_ms']=(time.perf_counter()-start)*1000
                    finally:progressive.ACTIVE.reset(token)
                samples.append(times)
            modes[label]={'median_ms':{k:statistics.median(r[k] for r in samples) for k in samples[0]},
                          'groups':len(groups),'triangles':sum(len(m[2]) for m in meshes),
                          'geometry_sha256':fingerprint(meshes)}
        assert modes['before']['geometry_sha256']==modes['after']['geometry_sha256'],name
        report['fixtures'].append(dict(fixture=name,**modes))
        print(name,json.dumps(modes),flush=True)
    (out/'coverage-benchmark.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
