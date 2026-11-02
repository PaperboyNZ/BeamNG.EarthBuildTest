"""Render every active theme's actual mesh and measure offline generation.

Diagnostic material colours approximate game textures; these are not screenshots.
Photographic research is linked in the catalogue and is not embedded in output.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen import regional_architecture as regional, regional_geography, environments
from buildgen.context import Context
from buildgen.topology import Footprint
from building_preview import raster


def fixture(key, regional_enabled=True, representative=False):
    profile=regional.catalogue()[key];e=profile['example']
    fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
    attrs=dict(_footprint=fp,_context=Context(location=(e['lat'],e['lon']) if regional_enabled else None),
               seed_id='regional-fixture',**{'class':'house','height':8.,'num_floors':2})
    spec=b.plan(np.asarray(fp.outer),attrs)
    if representative:
        preferred_roof=max(profile['roof_shapes'],key=lambda row:row[1])[0]
        preferred_wall=max(profile['facade'],key=lambda row:row[1])[0]
        variants=[row for row in profile.get('roof_variants',[]) if row[0]!='standard' and row[1]>0]
        target=max(variants,key=lambda row:row[1])[0] if preferred_roof!='flat' and variants else 'standard'
        target_roof=('hipped' if target=='mansard' else 'gabled') if target!='standard' else preferred_roof
        fallback=None
        for candidate in range(1024):
            attrs['seed_id']=f'regional-review-{candidate}'
            proposed=b.plan(np.asarray(fp.outer),attrs)
            if proposed.inference.facade.value!=preferred_wall or regional.variation(proposed)!='local_detail':
                continue
            if fallback is None and proposed.roof==preferred_roof:
                fallback=proposed
            if proposed.roof==target_roof and proposed.inference.roof_variant==target:
                spec=proposed;break
        else:
            if fallback is not None: spec=fallback
    spec.gring=np.zeros(len(fp.outer));spec.door=(0,2.3);spec.front=0
    return freeze_items([(spec,0.,0.)])[0]


def signature(mesh):
    h=hashlib.sha256()
    for index in (0,1,2,3,5):h.update(np.asarray(mesh[index]).tobytes())
    h.update(repr(mesh[4]).encode())
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/regional-runtime/preview')
    parser.add_argument('--no-images',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    keys=list(environments.catalogue()['regions'])
    t=time.perf_counter();regional_geography._index();cold=time.perf_counter()-t
    rows={};cells=[]
    try:font=ImageFont.truetype('arial.ttf',16)
    except OSError:font=ImageFont.load_default()
    for index,key in enumerate(keys):
        item=fixture(key,representative=True);spec=item[0]
        mesh=b.build([item]);lite=b.build([item],lite=True);collision=b.collision_mesh([item])
        label=environments.catalogue()['regions'][key]['label']
        rows[key]=dict(name=label,example=regional.catalogue()[key]['example'],
                       theme=spec.inference.selection.environment.region,facade=spec.inference.facade.value,
                       roof=spec.roof,roof_variant=spec.inference.roof_variant,
                       grammar=regional.catalogue()[key].get('massing_grammar'),pitch=spec.pitch,vertices=len(mesh[0]),triangles=len(mesh[2]),
                       lite_vertices=len(lite[0]),collision_vertices=len(collision[0]),
                       near_sha256=signature(mesh),lite_sha256=signature(lite),collision_sha256=signature(collision))
        if not args.no_images:
            cell=Image.new('RGB',(440,340),'#f4f6f7')
            cell.paste(raster(mesh,[('door',2.3,0.,0.,0.,'',2.25,'')],[],440,285,b),(0,45))
            draw=ImageDraw.Draw(cell)
            draw.text((12,7),f'{index+1:02d}. {label}',font=font,fill='#172b3a')
            draw.text((12,27),key,font=font,fill='#526878')
            cells.append(cell)
    times={}
    for enabled in (False,True):
        samples=[]
        for repeat in range(4):
            t=time.perf_counter()
            for key in keys:
                item=fixture(key,enabled)
                b.build([item]);b.build([item],lite=True);b.collision_mesh([item])
            samples.append((time.perf_counter()-t)*1000)
        times['regional' if enabled else 'generic']=dict(samples_ms=samples,median_ms=float(np.median(samples[1:])))
    # Distinct buildings nearby (not 64 repeated cache hits) exercise the index.
    coords=[]
    for key in keys:
        e=regional.catalogue()[key]['example']
        coords.extend((e['lat']+i*.00001,e['lon']+i*.00001) for i in range(32))
    regional_geography.locate.cache_clear();t=time.perf_counter()
    for lat,lon in coords:regional_geography.locate(lat,lon)
    lookup=(time.perf_counter()-t)*1000
    report=dict(schema=1,scope='synthetic offline meshes, not game FPS or material acceptance',
                theme_count=len(rows),unique_near_meshes=len({v['near_sha256'] for v in rows.values()}),
                geography_cold_load_ms=cold*1000,geography_2048_unique_queries_ms=lookup,
                timings=times,fixtures=rows)
    (args.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    if cells:
        for page in range(4):
            sheet=Image.new('RGB',(1760,1400),'#e8edf0')
            ImageDraw.Draw(sheet).text((16,10),'Regional themes — representative detail variants; actual meshes, approximate colours (not game screenshots)',font=font,fill='#243746')
            for i,cell in enumerate(cells[page*16:(page+1)*16]):sheet.paste(cell,((i%4)*440,40+(i//4)*340))
            sheet.save(args.out/f'themes-{page+1}.png')
    print(json.dumps({k:v for k,v in report.items() if k!='fixtures'},indent=2))


if __name__=='__main__':main()
