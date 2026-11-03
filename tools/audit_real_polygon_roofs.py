"""Compile nearest cached real buildings with downloads and access work excluded."""
import argparse,hashlib,json,sys,time
from pathlib import Path
from collections import Counter
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
import buildings as b,geodesy,mapcells,mapgeom
from buildgen import ingest,roof_edges,freeze_items


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    result=dict(scope='Cached real source geometry compilation; ground fixed at zero; road/access planning, source downloads and native rendering excluded',places=[],errors=[])
    for label,lat,lon in [('Auckland',-36.91493,174.9094),('Luganville',-15.5132,167.1666)]:
        key=mapcells.cell_of(lat,lon)
        path=Path.home()/'.cache/beamng-earth/mapdata/v2/overture/2026-09-23.1/buildings'/str(key.z)/str(key.x)/(str(key.y)+'.npz')
        with np.load(path,allow_pickle=False) as z:features=mapgeom.Features.from_arrays('buildings',dict(z),'')
        frame=geodesy.EnuFrame(lat,lon,0.);candidates=[];counts=Counter();cost=[]
        for i in range(len(features)):
            for part in features.parts(i):
                if not part:continue
                try:fp=ingest.project(features,frame,part)
                except ValueError:continue
                candidates.append((float(np.linalg.norm(np.mean(fp.outer,axis=0))),i,fp))
        for ordinal,(_,i,fp) in enumerate(sorted(candidates,key=lambda row:row[0])[:250]):
            try:
                attrs={n:v[i] for n,v in features.attrs.items() if n in b.ATTRIBUTE_FIELDS}
                attrs.update(seed_id=str(features.ids[i]),_footprint=fp,ml=str(features.attrs['src_dataset'][i])!='OpenStreetMap')
                spec=b.plan(np.asarray(fp.outer),attrs,lat=lat,lon=lon)
                if spec.roof=='flat' or spec.inference is None:counts['flat_or_special']+=1;continue
                start=time.perf_counter();items=freeze_items([(spec,0.,0.)])
                for lite in (False,True):
                    mesh=b.build(items,lite=lite)
                    assert mesh is not None and np.isfinite(mesh[0]).all() and np.isfinite(mesh[1]).all()
                    assert int(mesh[2].max())<len(mesh[0])
                collision=b.collision_mesh(items)
                assert np.isfinite(collision[0]).all()
                roof=roof_edges.for_spec(spec)
                domain=unary_union([Polygon([v[:2] for v in tri]) for tri in roof.triangles])
                outside=domain.difference(spec.footprint.shape()).area
                counts['compiled_pitched']+=1;counts['projecting_eaves']+=int(outside>1e-6)
                for hole in fp.holes:
                    assert domain.intersection(Polygon(hole)).area<1e-6,'roof covered source courtyard'
                cost.append(1000*(time.perf_counter()-start))
                if outside<=1e-6:counts['diagnosed_flush']+=int('roof_outline_narrow_flush_fallback' in spec.diagnostics)
            except Exception as ex:
                result['errors'].append(dict(place=label,source_id=str(features.ids[i]),error=repr(ex),outer=fp.outer,holes=fp.holes))
            if ordinal and ordinal%50==0:print(label,ordinal,'compiled',flush=True)
        result['places'].append(dict(place=label,source_hash=hashlib.sha256(path.read_bytes()).hexdigest(),counts=dict(counts),
                                    compile_ms_p50=float(np.median(cost)),compile_ms_p95=float(np.percentile(cost,95)),compile_ms_max=max(cost)))
        print(label,dict(counts),flush=True)
    result['sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (ROOT/'server/buildgen/roof_edges.py',ROOT/'server/buildgen/roof_domains.py',ROOT/'server/buildgen/regional_roofs.py',Path(__file__))}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n')
    if result['errors']:raise SystemExit(str(len(result['errors']))+' real-source geometry failures')


if __name__=='__main__':main()
