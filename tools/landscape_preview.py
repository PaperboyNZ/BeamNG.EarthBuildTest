"""Synthetic landscape identity sheet and bounded generation benchmark."""
import argparse
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items,landscaping,sitework
from buildgen.access import Solid
from buildgen.environments import Environment
from buildgen.topology import Footprint
from building_preview import raster

EXAMPLES=(('Temperate timber / lawn and beds','house','wood','','temperate_or_unknown',1),
          ('Masonry / planted frontage','house','brick','','temperate_or_unknown',0),
          ('Urban / concrete and compact beds','house','concrete','city_centre','temperate_or_unknown',7),
          ('Rural / grass and gravel','house','wood','rural','temperate_or_unknown',2),
          ('Warm climate / light paving and beds','house','render','','solar_shading',0),
          ('Cold climate / restrained planting','house','stone','','cold_climate',1),
          ('Supermarket / public frontage','supermarket','concrete','','temperate_or_unknown',0),
          ('Warehouse / utility concrete and gravel','warehouse','metal','','temperate_or_unknown',4),
          ('Trade units / service frontage','workshop','metal','','temperate_or_unknown',5))


def fixture(index,seed=None):
    label,cls,material,env,climate,key=EXAMPLES[index]
    w,d=(14.,10.) if cls=='house' else (38.,20.)
    fp=Footprint(((0,0),(w,0),(w,d),(0,d)))
    s=b.plan(np.asarray(fp.outer),{'class':cls,'num_floors':1,'height':5.5,'_footprint':fp,
        'seed_id':key if seed is None else seed,'roof_shape':'hipped' if cls=='house' else 'flat','facade_material':material})
    selection=replace(s.inference.selection,environment=Environment(env),climate_response=climate)
    s.inference=replace(s.inference,selection=selection)
    s.gring=np.zeros(len(s.ring))
    roads=[(np.array([(-30.,-11.),(w+30.,-11.)]),3.,'residential',False)]
    calls=[]
    def ground(p):calls.append(len(p));return np.zeros(len(p))
    start=time.perf_counter()
    props=b.doors([(s,0.,0.)],roads,0.,0.,[],ground=ground,walks=[],raw_walks=[])
    return s,props,calls,(time.perf_counter()-start)*1000


