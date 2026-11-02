"""Offline curb geometry preview and bounded generation benchmark (no FPS claim)."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
import sidewalks as sw
import streetscape as sc
import vehicle_crossings as vc
import roadside_clearance as rc
from buildgen import automatic_sites
from test_buildgen_commercial import fixture
from test_buildgen_automatic_sites import road,flat
from test_buildgen_driveways import walk


def benchmark():
    def build(enhanced):
        b=sw.Builder((0,0,0),collision=True)
        for i in range(200):
            p=np.array([[0.,i*5.,0.],[100.,i*5.,0.]])
            b.add_run(p,np.tile([0.,1.],(2,1)),2.5,
                      h=list(sc.STYLES.values())[i%6].height if enhanced else .15,
                      driveways=[(45.,51.)] if enhanced and i%5==0 else (),verge=enhanced and i%2==0)
        v=b.arrays();c=b.col.arrays()
        return dict(vertices=len(v[0]),visual_triangles=len(v[1]),collision_triangles=len(c[1]))
    result={}
    for enhanced in (False,True):
        build(enhanced)
        elapsed=[]
        for _ in range(7):
            start=time.perf_counter();counts=build(enhanced);elapsed.append((time.perf_counter()-start)*1000)
        result['regional_with_40_crossings' if enhanced else 'plain_native_runs']={
            **counts,'median_ms':round(float(np.median(elapsed)),2),'max_ms':round(max(elapsed),2)}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/curb-overhaul')
    dest=parser.parse_args().out;dest.mkdir(parents=True,exist_ok=True)
    item=fixture('industrial',40,20);spec=item[0];spec.door=None;spec.access=None
    wk=walk();wk['curb_h']=.15;wk['verge']=True
    records=automatic_sites.resolve([item],road(-12),0,0,ground=flat,walks=[wk])
    curb,out=sw.run_geometry(wk['pts'],1,2.5)
    b=sw.Builder((0,0,0),collision=True)
    b.add_run(curb,out,2.5,h=.15,driveways=wk.get('driveways',()),verge=True)
    P,T,UV,M=b.arrays()
    props=[['hydrant',x,-8.6,0,0,1,.9,0] for x in (3.,10.,20.,30.,37.)]
    props.append(['bin',20.,-7.,0,0,1,1.1,0])
    kept=rc.clear(props,walks=[wk],items=[item],drives=records)
    W,H=1600,1050
    im=Image.new('RGB',(W,H),'#101b25');d=ImageDraw.Draw(im)
    def font(n):
        path=Path('C:/Windows/Fonts/segoeui.ttf')
        return ImageFont.truetype(str(path),n) if path.exists() else ImageFont.load_default(size=n)
    def text(x,y,label,n=20,fill='#dce7ef'):d.text((x,y),label,font=font(n),fill=fill)
    text(42,25,'CURBS + ROAD ACCESS',35)
    text(44,75,'Generated geometry review  /  schematic colours  /  not an in-game render',18,'#9ab0c2')
    d.rounded_rectangle((32,120,1010,996),16,fill='#1c2c35')
    text(55,140,'Unresolved industrial frontage: one fitted service entrance',23)
    text(55,178,'No invented door or parking lot. The rear footpath remains continuous.',18,'#b1c3ce')
    def xy(p):return (70+(float(p[0])+5)*17.8,875-(float(p[1])+15)*17.8)
    def poly(p,fill,outline=None):d.polygon([xy(v) for v in p],fill=fill,outline=outline)
    poly([[-5,-15],[45,-15],[45,22],[-5,22]],'#527d59')
    poly([[-5,-15],[45,-15],[45,-9],[-5,-9]],'#39464d')
    poly([[-5,-9.5],[45,-9.5],[45,-9],[-5,-9]],'#89979a')
    for solid in spec.access.solids:
        poly(solid.top,'#9ca4a3' if solid.kind=='site_service' else '#aaaeb0')
    colors=['#dedbd0','#bdc2bf','#d7bb58','#ad7666','#789861']
    for tri,mat in zip(T,M):
        if np.any(P[tri,0]<-5) or np.any(P[tri,0]>45):
            # Clip only for display; source mesh still spans its complete run.
            from shapely.geometry import Polygon,box
            shape=Polygon(P[tri,:2]).intersection(box(-5,-15,45,22))
            if shape.geom_type=='Polygon' and not shape.is_empty:poly(shape.exterior.coords,colors[int(mat)])
        else:poly(P[tri],colors[int(mat)])
    poly(spec.ring,'#697f8c','#a7b6bc')
    text(315,350,'INDUSTRIAL BUILDING',23)
    for row in props:
        x,y=xy(row[1:3])
        if any(row is v for v in kept):d.ellipse((x-6,y-6,x+6,y+6),fill='#ffc166',outline='#101b25')
        else:
            d.line((x-7,y-7,x+7,y+7),fill='#fd7872',width=3)
            d.line((x-7,y+7,x+7,y-7),fill='#fd7872',width=3)
    text(55,905,'Green: mown verge   /   pale grey: sidewalk + driveway',18)
    text(55,940,'Gold: retained hydrants   /   red crosses: conflicting props removed',18)
    d.rounded_rectangle((1032,120,1568,710),16,fill='#1c2c35')
    text(1055,140,'6 REGIONAL TREATMENTS',24)
    text(1055,178,'64 themes share a compact palette',18,'#b1c3ce')
    for i,(name,style) in enumerate(sc.STYLES.items()):
        y=225+i*76
        label=name.replace('_',' ').title()
        text(1055,y,label,19)
        text(1055,y+27,f'{style.height*1000:.0f} mm upstand  |  {style.gutter:.2f} m gutter',16,'#a9becb')
        p=sw.profile(style.height,2.5)
        # Deliberate vertical exaggeration to make the profile legible.
        d.line([(1438+float(x)*34,y+40-float(z)*130) for x,z in p],fill='#dfdad0',width=3)
    d.rounded_rectangle((1032,732,1568,996),16,fill='#1c2c35')
    text(1055,752,'SMOOTH AT THE CROSSING',22)
    text(1055,790,'Bounded 1.2 m easing flares',18,'#b1c3ce')
    text(1055,820,'Same driving surface in visual + collision',18,'#b1c3ce')
    text(1055,850,'Curves sampled to <= 8 mm chord error',18,'#b1c3ce')
    text(1055,880,'Furniture masks survive late tile arrivals',18,'#b1c3ce')
    text(1055,940,'Cross-section heights exaggerated for clarity',15,'#839eaf')
    im.save(dest/'overview.png')
    report={'benchmark_200_runs_of_100m':benchmark(),'service_connections':list(spec.access.site_layout.connections),
            'cuts':wk.get('driveways',()),'props_before':len(props),'props_after':len(kept),
            'scene_visual_triangles':len(T),'scene_collision_triangles':len(b.col.arrays()[1]),
            'native_game_acceptance':'pending; no renderer/FPS or real driving claim'}
    report['visual_sha256']=hashlib.sha256(b''.join(a.tobytes() for a in b.arrays())).hexdigest()
    report['collision_sha256']=hashlib.sha256(b''.join(a.tobytes() for a in b.col.arrays())).hexdigest()
    (dest/'geometry-review.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
