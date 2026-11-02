"""Eligibility-boundary geometry/encoding costs, with an exact-physics control.

Native import/rendering is a separate acceptance gate, never inferred here.
"""
import argparse,hashlib,json,statistics,sys,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import buildings as b
from buildgen import facades,freeze_items
from buildgen.topology import Footprint
from test_buildgen_regional_blocks import building
from test_buildgen_city import make
from test_buildgen_churches import make as church


def fixtures():
    courtyard=Footprint(((0.,0.),(36.,0.),(36.,24.),(0.,24.)),
                        (((10.,8.),(10.,16.),(26.,16.),(26.,8.)),))
    complex_=Footprint(((0.,0.),(36.,0.),(36.,12.),(24.,12.),(24.,24.),(0.,24.)))
    return [('block48',building(floors=48)),('fallback49',building(floors=49)),
            ('courtyard48',building(floors=48,_footprint=courtyard)),
            ('complex49',building(floors=49,_footprint=complex_)),
            ('generic_glass80',building(floors=80,facade_material='glass')),
            ('city_glass80',make(material='glass',floors=80)[0]),('church',church()[0])]


def fingerprint(mesh):
    digest=hashlib.sha256()
    for k in (0,1,2,3,5):digest.update(np.asarray(mesh[k]).tobytes())
    return digest.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--repeats',type=int,default=5)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    result=dict(scope='Frozen plans: near/lite/physical generation, native encoding and writes. Native import and rendering pending.',
                source_hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in
                    (ROOT/'server/buildgen/facades.py',Path(__file__))},fixtures=[])
    for name,spec in fixtures():
        items=freeze_items([(spec,0.,0.)]);layout=items[0][0].facades
        physics=fingerprint(b.collision_mesh(items));row=dict(name=name,openings=sum(len(e.openings) for e in layout.elevations) if layout else None,
            floors=spec.floors,physical_fingerprint=physics,representations={})
        for label,control,lite in [('reference',True,False),('close',False,False),('lite',False,True)]:
            samples=[]
            for repeat in range(args.repeats+1):
                start=time.perf_counter()
                with patch.object(facades,'shallow_openings',return_value=frozenset()) if control else patch.dict({},{}):
                    mesh=b.build(items,lite=lite)
                generated=time.perf_counter();path=args.out/(name+'-'+label+'.cdae');b.write(str(path),mesh)
                encoded=time.perf_counter()
                if repeat:samples.append(dict(generation_ms=1000*(generated-start),encoding_and_write_ms=1000*(encoded-generated),total_ms=1000*(encoded-start)))
            assert physics==fingerprint(b.collision_mesh(items))
            row['representations'][label]=dict(vertices=len(mesh[0]),triangles=len(mesh[2]),
                materials=len(np.unique(mesh[3])),bytes=path.stat().st_size,
                median={k:statistics.median(s[k] for s in samples) for k in samples[0]})
        result['fixtures'].append(row)
        print(name,{k:v['vertices'] for k,v in row['representations'].items()},flush=True)
    (args.out/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
