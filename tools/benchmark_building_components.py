"""Isolate component reuse from concurrent trim/streaming optimizations."""
from pathlib import Path
import hashlib
import json
import statistics
import sys
import time
import types
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import buildings as b
from buildgen import components,details,facades,freeze_items,regional_architecture,regional_blocks
from test_buildgen_regions import building as house
from test_buildgen_regional_blocks import variants,building as block
from test_buildgen_components import reference_beam


def main():
    original=(ROOT/'build/component-rendering/original/facades.py').read_text()
    current=(ROOT/'server/buildgen/facades.py').read_text()
    begin="            if not lite and arch=='rectangular':"
    end='        for component in components:'
    a,z=original.index(begin),current.index(begin)
    # Restore only the old window-surround/sill emitter in memory. This keeps
    # unrelated current changes, including regional.band_frame, in both arms.
    source=current[:z]+original[a:original.index(end,a)]+current[current.index(end,z):]
    baseline=types.ModuleType('buildgen.component_baseline');baseline.__package__='buildgen'
    sys.modules[baseline.__name__]=baseline
    exec(compile(source,'component_baseline','exec'),baseline.__dict__)
    draw,beam=facades.draw,details.beam
    result={'notes':'Near-only geometry. 11 alternating paired runs after one warmup. '
                    'Cold clears component caches only, not roofs/OS. Other source changes are held equal. '
                    'No downloads, publication or game FPS included.',
            'baseline_facade_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'sources':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                       ('server/buildgen/facades.py','server/buildgen/details.py','server/buildgen/components.py')},
            'benchmarks':[]}
    checked=0;maxp=maxuv=0.
    for spec in [house(k) for k in regional_architecture.catalogue()]+[
            s for k in regional_blocks.catalogue() for s in variants(k)]:
        items=freeze_items([(spec,0.,0.)])
        for lite in (False,True):
            actual=b.build(items,lite=lite)
            with patch.object(facades,'draw',baseline.draw),patch.object(details,'beam',reference_beam):
                expected=b.build(items,lite=lite)
            for field in (0,1):np.testing.assert_allclose(actual[field],expected[field],atol=1e-10,rtol=0)
            for field in (2,3,5):np.testing.assert_array_equal(actual[field],expected[field])
            assert actual[4]==expected[4]
            maxp=max(maxp,float(np.max(np.abs(actual[0]-expected[0]))))
            maxuv=max(maxuv,float(np.max(np.abs(actual[1]-expected[1]))));checked+=1
    result.update(regional_comparisons=checked,position_max_abs_error=maxp,uv_max_abs_error=maxuv,
                  triangles_materials_colors_identical=True)
    print('Regional comparisons',checked,'max position error',maxp,flush=True)
    for name,spec in [('house',house('nz_temperate')),('block6',block()),('fallback49',block(floors=49))]:
        items=freeze_items([(spec,0.,0.)])
        for cold in (True,False):
            samples=[[],[]]
            for repeat in range(12):
                for k in (repeat%2,1-repeat%2):
                    if cold:components.clear()
                    with patch.object(facades,'draw',baseline.draw if k==0 else draw), \
                         patch.object(details,'beam',reference_beam if k==0 else beam):
                        start=time.perf_counter();b.build(items);elapsed=1000*(time.perf_counter()-start)
                    if repeat:samples[k].append(elapsed)
            a,z=map(statistics.median,samples)
            result['benchmarks'].append(dict(name=name,cold=cold,before_ms=a,after_ms=z,
                                             reduction_pct=100*(1-z/a),samples_ms=samples))
            print(name,'cold' if cold else 'warm',round(a,2),'->',round(z,2),flush=True)
    result['cache']=components.cache_info()
    (ROOT/'build/component-rendering/components-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
