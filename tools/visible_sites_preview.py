"""Reproduce automatic commercial grounds from the actual offline runtime.

Synthetic buildings share one translated footprint and supplied road/sidewalk.
The drawing shows emitted top surfaces, not a representation of shrubs or a
claim about surveyed property boundaries. No network or site catalogue is used.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen.topology import Footprint


def ground(points):return np.zeros(len(points),float)
def shape(solid):return Polygon([p[:2] for p in solid.top])


def fixture(cls,width,setback):
    fp=Footprint(((30,40),(30+width,40),(30+width,64),(30,64)))
    road_y=37.-setback
    spec=b.plan(np.asarray(fp.outer),{'class':cls,'num_floors':1,'height':6.,
        'seed_id':'visible-'+cls,'_footprint':fp,'roof_shape':'flat','facade_material':'concrete'})
    spec.gring=ground(np.asarray(spec.ring))
    item=(spec,0.,0.)
    road=[(np.array([[-50.,road_y],[150.,road_y]]),3.,'residential',False)]
    walks=[dict(pts=np.array([[-50.,road_y+4.25,0.],[150.,road_y+4.25,0.]]),side=1,w=2.5)]
    raw=[dict(pts=w['pts'].copy(),side=w['side'],w=w['w']) for w in walks]
    door_props=b.doors([item],road,0,0,ground=ground,walks=walks,raw_walks=raw)
    from geodesy import EnuFrame
    from sitegen.site_obstacles import collect
    bounds=(0.,0.,128.,128.)
    obstacles=collect(EnuFrame(-43.5,172.6),bounds,chunks=[dict(
        n=[[-50.,road_y,0.],[150.,road_y,0.]],w=6.,m='road_asphalt_2lane',tl=11.,p=19)])
    records=b.garage_drives([item],road,0,0,ground=ground,walks=walks,raw_walks=raw,
                           bounds=bounds,site_obstacles=obstacles)
    props=b.landscape_props([item],0,0)
    if any(not np.isfinite(np.asarray(row[1:],float)).all() for row in props):
        raise ValueError('non-finite native placement')
    frozen=freeze_items([item])
    meshes=[b.build(frozen),b.build(frozen,lite=True),b.collision_mesh(frozen)]
    if not all(mesh is not None and np.isfinite(mesh[0]).all() for mesh in meshes):
        raise ValueError('non-finite near, lite or collision mesh')
    solids=spec.access.solids
    beds=[s for s in spec.access.landscape if s.kind.startswith('site_')]
    if any(not np.isfinite(np.asarray(s.top,float)).all() for s in (*solids,*beds)):
        raise ValueError('non-finite surface')
    overlap=max((shape(a).intersection(shape(c)).area for a in beds for c in solids),default=0.)
    if overlap>1e-7:raise ValueError('accepted bed overlaps physical surface')
    paving=[s for s in solids if s.kind in ('site_service','site_parking','site_aisle','site_access','site_walk','site_driveway')]
    layout=spec.access.site_layout
    summary=dict(building=cls,preset=spec.inference.selection.preset.id,frontage_m=width,road_edge_setback_m=setback,
        paved_m2=round(sum(shape(s).area for s in paving),2),
        planted_bed_m2=round(sum(shape(s).area for s in beds),2),
        parking_spaces=layout.parking,curb_blocks=sum(s.kind=='site_curb' for s in solids),
        entry_links=sum(s.kind=='site_walk' for s in solids),
        road_connector_panels=sum(s.kind=='site_driveway' for s in solids),
        parking_exclusions=len(records),actual_walk_cuts=len(walks[0].get('driveways',())),
        raw_walk_cuts=len(raw[0].get('driveways',())),door_props=len(door_props),
        native_placements=dict(sorted(Counter(row[0] for row in props).items())),
        finite_near_lite_collision=True,bed_physical_overlap_m2=overlap,
        suppression_reasons=[n for n in layout.diagnostics if '=' not in n])
    return spec,summary,props,tuple(walks[0].get('driveways',()))


def render(path,fixtures):
    image=Image.new('RGB',(1400,1000),(239,242,241));d=ImageDraw.Draw(image)
    try:
        title=ImageFont.truetype('arial.ttf',24); font=ImageFont.truetype('arial.ttf',17);small=ImageFont.truetype('arial.ttf',14)
    except OSError:
        title=ImageFont.load_default();font=title;small=title
    d.text((28,16),'Automatic commercial frontages — actual runtime surfaces',font=title,fill=(27,39,40))
    d.text((30,50),'Synthetic translated fixtures  |  supplied road + sidewalk  |  ground plan  |  dots = native placement centres, not shrub meshes',font=font,fill=(70,80,80))
    cols={'site_service':(83,88,88),'site_parking':(83,88,88),'site_aisle':(83,88,88),
          'site_access':(83,88,88),'site_driveway':(83,88,88),'site_walk':(206,197,177),
          'threshold':(206,197,177),'path':(206,197,177),'path_link':(206,197,177),
          'paved_margin':(206,197,177),'site_curb':(236,218,178)}
    for index,(spec,stats,props,cuts) in enumerate(fixtures):
        xbase=20+(index%2)*690;ybase=86+(index//2)*445
        d.rounded_rectangle((xbase,ybase,xbase+670,ybase+425),radius=10,fill=(249,250,247),outline=(197,204,199),width=2)
        def pixel(p):return (xbase+165+(p[0]-20)*5.2,ybase+365-(p[1]-5)*5.2)
        def polygon(points,fill,outline=None):
            d.polygon([pixel(p) for p in points],fill=fill,outline=outline)
        road_y=37.-stats['road_edge_setback_m']
        polygon(((20,road_y-3),(84,road_y-3),(84,road_y+3),(20,road_y+3)),(67,72,73))
        polygon(((20,road_y+3),(84,road_y+3),(84,road_y+5.5),(20,road_y+5.5)),(209,203,189))
        for lo,hi,*_ in cuts:
            x0,x1=-50.+lo,-50.+hi
            polygon(((x0,road_y+3),(x1,road_y+3),(x1,road_y+5.5),(x0,road_y+5.5)),(83,88,88))
        for solid in spec.access.solids:
            if solid.kind in cols:polygon([p[:2] for p in solid.top],cols[solid.kind])
        for solid in spec.access.landscape:
            if solid.kind.startswith('site_'):polygon([p[:2] for p in solid.top],(98,137,74),outline=(65,103,58))
        for row in props:
            x,y=pixel((row[1],row[2]));d.ellipse((x-2,y-2,x+2,y+2),fill=(227,229,177),outline=(37,68,35))
        polygon(spec.ring,(182,174,158),outline=(84,77,66))
        for a,c in spec.access.site_layout.markings:
            d.line((pixel(a),pixel(c)),fill=(241,237,217),width=2)
        d.text((xbase+20,ybase+10),stats['building'].upper(),font=font,fill=(27,39,40))
        d.text((xbase+20,ybase+367),f"{stats['paved_m2']:.0f} m² pavement   {stats['planted_bed_m2']:.0f} m² beds   {stats['parking_spaces']} spaces",font=font,fill=(36,47,45))
        count=sum(stats['native_placements'].values())
        d.text((xbase+20,ybase+393),f"{stats['entry_links']} entry link  /  {stats['actual_walk_cuts']} sidewalk cut  /  {count} native placement centres",font=small,fill=(72,82,77))
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build'/'visible-sites'/'runtime-frontages.png')
    args=parser.parse_args()
    fixtures=[fixture(cls,width,setback) for cls,width,setback in
              (('retail',28.,4.),('office',30.,9.),('supermarket',44.,22.),('workshop',40.,18.))]
    render(args.out,fixtures)
    rows=[stats for _,stats,_,_ in fixtures]
    counts=Counter(note for row in rows for note in row['suppression_reasons'])
    report={'status':'synthetic actual-runtime geometry; not game acceptance','fixtures':rows,
            'suppression_counts':dict(sorted(counts.items()))}
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('preview:',args.out)

if __name__=='__main__':main()
