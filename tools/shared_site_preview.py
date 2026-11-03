"""Reproducible synthetic ground-plan review; no native rendering claim."""
from pathlib import Path
import argparse
import json
import sys
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
from test_sitegen_shared_layouts import fixture
from sitegen import shared_layouts as sl,shared_courts as sc
from sitegen.plan import SiteGraph


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tile,plan=fixture(cross=True)
    start=time.perf_counter();layout,why=sl.fit(plan,lambda la,lo:np.full(np.shape(la),20.))
    if why:raise RuntimeError(why)
    elapsed=time.perf_counter()-start
    canvas=Image.new('RGB',(1380,900),'#121b24');draw=ImageDraw.Draw(canvas)
    try:
        title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',27)
        label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    except OSError:title=label=ImageFont.load_default()
    draw.text((35,20),'Shared grounds | synthetic geometry review',font=title,fill='#edf2f6')
    def xy(p):return (390+float(p[0])*12,465-float(p[1])*12)
    def polygon(ring,fill,outline=None):draw.polygon([xy(q) for q in ring],fill=fill,outline=outline)
    polygon(plan.evidence.association_extent.outer,'#293f35','#91aa9a')
    for bed in layout.beds:
        polygon(bed.outer,'#52754a')
        for hole in bed.holes:polygon(hole,'#293f35')
    colours={'pedestrian':'#d2c7af','service':'#7b7c7e','vehicle':'#525a62'}
    for cell in layout.surfaces:polygon(cell.top,colours[cell.kind])
    for fp in plan.evidence.exclusions:polygon(fp.outer,'#839bad','#bacad5')
    for bay in layout.stalls:
        p=list(bay);draw.line([xy(q) for q in (p[0],p[3],p[2],p[1])],fill='#f2f3e7',width=2)
    park,marks,props=sl.additions(layout,sc._frame(plan),lambda la,lo:np.full(np.shape(la),20.))
    for row in props:
        x,y=xy(row[1:3]);r=6 if row[0]=='site_shrub' else 4
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#b9ce78' if row[0]=='site_shrub' else '#a6a29b')
    for port in plan.interfaces:
        draw.line([xy(q) for q in port.endpoints],fill='#ffc766',width=5)
    sectors=sl.sectors(plan);fragments=[sl.partition(layout,*s) for s in sectors]
    for sector in sectors:
        clip=sl.sector_shape(plan,*sector)
        boundary=clip.boundary.intersection(sl.shape(plan.evidence.association_extent))
        for line in getattr(boundary,'geoms',(boundary,)):
            if hasattr(line,'coords'):draw.line([xy(q) for q in line.coords],fill='#65d7ed',width=2)
    notes=[('WALKING','#d2c7af'),('DELIVERY ACCESS','#7b7c7e'),('CUSTOMER AISLE','#525a62'),('SOFT BEDS','#52754a'),('MEASURED OPENINGS','#ffc766'),('SECTOR BOUNDARY','#65d7ed')]
    for i,(text,colour) in enumerate(notes):
        y=110+i*49;draw.rectangle((805,y,827,y+22),fill=colour);draw.text((843,y-2),text,font=label,fill='#e4edf4')
    summary=[f'{len(layout.routes)} connected routes',f'{len(layout.stalls)} fitted parking bays',f'{len(props)} stock-asset planting positions',f'{len(sectors)} sector fragments; one contact owner per patch',f'{len(layout.surfaces)} canonical surface triangles',f'{layout.terrain_points} terrain probes',f'{elapsed*1000:.0f} ms synthetic planning time','Day/night, tyre contact and native streaming: pending']
    for i,text in enumerate(summary):draw.text((805,460+i*36),text,font=label,fill='#c4d4df')
    draw.text((35,830),'Plans reserve walking and delivery access before parking and planting. Source holes and exclusions stay open.',font=label,fill='#a9c0cc')
    canvas.save(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(dict(routes=len(layout.routes),parking=len(layout.stalls),plants=len(props),
        surfaces=len(layout.surfaces),terrain_points=layout.terrain_points,seconds=elapsed,sectors=sectors,
        surface_revision=layout.contact_revision,native_acceptance='pending'),indent=2))
    args.out.with_suffix('.site.json').write_text(SiteGraph((plan,)).to_json())
    print(args.out)


if __name__=='__main__':main()
