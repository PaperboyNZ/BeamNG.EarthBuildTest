"""Offline exact compiled-vertex sharing experiment; never used by live shapes.

Works after the encoder has finalized normals, tangent handedness, UV channels,
colours and material primitives. Candidates receive content-addressed new files.
"""
import argparse,hashlib,json,statistics,struct,sys,time,tracemalloc
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests'),str(ROOT/'tools')]
import cdae
ATTRS=('verts','tverts','tverts2','colors','norms','encodedNorms','tangents')


def rows(mesh):
    n=mesh['verts'][0]
    fields=[k for k in ATTRS if mesh[k][0]]
    if any(mesh[k][0]!=n for k in fields):raise ValueError('nonstatic or inconsistent vertex records')
    return fields,np.concatenate([np.frombuffer(mesh[k][2],np.uint8).reshape(n,mesh[k][1]) for k in fields],axis=1)


def compact(data):
    shape=cdae.decode(data);saved=0
    for mesh in shape['meshes']:
        if mesh['type']==4:continue
        if mesh['numFrames']!=1 or mesh['numMatFrames']!=1:raise ValueError('experiment supports single-frame static shapes only')
        fields,records=rows(mesh);n=len(records)
        original=np.frombuffer(mesh['indices'][2],'<u4')
        if not len(original):continue
        _,first,inverse=np.unique(records.view('V'+str(records.shape[1])).ravel(),return_index=True,return_inverse=True)
        used,first_use=np.unique(inverse[original],return_index=True)
        order=used[np.argsort(first_use,kind='stable')]
        vertices=first[order];remap=np.empty(len(first),np.uint32);remap[order]=np.arange(len(order),dtype=np.uint32)
        indices=remap[inverse[original]]
        np.testing.assert_array_equal(records[vertices][indices],records[original])
        for field in fields:
            _,stride,raw=mesh[field]
            mesh[field]=(len(vertices),stride,np.frombuffer(raw,np.uint8).reshape(n,stride)[vertices].tobytes())
        mesh['indices']=(len(indices),4,indices.astype('<u4',copy=False).tobytes())
        mesh['vertsPerFrame']=len(vertices);saved+=n-len(vertices)
    out=bytearray()
    pack=lambda v:cdae._pack(out,v)
    for name in ('smallestVisibleSize','smallestVisibleDL','radius','tubeRadius','center','bounds'):pack(shape[name])
    for name in cdae.SHAPE_VECTORS:
        for value in shape[name]:pack(value)
    pack(len(shape['names']))
    for name in shape['names']:pack(name)
    pack(len(shape['meshes']))
    for mesh in shape['meshes']:
        pack(mesh['type'])
        if mesh['type']==4:continue
        for name in ('numFrames','numMatFrames','parentMesh','bounds','center','radius'):pack(mesh[name])
        for name in cdae.MESH_VECTORS:
            for value in mesh[name]:pack(value)
        pack(mesh['vertsPerFrame']);pack(mesh['flags'])
    pack(0);pack(len(shape['materials']))
    for material in shape['materials']:
        for name in ('name','flags','reflectanceMap','bumpMap','detailMap','detailScale','reflectionAmount'):pack(material[name])
    header=dict(shape['header'],bodysize=len(out));header=cdae.packb(header)
    return struct.pack('<II',shape['version'],len(header))+header+bytes(out),saved


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--repeats',type=int,default=5)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    from benchmark_representation_boundaries import fixtures
    from test_buildgen_regions import building
    import buildings as b
    from buildgen import freeze_items
    report=dict(scope='Offline full visual generation + native encoding + optional idle-cache vertex rewrite + writes; native import/rendering not measured',
                rollout='disabled: no demonstrated native import/render benefit; no triangles or material submissions removed',fixtures=[])
    for name,spec in [('japan_house',building('jp_temperate')),*fixtures()]:
        items=freeze_items([(spec,0.,0.)]);samples=[]
        for i in range(args.repeats+1):
            start=time.perf_counter();parts=b.build_parts(items,with_lod=True)
            path=args.out/'original.cdae';b.write(str(path),parts[0]);baseline=time.perf_counter()
            data=path.read_bytes();candidate,saved=compact(data)
            identity=hashlib.sha256(candidate).hexdigest();(args.out/(identity+'.cdae')).write_bytes(candidate)
            end=time.perf_counter()
            if i:samples.append(dict(baseline_ms=1000*(baseline-start),rewrite_ms=1000*(end-baseline),total_ms=1000*(end-start)))
        tracemalloc.start();compact(data);peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        row=dict(name=name,original_bytes=len(data),candidate_bytes=len(candidate),removed_vertices=saved,
                 original_identity=hashlib.sha256(data).hexdigest(),candidate_identity=identity,peak_rewrite_bytes=peak,
                 medians={k:statistics.median(s[k] for s in samples) for k in samples[0]},samples=samples)
        report['fixtures'].append(row);print(name,saved,'vertices;',round(100*(1-len(candidate)/len(data)),2),'% bytes;',round(row['medians']['rewrite_ms'],2),'ms rewrite',flush=True)
    report['source_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'server/cdae.py',ROOT/'server/buildings.py')}
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
