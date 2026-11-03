"""Offline roof contact sheet and bounded geometry/CPU report; no FPS claims."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'server'), str(ROOT/'server/tests')]
import buildings as b
from buildgen import commercial_roofs as cr, freeze_items
from buildgen.topology import Footprint
from test_buildgen_commercial_roofs import fixture
from building_preview import raster


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    cases=[('Flat / service plant','flat','hvac'),('Shallow gable / rooflights','standard','rooflight'),
           ('Mono-pitch / solar','shed','solar'),('Offset ridge / rooflights','saltbox','rooflight'),
           ('Faceted barrel / rooflights','industrial_barrel','rooflight'),('Courtyard / service plant','flat','hvac')]
    canvas=Image.new('RGB',(1200,1000),'#e8edf0');draw=ImageDraw.Draw(canvas)
    draw.text((14,12),'Industrial / commercial roofs - synthetic geometry, approximate materials (not BeamNG)',fill='#203040')
    rows=[]
    for i,(label,form,wanted) in enumerate(cases):
        fp=Footprint(((0,0),(60,0),(60,40),(0,40)),(((20,10),(20,30),(40,30),(40,10)),)) if i==5 else None
        for seed in range(100):
            spec=fixture(form,seed_id=str(seed),fp=fp)
            if any(d.kind==wanted for d in cr.plan(spec)):break
        spec.gring=np.zeros(len(spec.ring))
        mesh=b.build([(spec,0.,0.)]);details=b.Mesh();cr.draw(details,spec,spec.height,b._Looks(spec.seed))
        x,y=(i%2)*600,40+(i//2)*320
        canvas.paste(raster(mesh,[],[],600,275,b,tight=True,camera=[1.35,-2.,1.6]),(x,y))
        draw.text((x+14,y+278),label,fill='#203040')
        draw.text((x+14,y+296),f'{len(cr.plan(spec))} roof details / {len(details.arrays()[2])} detail triangles / rise {spec.inference.roof_rise:.2f} m',fill='#203040')
        rows.append(dict(label=label,seed=seed,details=len(cr.plan(spec)),detail_triangles=len(details.arrays()[2]),rise=spec.inference.roof_rise))
    canvas.save(args.out/'roof-variety.png')
    # Isolate the feature against the previous fallback and clutter path.
    # Alternate order, discard one warmup, and report per-building CPU time.
    modes={}
    for enabled in (False,True):
        with ExitStack() as stack:
            if not enabled:
                stack.enter_context(patch.object(cr,'options',return_value=()))
                stack.enter_context(patch.object(cr,'eligible',return_value=False))
            start=time.perf_counter()
            items=freeze_items([(fixture(seed_id=str(i)),0.,0.) for i in range(40)])
            planning=(time.perf_counter()-start)*1000/len(items)
        modes[enabled]=dict(items=items,planning_ms=planning,timings={False:[],True:[]},triangles={})
    for run in range(6):
        for enabled in ((False,True) if run%2 else (True,False)):
            data=modes[enabled]
            with ExitStack() as stack:
                if not enabled:stack.enter_context(patch.object(cr,'eligible',return_value=False))
                for lite in (False,True):
                    start=time.perf_counter()
                    meshes=[b.build([item],lite=lite) for item in data['items']]
                    elapsed=(time.perf_counter()-start)*1000/len(meshes)
                    data['triangles'][lite]=sum(len(m[2]) for m in meshes)/len(meshes)
                    if run:data['timings'][lite].append(elapsed)
    report=dict(preview=rows,buildings=40,measured_runs=5,scope='Synthetic CPU only; warm geometry caches, no game FPS or streaming acceptance',modes={})
    for enabled,data in modes.items():
        report['modes']['updated' if enabled else 'prior_fallback']=dict(planning_ms_per_building=data['planning_ms'],
            **{name:dict(median_ms_per_building=statistics.median(data['timings'][lite]),triangles_per_building=data['triangles'][lite])
               for lite,name in ((False,'near'),(True,'middle'))})
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['modes'],indent=2))


if __name__=='__main__':main()
