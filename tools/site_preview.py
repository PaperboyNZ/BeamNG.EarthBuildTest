"""Synthetic, source-bounded site review; never fetches data or changes a map."""
from dataclasses import asdict, replace
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from commercial_preview import make, ROOT
import buildings as b
from buildgen import freeze_items, site_layout
from buildgen.site_data import Site, Port
from buildgen.topology import Footprint
from building_preview import raster


def fixture(width=60.,variant=0):
    spec,props=make('warehouse' if variant!=1 else 'supermarket',width,25.,'A')
    x=spec.door[1]
    boundary=Footprint(((-15,-40),(width+15,-40),(width+15,60),(-15,60)))
    exclusions=()
    if variant==2:
        boundary=Footprint(((-10,-40),(width*.55,-40),(width+10,-20),(width+10,60),(-10,60)))
    if variant==3:exclusions=(Footprint(((8,-18),(31,-18),(31,-4),(8,-4))),)
    ports=(Port('service',(width/2-3,60,.04),(width/2+3,60,.04)),
           Port('parking',(width*.65-3,-40,.04),(width*.65+3,-40,.04)),
           Port('pedestrian',(x-.7,-40,.04),(x+.7,-40,.04)))
    spec.site=Site('synthetic-property','synthetic-1',boundary,exclusions,ports,None if variant==4 else 1.1)
    return spec,props


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT.parent/'artifacts/buildings-sites-stage2.png')
    parser.add_argument('--example-catalogue',type=Path,help='Write a synthetic GeoJSON format example; never live map data')
    args=parser.parse_args()
    out=args.out
    out.parent.mkdir(parents=True,exist_ok=True)
    canvas=Image.new('RGB',(1500,1010),(232,237,240));d=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('Arial.ttf',19)
    except OSError:font=ImageFont.load_default(size=19)
    d.text((20,15),'Property-fitted docks, parking and footpath connections',font=font,fill=(30,45,55))
    d.text((20,44),'Synthetic evidence / approximate colours / measured boundary ports / no fixed site layouts',font=font,fill=(60,75,85))
    names=('Warehouse / full section','Supermarket / public and service sides','Tapered section',
           'Protected area / fewer spaces','No loading-floor evidence / no docks','Rough terrain / surfaces omitted')
    rows=[]
    for i,name in enumerate(names):
        s,props=fixture(60 if i<3 else 46,i)
        ground=(lambda p:.3*np.sin(p[:,0])) if i==5 else (lambda p:np.zeros(len(p)))
        site_layout.resolve([(s,0.,0.)],ground,0,0)
        mesh=b.build(freeze_items([(s,0.,0.)]))
        im=raster(mesh,props,[],500,365,b,ground=ground)
        canvas.paste(im,((i%3)*500,80+(i//3)*460))
        r=s.access.site_layout
        d.text(((i%3)*500+20,450+(i//3)*460),name,font=font,fill=(30,45,55))
        d.text(((i%3)*500+20,478+(i//3)*460),f'{r.docks} docks / {r.parking} bays / {r.terrain_points} samples',font=font,fill=(60,75,85))
        rows.append(dict(label=name,result={k:v for k,v in asdict(r).items() if k!='baseline_facades'}))
    canvas.save(out)
    # Reverse view exposes the platforms hidden behind the public frontage.
    s,props=fixture()
    site_layout.resolve([(s,0.,0.)],lambda p:np.zeros(len(p)),0,0)
    mesh=list(b.build(freeze_items([(s,0.,0.)])))
    mesh[0]=mesh[0].copy();mesh[0][:,:2]*=-1
    raster(mesh,[],[],1100,650,b).save(out.with_name(out.stem+'-docks.png'))
    if args.example_catalogue:
        from geodesy import EnuFrame
        frame=EnuFrame(-43.5,172.6,0.)
        def ll(points):
            p=np.asarray(points,float)
            lat,lon,h=frame.enu_to_geodetic(p[:,0],p[:,1],p[:,2])
            return np.c_[lon,lat,h].tolist()
        ring=ll([[-15,-40,0],[75,-40,0],[75,60,0],[-15,60,0],[-15,-40,0]])
        props=dict(site_id='synthetic-property',owner_id='SYNTHETIC-EXAMPLE-NOT-A-MAP-ID',
                   source='Synthetic format example; not surveyed data',release='example-1',obstacles_complete=True,
                   exclusions=[],dock_rise=1.1,
                   ports=[dict(kind=p.kind,coordinates=ll([p.a,p.b])) for p in s.site.ports])
        data=dict(type='FeatureCollection',features=[dict(type='Feature',properties=props,
            geometry=dict(type='Polygon',coordinates=[[q[:2] for q in ring]]))])
        args.example_catalogue.parent.mkdir(parents=True,exist_ok=True)
        args.example_catalogue.write_text(json.dumps(data,indent=2),encoding='utf-8')
    ms=[];points=[]
    for i in range(90):
        s,_=fixture(25.+i%65,i%4)
        start=time.perf_counter();site_layout.resolve([(s,0.,0.)],lambda p:np.zeros(len(p)),0,0)
        ms.append((time.perf_counter()-start)*1000);points.append(s.access.site_layout.terrain_points)
    result=dict(status='synthetic_not_game_acceptance',sites=90,p50_ms=float(np.percentile(ms,50)),
                p95_ms=float(np.percentile(ms,95)),max_points=max(points),fixtures=rows)
    out.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='fixtures'},indent=2))
    print(out)


if __name__=='__main__':main()
