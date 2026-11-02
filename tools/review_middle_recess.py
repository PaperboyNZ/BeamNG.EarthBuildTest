"""Inspect production middle geometry against the previous flattened variant."""
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
import buildings as b
from buildgen import facades,residential
from test_buildgen_residential_structures import building
from building_preview import raster


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    rows=[];seen=set();sheet=[]
    for region,choices in residential.catalogue()['regions'].items():
        for family,_ in choices:
            if family in seen:continue
            seen.add(family)
            spec,items,near,middle,col=building(region,family,roof_shape='flat')
            with patch.object(facades,'MIDDLE_RECESS_M',float('inf')):
                previous=b.build(items,lite=True)
            # Independent representations use this exact accepted immutable plan.
            sky=b._sky_mesh(items)
            for k in (0,1,2,3,5):np.testing.assert_array_equal(col[k],b.collision_mesh(items)[k])
            shapes={}
            for label,mesh in (('close',near),('previous_middle',previous),('middle',middle),('distant',sky)):
                path=args.out/(family+'-'+label+'.cdae');b.write(str(path),mesh)
                shapes[label]=dict(vertices=len(mesh[0]),triangles=len(mesh[2]),materials=len(np.unique(mesh[3])),
                                   bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            deep=sum(not o.assembly and (o.depth or 0)>=facades.MIDDLE_RECESS_M
                     for e in items[0][0].facades.elevations for o in e.openings if o.kind!='door')
            rows.append(dict(region=region,family=family,deep_openings=deep,representations=shapes,
                             collision_sha256=hashlib.sha256(col[0].tobytes()+col[2].tobytes()).hexdigest()))
            if family in ('sahel_compound','maghreb_courtyard','korean_compact','japanese_machiya'):
                sheet.append((family,near,previous,middle))
    cellw,cellh=500,370
    canvas=Image.new('RGB',(1500,len(sheet)*cellh+50),'#e8edf0');draw=ImageDraw.Draw(canvas)
    for i,label in enumerate(('Close','Previous middle: deep slots flattened','Middle: retained depth')):
        draw.text((i*cellw+12,12),label,fill='#172b3a')
    draw.text((12,30),'Flat ground preview: subsurface foundation skirts clipped at z=0; encoded production shapes are complete.',fill='#43515c')
    for row,(family,*meshes) in enumerate(sheet):
        for column,mesh in enumerate(meshes):
            x,y=column*cellw,50+row*cellh
            p=mesh[0].copy();p[:,2]=np.maximum(0.,p[:,2])
            preview=(p,*mesh[1:])
            canvas.paste(raster(preview,[],[],cellw,330,b,tight=True,camera=(1.4,-2.8,.7)),(x,y))
            draw.text((x+12,y+334),family+f' / {len(mesh[0])} vertices',fill='#172b3a')
    canvas.save(args.out/'comparison.png')
    sources=['server/buildgen/facades.py','server/buildgen/regional_openings.py',
             'server/tests/test_buildgen_middle_recess.py',Path(__file__).relative_to(ROOT).as_posix()]
    report=dict(scope='Synthetic production geometry and encoded shapes; native lighting/import/transition review pending',
                threshold_metres=facades.MIDDLE_RECESS_M,
                previous='same accepted plan, deep middle retention disabled; no other representation choice changes',
                source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},fixtures=rows)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(len(rows),'families checked;',sum(r['deep_openings'] for r in rows),'deep openings retained')
    print(args.out/'comparison.png')


if __name__=='__main__':main()
