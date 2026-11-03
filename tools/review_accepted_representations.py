"""Production close/middle/distant meshes from identical immutable source plans."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
from building_preview import raster
from test_buildgen_residential_structures import building
import buildings as b
from buildgen import residential
from buildgen.topology import Footprint


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    court=Footprint(((0.,0.),(18.,0.),(18.,16.),(0.,16.)),
                    (((5.,5.),(5.,11.),(13.,11.),(13.,5.)),))
    brazil=next(region for region,choices in residential.catalogue()['regions'].items()
                if any(family=='brazil_cobogo' for family,_ in choices))
    cases=[('jp_temperate','japanese_engawa','cross_gable',None),
           ('korea','korean_maru','flared_hip',None),
           ('sahel','sahel_compound','flat',court),
           (brazil,'brazil_cobogo','hipped',None)]
    canvas=Image.new('RGB',(1500,50+len(cases)*380),'#e8edf0');draw=ImageDraw.Draw(canvas)
    for column,label in enumerate(('Close: retained construction','Middle: major depth and facade pattern','Distant: roof/volume silhouette')):
        draw.text((column*500+12,12),label,fill='#172b3a')
    draw.text((12,31),'Same frozen plan per row. Offline geometry render; skirts clipped at flat ground only for the preview.',fill='#43515c')
    rows=[]
    for row,(region,family,roof,fp) in enumerate(cases):
        recipe=dict(residential.catalogue()['families'][family])
        forced=roof in ('cross_gable','flared_hip')
        if forced:recipe['roof_variants']=[[roof,1]]
        values=dict(height=9.,roof_height=2.5 if roof!='flat' else 0.,roof_shape=None if forced else roof)
        if fp is not None:values['fp']=fp
        with patch.dict(residential.catalogue()['families'],{family:recipe}):
            for candidate in range(80 if forced else 1):
                spec,items,close,middle,collision=building(region,family,
                    seed_id=family+'-representation-'+str(candidate),**values)
                if not forced or spec.roof!='flat' and spec.inference.roof_variant==roof:break
            assert not forced or spec.roof!='flat' and spec.inference.roof_variant==roof
            distant=b._sky_mesh(items)
        meshes={};physical=hashlib.sha256(collision[0].tobytes()+collision[2].tobytes()).hexdigest()
        for column,(label,mesh) in enumerate((('close',close),('middle',middle),('distant',distant))):
            path=args.out/(family+'-'+label+'.cdae');b.write(str(path),mesh)
            position=mesh[0].copy();position[:,2]=np.maximum(0.,position[:,2])
            x,y=column*500,50+row*380
            canvas.paste(raster((position,*mesh[1:]),[],[],500,335,b,tight=True,camera=(1.35,-2.,1.1)),(x,y))
            draw.text((x+12,y+339),family+f' / {len(mesh[0])} vertices',fill='#172b3a')
            meshes[label]=dict(vertices=len(mesh[0]),triangles=len(mesh[2]),materials=len(np.unique(mesh[3])),
                               bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        assert physical==hashlib.sha256(b.collision_mesh(items)[0].tobytes()+b.collision_mesh(items)[2].tobytes()).hexdigest()
        rows.append(dict(region=region,family=family,source_area=items[0][0].footprint.area,
                         source_holes=len(items[0][0].footprint.holes),roof=spec.roof,roof_variant=spec.inference.roof_variant,
                         forced_supported_inferred_roof=forced,physical_sha256=physical,representations=meshes))
    canvas.save(args.out/'representations.png')
    sources=['server/buildgen/distant.py','server/buildgen/facades.py','server/buildgen/geometry.py',
             'server/buildgen/residential.py',Path(__file__).relative_to(ROOT).as_posix()]
    report=dict(scope='Synthetic production compilers from identical frozen plans; not native texture/night/transition acceptance',
                source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},fixtures=rows)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(args.out/'representations.png')


if __name__=='__main__':main()
