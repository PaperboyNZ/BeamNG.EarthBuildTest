"""All 192 actual runtime block meshes, plus bounded geometry/performance report."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen import regional_blocks as blocks, environments
from buildgen.context import Context
from buildgen.topology import Footprint
from buildgen.zones import Zone
from building_preview import raster


def fixtures(theme):
    fp=Footprint(((0.,0.),(36.,0.),(36.,24.),(0.,24.)))
    zone=Zone('block-preview','v1','test','R','statutory',('residential',),1.,region=theme)
    found={}
    for i in range(64):
        attrs=dict(_footprint=fp,_context=Context(zones=(zone,)),seed_id=f'block-variant-{i}',
                   **{'class':'apartments','height':18.,'num_floors':6,'roof_shape':'flat'})
        spec=b.plan(np.asarray(fp.outer),attrs)
        spec.gring=np.zeros(len(spec.ring));spec.front=0;spec.door=(0,5.1)
        profile=blocks.profile(spec)
        found.setdefault(profile['id'],spec)
        if len(found)==3:return [found[p['id']] for p in blocks.catalogue()[theme]]
    raise ValueError('Could not exercise all three variants: '+theme)


def fingerprint(mesh):
    h=hashlib.sha256()
    for i in (0,1,2,3,5):h.update(np.asarray(mesh[i]).tobytes())
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/regional-blocks/preview')
    parser.add_argument('--no-images',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    try:font=ImageFont.truetype('arial.ttf',16);small=ImageFont.truetype('arial.ttf',13)
    except OSError:font=small=ImageFont.load_default()
    records={};all_specs=[];featured=[];sheet=None
    for index,theme in enumerate(blocks.catalogue()):
        if not args.no_images and index%8==0:
            sheet=Image.new('RGB',(1320,8*340+60),'#edf1ee')
            ImageDraw.Draw(sheet).text((18,16),'Regional blocks | actual generated meshes, approximate materials | 36 x 24 m, six storeys',font=font,fill='#243b33')
        row=Image.new('RGB',(1320,340),'#edf1ee') if not args.no_images else None
        if row:
            ImageDraw.Draw(row).text((14,6),f"{index+1:02d}. {environments.catalogue()['regions'][theme]['label']}",font=font,fill='#243b33')
        for option,spec in enumerate(fixtures(theme)):
            p=blocks.profile(spec);all_specs.append(spec)
            item=freeze_items([(spec,0.,0.)])[0]
            start=time.perf_counter();near=b.build([item]);lite=b.build([item],lite=True)
            elapsed=(time.perf_counter()-start)*1000
            collision=b.collision_mesh([item])
            openings=[o for e in item[0].facades.elevations for o in e.openings if o.kind!='door']
            area=sum((o.right-o.left)*(o.top-o.bottom) for o in openings)
            records[p['id']]=dict(name=p['name'],theme=theme,grammar=p['grammar'],
                openings=len(openings),glazed_wall_fraction=area/(120*18),
                near_vertices=len(near[0]),near_triangles=len(near[2]),lite_triangles=len(lite[2]),
                near_sha256=fingerprint(near),lite_sha256=fingerprint(lite),collision_sha256=fingerprint(collision),
                build_ms=elapsed)
            if row:
                row.paste(raster(near,[],[],440,255,b),(option*440,55))
                draw=ImageDraw.Draw(row)
                draw.text((option*440+12,32),f"{chr(65+option)}. {p['name']}",font=small,fill='#243b33')
                draw.text((option*440+12,316),f"{len(openings)} opening groups | wall glazing {area/(120*18):.0%}",font=small,fill='#52665c')
        if row:
            sheet.paste(row,(0,60+(index%8)*340))
            if theme in ('nz_temperate','eu_atlantic','brazil_coastal','jp_temperate'):featured.append(row)
            if index%8==7:sheet.save(args.out/f'blocks-{index//8+1:02d}.png')
    if featured:
        overview=Image.new('RGB',(1320,len(featured)*340+40),'#edf1ee')
        ImageDraw.Draw(overview).text((16,10),'Implemented A / B / C variants | actual meshes, approximate material colours; not game screenshots',font=font,fill='#243b33')
        for i,row in enumerate(featured):overview.paste(row,(0,40+i*340))
        overview.save(args.out/'overview.png')
    benchmark={}
    for enabled in (False,True):
        samples=[]
        for repeat in range(3):
            start=time.perf_counter()
            def draw_all():
                for spec in all_specs:
                    items=freeze_items([(spec,0.,0.)]);b.build(items);b.build(items,lite=True)
            if enabled:draw_all()
            else:
                with patch.object(blocks,'profile',return_value=None):draw_all()
            samples.append((time.perf_counter()-start)*1000)
        benchmark['blocks' if enabled else 'previous_generic']=dict(samples_ms=samples,warm_median_ms=float(np.median(samples[1:])))
    report=dict(themes=64,variants=len(records),unique_meshes=len({r['near_sha256'] for r in records.values()}),
        opening_range=[min(r['openings'] for r in records.values()),max(r['openings'] for r in records.values())],
        glazing_fraction_range=[min(r['glazed_wall_fraction'] for r in records.values()),max(r['glazed_wall_fraction'] for r in records.values())],
        grammar_counts=dict(Counter(r['grammar'] for r in records.values())),benchmark=benchmark,fixtures=records,
        scope='Offline synthetic geometry and CPU timings, not game FPS or native visual acceptance')
    (args.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='fixtures'},indent=2))


if __name__=='__main__':main()
