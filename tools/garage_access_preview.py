"""Synthetic garage entry review: actual mesh and ground-floor cutaway, offline."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen.topology import Footprint
from buildgen.garages import circulation
from building_preview import raster


def fixture(sidewalk=False,slope=0.):
    fp=Footprint(((0,0),(60,0),(60,40),(0,40)))
    spec=b.plan(np.asarray(fp.outer),{'class':'parking','height':9.,'num_floors':3,
                                     'seed_id':'garage-review','_footprint':fp})
    ground=lambda p:-slope*p[:,1]
    items=[(spec,-slope*40,0.)]
    roads=[(np.array([[-50.,-12.],[120.,-12.]]),4.,'residential',False)]
    walks=[]
    if sidewalk:
        walks=[dict(pts=np.array([[-50.,-6.75,slope*8],[120.,-6.75,slope*8]]),side=1,w=2.5,caps=(True,True))]
    start=time.perf_counter()
    drives=b.garage_drives(items,roads,0,0,ground=ground,walks=walks)
    resolved=time.perf_counter()
    frozen=freeze_items(items)
    mesh=b.build(frozen);lite=b.build(frozen,lite=True);collision=b.collision_mesh(frozen)
    compiled=time.perf_counter()
    return spec,mesh,walks,ground,dict(status=spec.garage_access.status,diagnostics=spec.garage_access.diagnostics,
        portal=spec.garage_access.portal,terrain_points=spec.garage_access.terrain_points,
        access_ms=(resolved-start)*1000,near_lite_collision_ms=(compiled-resolved)*1000,
        vertices=len(mesh[0]),triangles=len(mesh[2]),drive_records=len(drives),
        near_lite_collision_equal=bool(np.array_equal(mesh[0],lite[0]) and np.array_equal(mesh[0],collision[0])))


def route_map(spec):
    image=Image.new('RGB',(720,295),(232,237,240));draw=ImageDraw.Draw(image)
    def project(points):return [(190+float(x)*5,245-float(y)*5) for x,y in points]
    draw.polygon(project(spec.ring),fill=(177,181,179),outline=(65,75,80))
    plan=b.deck_plan(spec,-.8,0.)
    well,turns=circulation(plan)
    draw.polygon(project(well.exterior.coords),fill=(225,201,153))
    for turn in turns:
        for p in getattr(turn,'geoms',(turn,)):
            draw.polygon(project(p.exterior.coords),fill=(137,194,178))
    access=spec.garage_access
    for solid in access.surfaces:
        draw.polygon(project([p[:2] for p in solid.top]),fill=(130,145,150))
    draw.line(project(access.route),fill=(20,91,190),width=4)
    for hole in spec.footprint.holes:draw.polygon(project(hole),fill=(232,237,240))
    draw.text((18,10),'Blue: accepted car route  /  Amber: ramp well  /  Green: full-body turns',
              fill=(30,45,55),font=ImageFont.load_default(size=15))
    draw.text((190,275),'Road contact / shared entrance and exit',fill=(30,45,55),font=ImageFont.load_default(size=15))
    return image


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'build/garage-access/review.png')
    args=ap.parse_args()
    canvas=Image.new('RGB',(1440,1120),(232,237,240));d=ImageDraw.Draw(canvas)
    font=ImageFont.load_default(size=18)
    d.text((20,15),'Garage road-access repair / synthetic geometry / no in-game driving validation',font=font,fill=(30,45,55))
    d.text((20,42),'Left: complete mesh. Right: accepted ground route and turning reservations.',font=font,fill=(30,45,55))
    records=[]
    for i,(label,walk,slope) in enumerate((('Level road',False,0.),('Dropped curb and footpath',True,0.),('Sloping approach',False,.02))):
        spec,mesh,walks,ground,record=fixture(walk,slope)
        # Existing sidewalk meshes share the accepted crossing interval/profile.
        if walks:
            import sidewalks
            builder=sidewalks.Builder((0,0,0))
            for wk in walks:
                curb,out=sidewalks.run_geometry(wk['pts'],wk['side'],wk['w'])
                builder.add_run(curb,out,wk['w'],driveways=wk.get('driveways',()))
            p,t,uv,mid=builder.arrays()
            # Restrict the review strip; long road runs otherwise dwarf the garage.
            keep=(p[t,:,][...,0].min(1)>-10)&(p[t,:,][...,0].max(1)<70)
            indices,inverse=np.unique(t[keep],return_inverse=True)
            sm=(p[indices],uv[indices],inverse.reshape(-1,3),np.zeros(int(keep.sum()),np.int32),
                b.MATERIALS,np.full((len(indices),4),190,np.uint8))
            mesh=b._concat([mesh,sm])
        y=90+i*340
        canvas.paste(raster(mesh,[],[],720,295,b,ground=ground),(0,y))
        canvas.paste(route_map(spec),(720,y))
        d.text((20,y+298),label+' / '+record['status'],font=font,fill=(30,45,55))
        records.append(dict(label=label,**record))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(args.out)
    result=dict(status='synthetic_not_game_acceptance',fixtures=records,
                limitations=['Vehicle clearances tested offline; BeamNG handling/tyre contact unverified.',
                             'Cross-tile approaches deferred; curved/narrow footpaths and rough terrain rejected.',
                             'Timings are one synthetic pass, not release performance measurements.'])
    args.out.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
