"""Production publication audit, paired optimization check and geometry contact sheet.

This uses synthetic accepted plans and the actual staged CDAE writer. It does
not measure downloads, game imports, GPU frame time or a real driving session.
"""
import argparse
import cProfile
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'server'),str(ROOT/'server/tests')]
os.environ['BNE_BUILDING_GENERATOR']='v2'
from benchmark_building_quality import fixtures,digest
import buildings as b
import geotiles
from buildgen import freeze_items,quality,city
from buildgen import progressive as p
from test_buildgen_progressive import ProgressiveTests
from building_preview import raster


def profile(fn):
    prof=cProfile.Profile();prof.runcall(fn)
    rows=[]
    for entry in prof.getstats():
        code=entry.code
        if isinstance(code,str):continue
        try:name=Path(code.co_filename).relative_to(ROOT).as_posix()
        except ValueError:continue
        rows.append(dict(file=name,function=code.co_name,calls=entry.callcount,
                         self_ms=entry.inlinetime*1000,inclusive_ms=entry.totaltime*1000))
    return sorted(rows,key=lambda row:-row['self_ms'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--baseline-city',type=Path)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    report=dict(scope=__doc__,stages=[],planning_profiles={},paired_city=[])
    # Attribute fixture planning, layout freezing and collision separately from
    # visual compilation. Inclusive nested timers must never be summed.
    for name,make in fixtures():
        spec=make();items=freeze_items([(spec,0.,0.)])
        report['planning_profiles'][name]=dict(planning=profile(make),
            freezing=profile(lambda:freeze_items([(spec,0.,0.)])),
            collision=profile(lambda:b.collision_mesh(items)))
    items=ProgressiveTests().items(24);tile=geotiles.geobox(100,100)
    for name in quality.NAMES:
        runs=[]
        for repeat in range(3):
            with tempfile.TemporaryDirectory(dir=args.output) as folder:
                token=p.DETAIL.set(name)
                pub=p.Publisher(folder,'/vfs',tile,'a'*32);active=p.ACTIVE.set(pub)
                events=[];original=pub.publish;start=time.perf_counter()
                def publish(group,stage,meshes,names=None):
                    result=original(group,stage,meshes,names)
                    events.append(dict(group=group,stage=stage,ms=1000*(time.perf_counter()-start),ok=result))
                    return result
                try:
                    with patch.object(pub,'publish',side_effect=publish):
                        pub.shells(items);meshes,groups=pub.build(items)
                    elapsed=1000*(time.perf_counter()-start)
                    assert events and all(e['ok'] for e in events),'publication failed'
                    paths=list(Path(folder).rglob('*.cdae'))
                    runs.append(dict(total_ms=elapsed,first_shell_ms=next(e['ms'] for e in events if e['stage']==0),
                        first_final_ms=next(e['ms'] for e in events if e['stage']==2),
                        bytes=sum(path.stat().st_size for path in paths),publications=len(events),groups=len(groups),
                        chunks=len(meshes),near_vertices=sum(len(m[0]) for m in meshes),
                        lod_vertices=sum(len(m[6][0]) for m in meshes if len(m)>6 and m[6] is not None)))
                finally:p.ACTIVE.reset(active);p.DETAIL.reset(token)
        row=dict(tier=name,medians={k:statistics.median(r[k] for r in runs) for k in runs[0]},runs=runs)
        report['stages'].append(row)
        print(name,'staged total ms',round(row['medians']['total_ms'],2),flush=True)
    if args.baseline_city:
        module_name='buildgen._quality_original_city'
        spec=importlib.util.spec_from_file_location(module_name,args.baseline_city)
        original_city=importlib.util.module_from_spec(spec);sys.modules[module_name]=original_city;spec.loader.exec_module(original_city)
        current=city.draw
        for name,make in fixtures():
            if not name.startswith(('office','glass')):continue
            items=freeze_items([(make(),0.,0.)]);samples=[[],[]];digests=[]
            for index,draw in enumerate((original_city.draw,current)):
                with patch.object(city,'draw',draw):digests.append(digest(b.build(items)))
            assert digests[0]==digests[1],'optimization changed geometry'
            for rep in range(12):
                for index in ((0,1) if rep%2 else (1,0)):
                    with patch.object(city,'draw',(original_city.draw,current)[index]):
                        start=time.perf_counter();b.build(items);elapsed=(time.perf_counter()-start)*1000
                    if rep:samples[index].append(elapsed)
            report['paired_city'].append(dict(fixture=name,identical_geometry=True,before_ms=statistics.median(samples[0]),
                                               after_ms=statistics.median(samples[1]),samples_ms=samples))
    # Actual mesh geometry under a fixed camera; no AI images or invented asset
    # appearance. Surface colours are approximate, as in building_preview.py.
    width,height=340,290
    sheet=Image.new('RGB',(width*6,height*3+76),'#18212b');draw=ImageDraw.Draw(sheet)
    draw.text((16,12),'BUILDING QUALITY / generated geometry comparison',fill='white')
    draw.text((16,34),'Same plans, seeds and camera. Approximate materials; not a BeamNG screenshot.',fill='#b4c0cb')
    chosen=[fixtures()[0],fixtures()[1],fixtures()[6]]
    for row,(label,make) in enumerate(chosen):
        items=freeze_items([(make(),0.,0.)])
        for col,name in enumerate(quality.NAMES):
            state=p.DETAIL.set(name)
            try:mesh=b.build(items)
            finally:p.DETAIL.reset(state)
            # Hide the intentional underground skirt in this flat-ground
            # illustration; otherwise the auto-fit makes low tiers look tiny.
            visible=mesh[0].copy();visible[:,2]=np.maximum(0.,visible[:,2])
            im=raster((visible,*mesh[1:]),[],[],width,height-45,b,tight=True,camera=(1.35,-2.,1.2))
            x,y=col*width,76+row*height;sheet.paste(im,(x,y+25))
            draw.text((x+12,y+7),name.replace('_',' ').upper(),fill='white')
            draw.text((x+12,y+height-16),f'{label} / {len(mesh[2]):,} triangles',fill='#b4c0cb')
    sheet.save(args.output/'quality-comparison.png')
    (args.output/'pipeline-audit.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
