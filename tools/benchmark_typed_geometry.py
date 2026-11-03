"""Reference parity and complete resolved-worker CPU/memory measurements.

Includes near/lite/collision generation, native shape encoding and file writes.
Map fetch, terrain/access planning and game imports are reported as exclusions.
"""
import argparse,ast,hashlib,json,statistics,sys,time,tracemalloc
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import buildings as b
import cdae
from buildgen import components,freeze_items,regional_architecture,regional_blocks,weathering
from test_buildgen_regions import building as house
from test_buildgen_regional_blocks import building as block,variants


def reference_mesh(path):
    tree=ast.parse(path.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
    namespace=dict(vars(b))
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace['Mesh']


def encode(mesh):
    return cdae.encode(mesh[0],mesh[2],uvs=mesh[1],material=list(mesh[4]),tri_materials=mesh[3],
                       colors=mesh[5],uvs2=weathering.uv(mesh[0],mesh[2]))


def run(items,mesh_type,folder):
    start=time.perf_counter()
    with patch.object(b,'Mesh',mesh_type):
        meshes=(b.build(items),b.build(items,lite=True),b.collision_mesh(items))
    generation=time.perf_counter();payloads=[encode(mesh) for mesh in meshes];encoded=time.perf_counter()
    for i,data in enumerate(payloads):(folder/f'product-{i}.cdae').write_bytes(data)
    end=time.perf_counter()
    return dict(generation_ms=1000*(generation-start),encoding_ms=1000*(encoded-generation),
                write_ms=1000*(end-encoded),total_ms=1000*(end-start)),payloads


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=5);parser.add_argument('--all-regions',action='store_true')
    args=parser.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    source=ROOT/'build/world-architecture-programme/p4-reference/server/buildings.py'
    old,new=reference_mesh(source),b.Mesh
    result=dict(scope='Resolved worker: near/lite/collision, native encoding, publication writes; no map fetching, terrain/access planning, game import, rendering or FPS claim',
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    [source,ROOT/'server/buildings.py',ROOT/'server/buildgen/components.py',ROOT/'server/buildgen/typed_mesh.py']},
                binary_parity_cases=0,fixtures=[])
    specs=([house(k) for k in regional_architecture.catalogue()]+
           [s for k in regional_blocks.catalogue() for s in variants(k)]) if args.all_regions else [house('jp_temperate'),block(),block(floors=49)]
    for spec in specs:
        items=freeze_items([(spec,0.,0.)])
        for lite in (False,True):
            with patch.object(b,'Mesh',old):before=b.build(items,lite=lite)
            after=b.build(items,lite=lite)
            for field in (0,1,2,3,5):np.testing.assert_array_equal(before[field],after[field])
            assert encode(before)==encode(after),'native position/UV/normal/tangent/material/color parity'
            result['binary_parity_cases']+=1
    print('Exact arrays and native bytes:',result['binary_parity_cases'],flush=True)
    dense=freeze_items([(house(('jp_temperate','brazil_coastal','korea','sahel')[i%4],seed='dense-'+str(i)),0.,0.) for i in range(12)])
    for label,items in [('house',freeze_items([(house('nz_temperate'),0.,0.)])),
                        ('screened_japan',freeze_items([(house('jp_temperate'),0.,0.)])),
                        ('tower80',freeze_items([(block(floors=80,facade_material='glass'),0.,0.)])),
                        ('fallback49',freeze_items([(block(floors=49),0.,0.)])),('dense_mixed12',dense)]:
        for cold in (True,False):
            samples=[[],[]]
            for repeat in range(args.repeats+1):
                for index in (repeat%2,1-repeat%2):
                    if cold:components.clear()
                    measured,payloads=run(items,(old,new)[index],args.out.parent)
                    if repeat:samples[index].append(measured)
            peaks=[]
            for typ in (old,new):
                tracemalloc.start();run(items,typ,args.out.parent);peaks.append(tracemalloc.get_traced_memory()[1]);tracemalloc.stop()
            medians=[{key:statistics.median(x[key] for x in arm) for key in arm[0]} for arm in samples]
            result['fixtures'].append(dict(name=label,cold_templates=cold,before=medians[0],after=medians[1],
                    before_peak_bytes=peaks[0],after_peak_bytes=peaks[1],samples=samples))
            print(label,'cold' if cold else 'warm',round(medians[0]['total_ms'],2),'->',round(medians[1]['total_ms'],2),'ms',flush=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
