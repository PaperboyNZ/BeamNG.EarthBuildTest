"""Render naturally selected sparse-data compositions and report their coverage."""
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import commercial_forms as forms, freeze_items
from commercial_preview import make
from building_preview import raster


def main():
    out=ROOT.parent/'artifacts/commercial-variety-r7'
    out.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(1800,930),(232,237,240))
    draw=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('Arial.ttf',18)
    except OSError:font=ImageFont.load_default(size=18)
    draw.text((20,15),'Sparse-data architecture: broad commercial / industrial tags, no zoning',font=font,fill=(30,45,55))
    draw.text((20,44),'Same 60 x 25 m footprint, 6 m wall, concrete material. Naturally selected seeds. Offline mesh preview.',font=font,fill=(60,75,85))
    rows=[];populations={}
    for j,(use,ids) in enumerate((('commercial',forms.COMMERCIAL),('industrial',forms.INDUSTRIAL))):
        found={};population=Counter();fronts=Counter()
        for seed in range(128):
            spec,props=make(use,60.,25.,str(seed),height=6.,floors=1,material='concrete')
            pid=spec.inference.selection.preset.id
            population[pid]+=1
            front=next(e for e in spec.facades.elevations if not e.boundary and e.edge==spec.front)
            fronts[str(dict(Counter(o.kind for o in front.openings)))]+=1
            if pid not in found:found[pid]=(spec,props,seed)
        populations[use]=dict(seeds=128,selected=dict(population),fronts=dict(fronts))
        for i,pid in enumerate(ids):
            spec,props,seed=found[pid]
            frozen=freeze_items([(spec,0.,0.)])
            mesh=b.build(frozen)
            x,y=i*450,85+j*410
            image.paste(raster(mesh,props,[],450,315,b),(x,y))
            label=pid.removeprefix('ci_form_').replace('_',' ').title()
            draw.text((x+15,y+317),label,font=font,fill=(30,45,55))
            front=next(e for e in spec.facades.elevations if not e.boundary and e.edge==spec.front)
            count=dict(Counter(o.kind for o in front.openings))
            draw.text((x+15,y+344),f'Seed {seed} / '+', '.join(f'{v} {k}' for k,v in count.items()),font=font,fill=(60,75,85))
            rows.append(dict(preset=pid,seed=seed,layout=asdict(spec.facades),
                             reasons=spec.inference.selection.reasons,vertices=len(mesh[0]),triangles=len(mesh[2])))
    image.save(out/'preview.png')
    report=dict(status='offline_synthetic_meshes_not_native_game_acceptance',populations=populations,fixtures=rows)
    (out/'coverage.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(populations,indent=2))
    print(out/'preview.png')


if __name__=='__main__':main()