def coordination_review():
    """Illustrate final reservation priority on an actual fitted frontage.

    The extra paving reservation is deliberately injected as a review fixture,
    not a new generated driveway or evidence of a mapped entrance.
    """
    spec,props,_,_=fixture(1)
    band=spec.access.landscape[0]
    p=np.asarray(band.top)
    centre=p.mean(axis=0)
    tangent=p[1,:2]-p[0,:2];tangent/=np.linalg.norm(tangent)
    normal=np.array([-tangent[1],tangent[0]])
    q=[centre[:2]+tangent*a+normal*c for a,c in ((-.6,-1.),(.6,-1.),(.6,1.),(-.6,1.))]
    reservation=Solid('path',tuple((*map(float,xy),float(centre[2]+.035)) for xy in q),float(centre[2]-.1))
    spec.access=replace(spec.access,solids=(*spec.access.solids,reservation))
    before=copy.deepcopy(spec)
    count=len(spec.access.landscape)
    physical=spec.access.solids
    sitework.coordinate([(spec,0.,0.)])
    assert spec.access.solids==physical
    return before,spec,props,dict(before_patches=count,after_patches=len(spec.access.landscape),
                                  physical_solids_preserved=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT.parent/'artifacts/buildings-landscaping-stage3.png')
    args=parser.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    canvas=Image.new('RGB',(1500,1610),(232,237,240));draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('Arial.ttf',18)
    except OSError:font=ImageFont.load_default(size=18)
    draw.text((20,15),'Procedural frontage landscaping / residential, retail and industry',font=font,fill=(30,45,55))
    draw.text((20,44),'Synthetic identities / approximate materials / bounded terrain fitting / no garden templates',font=font,fill=(60,75,85))
    rows=[]
    for i,example in enumerate(EXAMPLES):
        s,props,calls,_=fixture(i)
        mesh=b.build(freeze_items([(s,0.,0.)]))
        im=raster(mesh,props,[],500,300,b)
        x,y=(i%3)*500,80+(i//3)*385
        canvas.paste(im,(x,y))
        draw.text((x+18,y+310),example[0],font=font,fill=(30,45,55))
        covers={k:sum(p.kind==k for p in s.access.landscape) for k in sorted({p.kind for p in s.access.landscape})}
        draw.text((x+18,y+337),f'{len(s.access.landscape)} groundcover patches / {sum(calls)} terrain samples',font=font,fill=(60,75,85))
        rows.append(dict(label=example[0],identity=landscaping.treatment(s).identity,covers=covers,
                         paved_shoulders=sum(p.kind=='paved_margin' for p in s.access.solids),
                         terrain_points=sum(calls),triangles=len(mesh[2])))
    before,after,props,coordination=coordination_review()
    for index,spec in enumerate((before,after)):
        image=raster(b.build(freeze_items([(spec,0.,0.)])),props,[],500,290,b)
        canvas.paste(image,(index*500,1240))
        draw.text((index*500+18,1535),('Before final reservation check' if index==0 else 'After: conflicting cover removed'),font=font,fill=(30,45,55))
    draw.text((1018,1270),'Final local reservation check',font=font,fill=(30,45,55))
    draw.text((1018,1310),'Injected paved reservation',font=font,fill=(60,75,85))
    draw.text((1018,1340),'All physical solids preserved',font=font,fill=(60,75,85))
    draw.text((1018,1370),f"Cover patches: {coordination['before_patches']} -> {coordination['after_patches']}",font=font,fill=(60,75,85))
    canvas.save(args.out)
    ms=[];points=[]
    for i in range(90):
        s,_,calls,elapsed=fixture(i%9,seed=i)
        ms.append(elapsed);points.append(sum(calls))
    reference=[]
    with patch('sitegen.surfaces.terrain_sampler',side_effect=lambda ground:ground), \
         patch.object(sitework,'coordinate',return_value=()):
        for i in range(90):
            reference.append(fixture(i%9,seed=i)[3])
    comparisons=[]
    for index in range(len(EXAMPLES)):
        with patch('sitegen.surfaces.terrain_sampler',side_effect=lambda ground:ground):
            baseline,_,original,_=fixture(index)
        current,_,shared,_=fixture(index)
        original_mesh=b.build(freeze_items([(baseline,0.,0.)]))
        current_mesh=b.build(freeze_items([(current,0.,0.)]))
        digest=lambda mesh:hashlib.sha256(b''.join(np.ascontiguousarray(a).tobytes() for a in (mesh[0],mesh[2],mesh[3]))).hexdigest()
        assert digest(original_mesh)==digest(current_mesh)
        comparisons.append(dict(label=EXAMPLES[index][0],original_points=sum(original),shared_points=sum(shared),geometry_sha256=digest(current_mesh)))
    stats=dict(status='synthetic_not_game_acceptance',cases=90,access_and_landscape_p50_ms=float(np.percentile(ms,50)),
               access_and_landscape_p95_ms=float(np.percentile(ms,95)),max_points=max(points))
    stats['reference_without_sample_reuse_or_coordination_p50_ms']=float(np.percentile(reference,50))
    stats['reference_without_sample_reuse_or_coordination_p95_ms']=float(np.percentile(reference,95))
    stats['sampling_original_points']=sum(c['original_points'] for c in comparisons)
    stats['sampling_shared_points']=sum(c['shared_points'] for c in comparisons)
    args.out.with_suffix('.json').write_text(json.dumps(dict(**stats,fixtures=rows,sampling=comparisons,coordination=coordination),indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2));print(args.out)


if __name__=='__main__':main()
